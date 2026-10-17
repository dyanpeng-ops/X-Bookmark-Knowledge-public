"""图片描述（caption）生成与增量缓存（队列 #24 A 阶段）。

职责
----
1. 对知识库里的每张配图生成**可检索的中文/文字描述**：
   * **含文字**的图片（截图类）→ 本地 OCR（:mod:`src.media.vision_ocr`）提取文字；
   * **无文字**的图片 → A 阶段如实标记"未识别到文字"，**不伪造描述**；
     B 阶段（本地视觉模型）再补"看图说话"。
2. **增量**：以图片内容的 SHA-256 为键缓存，同一内容只识别一次；图片变了才重跑。
3. **离线**：只读本地图片、只用本地进程；不联网、零 API 花费。

缓存文件：``data/state/media-descriptions.json``（gitignored，永不入 Git）。
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.media.vision_ocr import OcrEngine, OcrError, OcrUnavailableError

__all__ = [
    "MediaDescription",
    "MediaDescriptionStore",
    "DESCRIPTION_SCHEMA",
    "default_store_path",
]

#: 缓存文件 schema 版本（结构变更时递增，旧缓存自动失效）。
DESCRIPTION_SCHEMA = 2

#: caption 里正文的最大长度（超出截断并加省略号；完整文本仍在缓存/OCR 里）。
CAPTION_MAX_CHARS = 600


def default_store_path(project_root: str | os.PathLike[str] | None = None) -> Path:
    root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[2]
    return root / "data" / "state" / "media-descriptions.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_lines(lines: tuple[str, ...]) -> str:
    """把 OCR 行清洗成一段可读文本：去空行、按行拼接。"""

    cleaned = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned)


def _caption_text(text: str) -> str:
    if len(text) <= CAPTION_MAX_CHARS:
        return text
    return text[:CAPTION_MAX_CHARS].rstrip() + "…"


@dataclass(frozen=True)
class MediaDescription:
    """一张配图的描述。``source`` 取值：``"ocr"`` / ``"none"``（未来 ``"vision"``）。"""

    sha256: str
    text: str
    source: str
    has_text: bool
    langs: tuple[str, ...] = ()
    described_at: str = ""

    @property
    def caption(self) -> str:
        """用于 caption 的短文本（截断到 ``CAPTION_MAX_CHARS``）。"""

        return _caption_text(self.text)

    @property
    def alt_text(self) -> str:
        """Markdown 图片 alt 文本 —— 用描述的首行，保证可检索且不破坏排版。"""

        if self.has_text:
            first = self.text.split("\n", 1)[0].strip()
            if first:
                return first[:80]
            return "截图（OCR 未返回文本）"
        return "配图（A 阶段未识别到文字）"

    def to_json(self) -> dict[str, Any]:
        return {
            "sha256": self.sha256,
            "text": self.text,
            "source": self.source,
            "has_text": self.has_text,
            "langs": list(self.langs),
            "described_at": self.described_at,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "MediaDescription":
        return cls(
            sha256=str(payload.get("sha256") or ""),
            text=str(payload.get("text") or ""),
            source=str(payload.get("source") or "none"),
            has_text=bool(payload.get("has_text")),
            langs=tuple(str(x) for x in (payload.get("langs") or [])),
            described_at=str(payload.get("described_at") or ""),
        )


class MediaDescriptionStore:
    """描述缓存 + 生成器（增量、离线、可降级）。

    ``engine`` 缺省为 :class:`~src.media.vision_ocr.OcrEngine`；测试可注入桩引擎
    （只需提供 ``ocr(path) -> OcrResult`` 与 ``available()``）。
    """

    def __init__(
        self,
        *,
        store_path: str | os.PathLike[str] | None = None,
        root: str | os.PathLike[str] | None = None,
        engine: Any | None = None,
    ) -> None:
        self._root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
        self._store_path = Path(store_path) if store_path is not None else default_store_path(self._root)
        self._engine = engine if engine is not None else OcrEngine(root=self._root)
        self._entries: dict[str, MediaDescription] = {}
        self._dirty = False
        self._loaded = False
        self.stats = {"hit": 0, "ocr": 0, "no_text": 0, "failed": 0}

    # ── 持久化 ──────────────────────────────────────────────────────────────

    def load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._store_path.is_file():
            return
        try:
            payload = json.loads(self._store_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return                       # 缓存损坏 ⇒ 当作空缓存（可重建，不阻断）
        if payload.get("schema") != DESCRIPTION_SCHEMA:
            return                       # schema 变了 ⇒ 旧缓存失效
        for item in payload.get("entries") or []:
            desc = MediaDescription.from_json(item)
            if desc.sha256:
                self._entries[desc.sha256] = desc

    def save(self) -> None:
        if not self._dirty:
            return
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": DESCRIPTION_SCHEMA,
            "entries": [desc.to_json() for desc in sorted(
                self._entries.values(), key=lambda d: d.sha256)],
        }
        tmp = self._store_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self._store_path)
        self._dirty = False

    # ── 生成 ────────────────────────────────────────────────────────────────

    def describe(self, image_path: str | os.PathLike[str]) -> MediaDescription:
        """返回该图片的描述；命中缓存直接复用（增量），否则跑 OCR 并入库。"""

        self.load()
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"配图不存在: {path}")
        sha = _sha256_file(path)
        cached = self._entries.get(sha)
        if cached is not None:
            self.stats["hit"] += 1
            return cached
        desc = self._describe_uncached(path, sha)
        self._entries[sha] = desc
        self._dirty = True
        return desc

    def _describe_uncached(self, path: Path, sha: str) -> MediaDescription:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            result = self._engine.ocr(path)
        except OcrUnavailableError:
            # 本机不具备本地 OCR：**如实标记未识别**，不伪造、不阻断渲染
            self.stats["failed"] += 1
            return MediaDescription(sha256=sha, text="", source="none", has_text=False,
                                    described_at=stamp)
        except OcrError:
            self.stats["failed"] += 1
            return MediaDescription(sha256=sha, text="", source="none", has_text=False,
                                    described_at=stamp)
        text = _clean_lines(result.lines)
        if text:
            self.stats["ocr"] += 1
            return MediaDescription(sha256=sha, text=text, source="ocr", has_text=True,
                                    langs=result.languages, described_at=stamp)
        self.stats["no_text"] += 1
        return MediaDescription(sha256=sha, text="", source="none", has_text=False,
                                langs=result.languages, described_at=stamp)

    # ── 便于渲染层使用的映射 ────────────────────────────────────────────────

    def captions_for(self, images: Mapping[str, str | os.PathLike[str]]) -> dict[str, MediaDescription]:
        """``{source_url: 本地图片路径}`` → ``{source_url: 描述}``（失败的条目缺省）。"""

        out: dict[str, MediaDescription] = {}
        for url, local in images.items():
            try:
                out[str(url)] = self.describe(local)
            except (OSError, FileNotFoundError):
                continue
        return out
