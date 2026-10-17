"""书签标签分类（队列 #28）：用本机 Bionic/Saluki，从**预设 12 个标签**里选 1–3 个。

约束：
* **本地优先**：只调本机 OpenAI 兼容端点，零 API 花费、数据不出本机；
* **只允许预设标签**：模型输出里不在预设表的词一律丢弃（不自由造标签）；
* **每篇 1–3 个**；
* 不可用/失败 ⇒ 返回空（**不伪造标签**），并计入 `failed` 统计。
"""

from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass

from src.media.vision import DEFAULT_BASE_URL, DEFAULT_MODEL, VisionError, VisionUnavailableError

__all__ = ["PRESET_TAGS", "TagClassifier", "parse_tags", "TAG_PROMPT"]

#: 预设标签（Arlo 列、用户认可；顺序固定，便于渲染与测试）
PRESET_TAGS: tuple[str, ...] = (
    "AI大模型",
    "AI工具",
    "Agent自动化",
    "编程开发",
    "投资理财",
    "宏观经济",
    "美股QDII",
    "iPhone技巧",
    "效率工具",
    "科技新闻",
    "设计创意",
    "生活随笔",
)

#: 分类提示词：只从预设里选，输出 JSON 数组，1–3 个。
TAG_PROMPT = (
    "你是书签分类器。从下列**固定标签**中选择 1–3 个最贴切的：\n"
    + "\n".join(f"- {tag}" for tag in PRESET_TAGS)
    + "\n\n只输出一个 JSON 数组（如 [\"AI工具\"]），不要解释、不要输出标签以外的词。\n\n内容：\n{text}"
)


def parse_tags(raw: str) -> tuple[str, ...]:
    """把模型输出解析成**合法的预设标签**（去重、保序、最多 3 个；非法一律丢弃）。"""

    text = str(raw or "").strip()
    match = re.search(r"\[[^\]]*\]", text)
    candidates: list[str] = []
    if match:
        try:
            data = json.loads(match.group(0))
        except ValueError:
            data = None
        if isinstance(data, list):
            candidates = [str(item) for item in data]
    if not candidates:
        # 退路：直接找预设标签出现
        candidates = [tag for tag in PRESET_TAGS if tag in text]
    preset = {tag: index for index, tag in enumerate(PRESET_TAGS)}
    picked: list[str] = []
    for item in candidates:
        tag = item.strip().strip('"\'，,')
        if tag in preset and tag not in picked:
            picked.append(tag)
    picked.sort(key=lambda tag: preset[tag])       # 保预设顺序，稳定输出
    return tuple(picked[:3])


@dataclass
class TagClassifier:
    """本地标签分类器（OpenAI 兼容；可用性可注入，便于测试与降级）。"""

    base_url: str = ""
    model: str = ""
    timeout: float = 180.0
    stats: dict | None = None

    def __post_init__(self) -> None:
        self.base_url = (self.base_url or os.environ.get("XBK_VISION_BASE_URL")
                         or DEFAULT_BASE_URL).rstrip("/")
        self.model = self.model or os.environ.get("XBK_VISION_MODEL") or DEFAULT_MODEL
        if self.stats is None:
            self.stats = {"classified": 0, "failed": 0, "hit": 0}
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

    def classify(self, text: str) -> tuple[str, ...]:
        """返回 1–3 个预设标签；不可用/失败返回空元组（不伪造）。"""

        body = str(text or "").strip()
        if not body or not self.available():
            return ()
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": TAG_PROMPT.format(text=body[:4000])}],
            "max_tokens": 128,
            "temperature": 0.0,
        }
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            content = data["choices"][0]["message"]["content"]
        except Exception:  # noqa: BLE001 - 分类失败只降级，绝不阻断
            self.stats["failed"] = int(self.stats.get("failed", 0)) + 1
            return ()
        tags = parse_tags(str(content))
        if tags:
            self.stats["classified"] = int(self.stats.get("classified", 0)) + 1
        else:
            self.stats["failed"] = int(self.stats.get("failed", 0)) + 1
        return tags
