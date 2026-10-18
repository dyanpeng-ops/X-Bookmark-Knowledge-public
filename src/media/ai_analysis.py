"""AI 增强分析（Phase 11，队列 #37）：本地 Saluki，零云端 token。

对清洗后的推文正文做后处理，产出三段结构化内容：
1. **要点提炼**（1–3 句）
2. **见解与行动建议**（2–4 条）
3. **标签扩展** —— 存**单独字段** `tags_ai`，**不碰 #28 的预设 `tags` 体系**，避免冲突。

约束（队列 #37）：增量（按正文 sha256 缓存）、失败留空不伪造、本地优先。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.media.vision import DEFAULT_BASE_URL, DEFAULT_MODEL, VisionError, VisionUnavailableError

__all__ = ["AIAnalysis", "AIAnalysisStore", "should_analyze", "PROMPT", "ANALYSIS_SCHEMA"]

ANALYSIS_SCHEMA = 1

#: 提示词：要求输出严格 JSON，三段齐全；标签扩展单独给出、不得冲撞预设。
PROMPT = """你是知识库分析助手。阅读下面这条书签的内容，输出**严格 JSON**（不要多余文字）：
{{
  "summary": "1–3 句要点提炼",
  "insights": ["见解或行动建议", "..."],
  "tags_ai": ["扩展标签1", "扩展标签2"]
}}

要求：
- summary：客观概括，不评论；
- insights：2–4 条，尽量可执行；
- tags_ai：1–3 个**扩展**标签（补充预设体系之外的主题词，如具体地名/行业/人名），不要重复这些预设标签：{preset}；
- 信息不足就少写，不要编造。

内容：
{text}
"""

#: 判断是否值得分析：正文要有一定信息量
def should_analyze(text: str | None) -> bool:
    body = str(text or "").strip()
    return len(re.sub(r"\s+", "", body)) >= 40


def _sha256(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


@dataclass
class AIAnalysis:
    summary: str = ""
    insights: list[str] = field(default_factory=list)
    tags_ai: list[str] = field(default_factory=list)
    at: str = ""

    @property
    def has_content(self) -> bool:
        return bool(self.summary or self.insights)

    def to_markdown(self) -> str:
        lines: list[str] = []
        if self.summary:
            lines += [f"- **要点**：{self.summary}"]
        for item in self.insights:
            lines.append(f"- **建议**：{item}")
        if self.tags_ai:
            lines.append(f"- **扩展标签**：{'、'.join(self.tags_ai)}")
        return "\n".join(lines) if lines else "_未生成 AI 分析_"

    def to_json(self) -> dict[str, Any]:
        return {"summary": self.summary, "insights": list(self.insights),
                "tags_ai": list(self.tags_ai), "at": self.at}


class AIAnalysisStore:
    """分析缓存 + 生成器（按正文 sha256 增量；失败留空不伪造）。"""

    def __init__(self, *, store_path: str | os.PathLike[str] | None = None,
                 engine: Any | None = None, preset_tags: tuple[str, ...] = ()) -> None:
        from pathlib import Path
        self._path = Path(store_path) if store_path is not None else Path("data/state/ai-analysis.json")
        self._engine = engine if engine is not None else _LocalEngine()
        self._preset = preset_tags
        self._entries: dict[str, dict[str, Any]] = {}
        self._loaded = False
        self._dirty = False
        self.stats = {"hit": 0, "analyzed": 0, "failed": 0}

    def load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._path.is_file():
            return
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if payload.get("schema") == ANALYSIS_SCHEMA:
            self._entries = dict(payload.get("entries") or {})

    def save(self) -> None:
        if not self._dirty:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"schema": ANALYSIS_SCHEMA, "entries": self._entries},
                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self._path)
        self._dirty = False

    def analyze(self, text: str) -> AIAnalysis:
        body = str(text or "").strip()
        if not should_analyze(body):
            return AIAnalysis()
        self.load()
        key = _sha256(body)
        cached = self._entries.get(key)
        if cached is not None:
            self.stats["hit"] += 1
            return AIAnalysis(summary=cached.get("summary", ""),
                              insights=list(cached.get("insights") or []),
                              tags_ai=list(cached.get("tags_ai") or []),
                              at=cached.get("at", ""))
        try:
            raw = self._engine.complete(PROMPT.format(
                preset="、".join(self._preset) or "（无）", text=body[:6000]))
        except (VisionUnavailableError, VisionError, OSError):
            self.stats["failed"] += 1
            return AIAnalysis()
        result = parse_analysis(raw, preset=self._preset)
        if not result.has_content:
            self.stats["failed"] += 1
            return AIAnalysis()
        result.at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._entries[key] = result.to_json()
        self._dirty = True
        self.stats["analyzed"] += 1
        return result


def parse_analysis(raw: str, preset: tuple[str, ...] = ()) -> AIAnalysis:
    """解析模型输出（严格 JSON → 宽松回退）；标签扩展不得与预设重复。"""

    text = str(raw or "").strip()
    block = re.search(r"\{.*\}", text, re.S)
    data: dict[str, Any] = {}
    if block:
        try:
            data = json.loads(block.group(0))
        except ValueError:
            data = {}
    summary = str(data.get("summary") or "").strip()
    insights = [str(x).strip() for x in (data.get("insights") or []) if str(x).strip()]
    tags_ai = [str(x).strip() for x in (data.get("tags_ai") or []) if str(x).strip()]
    preset_set = set(preset)
    tags_ai = [t for t in tags_ai if t not in preset_set][:3]
    return AIAnalysis(summary=summary, insights=insights[:4], tags_ai=tags_ai)


class _LocalEngine:
    """最小本地补全客户端（OpenAI 兼容、纯 stdlib、零云端）。"""

    def __init__(self, *, base_url: str | None = None, model: str | None = None,
                 timeout: float = 240.0) -> None:
        self.base_url = (base_url or os.environ.get("XBK_VISION_BASE_URL")
                         or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("XBK_VISION_MODEL") or DEFAULT_MODEL
        self.timeout = timeout
        self._probed: bool | None = None

    def available(self) -> bool:
        if self._probed is not None:
            return self._probed
        try:
            with urllib.request.urlopen(f"{self.base_url}/v1/models", timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8", "replace"))
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError, ValueError):
            self._probed = False
            return False
        ids = {item.get("id") for item in payload.get("data") or [] if isinstance(item, dict)}
        self._probed = self.model in ids
        return self._probed

    def complete(self, prompt: str) -> str:
        if not self.available():
            raise VisionUnavailableError(f"本地模型不可用（{self.base_url} / {self.model}）")
        payload = {"model": self.model,
                   "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": 800, "temperature": 0.3}
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        return str(data["choices"][0]["message"]["content"]).strip()
