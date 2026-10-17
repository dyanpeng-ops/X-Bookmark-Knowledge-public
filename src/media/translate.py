"""本地翻译（英文/西语书签 → 简体中文）：调用本机 Bionic/Saluki，零 API 花费、数据不出本机。

用户要求（2026-10-17）：
* 书签原内容是英文的 ⇒ **翻译成中文**；
* **不翻译软件名/公司名/产品名/模型名/代码/命令/URL/@用户名/#标签**，只翻译**日常用语**；
* **标题也翻译**（同样规则）。

与视觉共用同一本地 OpenAI 兼容端点（`XBK_VISION_BASE_URL` / `XBK_VISION_MODEL`），纯 stdlib。
"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request

from src.media.vision import DEFAULT_BASE_URL, DEFAULT_MODEL, VisionError, VisionUnavailableError

__all__ = ["TranslationEngine", "TRANSLATE_PROMPT", "should_translate"]

#: 翻译提示词：**只翻日常用语**，专有名词/代码/URL 一律保留（用户明确要求）。
TRANSLATE_PROMPT = (
    "把下面的内容翻译成简体中文。严格要求：\n"
    "1) 只翻译日常用语与叙述性文字；\n"
    "2) **软件名、公司名、产品名、模型名、代码、命令行、URL、@用户名、#标签、emoji 一律保留原文**，"
    "不翻译、不音译、不改写；\n"
    "3) 不增删信息、不加解释、不加引号；只输出译文本身。\n\n"
    "原文：\n{text}"
)

#: 英文/西语等"需要翻译"的语言代码（中文 zh 与 zxx 不翻）。
_TRANSLATABLE_LANGS = frozenset({"en", "es", "fr", "de", "ja", "ko", "pt", "ru"})


def should_translate(language: str | None, text: str | None = None) -> bool:
    """是否需要翻译：语言属于外文，或（语言未知时）正文以拉丁字母为主。"""

    lang = str(language or "").strip().lower()
    if lang in _TRANSLATABLE_LANGS:
        return True
    if lang in ("zh", "zxx", ""):
        if lang == "zh":
            return False
        body = str(text or "")
        letters = sum(1 for ch in body if ch.isascii() and ch.isalpha())
        cjk = sum(1 for ch in body if "\u4e00" <= ch <= "\u9fff")
        return letters >= 20 and letters > cjk * 2      # 字母为主才判定外文
    return False


class TranslationEngine:
    """本地翻译客户端（OpenAI 兼容，纯 stdlib；不可用时如实抛错，由上层降级）。"""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 180.0,
    ) -> None:
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

    def translate(self, text: str) -> str:
        """翻译一段文本；空文本直接返回空串。失败抛 Vision*Error（上层降级、不伪造）。"""

        body_text = str(text or "").strip()
        if not body_text:
            return ""
        if not self.available():
            raise VisionUnavailableError(f"本地翻译服务不可用（{self.base_url} / {self.model}）")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": TRANSLATE_PROMPT.format(text=body_text)}],
            "max_tokens": 2048,
            "temperature": 0.1,
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
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            raise VisionUnavailableError(f"翻译调用失败（网络/超时）: {exc}") from exc
        except (OSError, ValueError) as exc:
            raise VisionError(f"翻译调用失败: {exc}") from exc
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise VisionError(f"翻译响应结构异常: {str(data)[:200]}") from exc
        return str(content).strip()


# ── 增量缓存（按原文 sha256）────────────────────────────────────────────────

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

TRANSLATION_SCHEMA = 1


def _sha256(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


class TranslationStore:
    """翻译缓存（`data/state/translations.json`，gitignored）：原文不变就不重翻。"""

    def __init__(self, *, store_path: str | Path | None = None, engine: Any | None = None) -> None:
        self._path = Path(store_path) if store_path is not None else Path("data/state/translations.json")
        self._engine = engine if engine is not None else TranslationEngine()
        self._entries: dict[str, dict[str, str]] = {}
        self._loaded = False
        self._dirty = False
        self.stats = {"hit": 0, "translated": 0, "failed": 0}

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
        if payload.get("schema") == TRANSLATION_SCHEMA:
            self._entries = dict(payload.get("entries") or {})

    def save(self) -> None:
        if not self._dirty:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": TRANSLATION_SCHEMA, "entries": self._entries}
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self._path)
        self._dirty = False

    def translate(self, text: str) -> str:
        """翻译一段文本（命中缓存直接返回；失败返回空串，不伪造）。"""

        body = str(text or "").strip()
        if not body:
            return ""
        self.load()
        key = _sha256(body)
        cached = self._entries.get(key)
        if cached is not None:
            self.stats["hit"] += 1
            return str(cached.get("zh") or "")
        try:
            zh = self._engine.translate(body)
        except (VisionUnavailableError, VisionError, OSError):
            self.stats["failed"] += 1
            return ""
        if not zh:
            self.stats["failed"] += 1
            return ""
        self._entries[key] = {
            "zh": zh,
            "src": body[:120],
            "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self._dirty = True
        self.stats["translated"] += 1
        return zh
