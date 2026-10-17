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

from src.media.vision import VisionEngine, VisionError, VisionUnavailableError
from src.media.vision_ocr import OcrEngine, OcrError, OcrUnavailableError

__all__ = [
    "MediaDescription",
    "MediaDescriptionStore",
    "DESCRIPTION_SCHEMA",
    "default_store_path",
]

#: 缓存文件 schema 版本（结构变更时递增，旧缓存自动失效）。
#: v4（2026-10-17）：新增「OCR 质量门」——乱码/过碎的 OCR 也补视觉描述，
#: 旧条目需重判 ⇒ schema 升级使 v3 缓存整体失效一次（一次性重跑，之后仍按 sha256 增量）。
DESCRIPTION_SCHEMA = 4

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


# ── OCR 质量门（队列 #26）──────────────────────────────────────────────────
#
# 目标：识别「有文字、但**乱码/过碎**」的 OCR —— 这类图的 OCR caption 读不懂，
# 交给视觉模型"看图说话"更有价值；而**质量好的 OCR**（成句、行较长）仍然不调视觉（省时间）。
#
# 启发式（均可用环境变量覆盖，便于调参与测试）：
#   H1 有效字数过少：total_chars < XBK_OCR_MIN_CHARS（默认 40）
#   H2 过碎：短行（≤3 字）占比 ≥ XBK_OCR_SHORT_LINE_RATIO（默认 0.40）
#            且 平均行长 < XBK_OCR_MAX_AVG_LINE（默认 8.0）
#
# 刻意**不使用**「CJK 占比低」：英文截图（GitHub / 英文网页）CJK 占比天然为 0，
# 但 OCR 完全正确，用它会把好文本误判为乱码（实测数据已证实）。
MIN_TOTAL_CHARS = int(os.environ.get("XBK_OCR_MIN_CHARS", "40"))
SHORT_LINE_MAX_LEN = 3
SHORT_LINE_RATIO = float(os.environ.get("XBK_OCR_SHORT_LINE_RATIO", "0.40"))
MAX_AVG_LINE_LEN = float(os.environ.get("XBK_OCR_MAX_AVG_LINE", "8.0"))


@dataclass(frozen=True)
class OcrQuality:
    """OCR 文本的质量指标（纯数据，便于断言与调参）。"""

    total_chars: int
    n_lines: int
    short_line_ratio: float
    avg_line_len: float

    @property
    def garbled(self) -> bool:
        """是否判定为「乱码/过碎」（需补视觉描述）。"""

        if self.n_lines == 0 or self.total_chars == 0:
            return False                      # 空文本走"无文字"分支，不在此判定
        too_short = self.total_chars < MIN_TOTAL_CHARS
        fragmented = (
            self.short_line_ratio >= SHORT_LINE_RATIO
            and self.avg_line_len < MAX_AVG_LINE_LEN
        )
        return too_short or fragmented


def classify_ocr_quality(text: str) -> OcrQuality:
    """计算 OCR 文本的质量指标（空行不计入行数）。"""

    lines = [line.strip() for line in str(text).split("\n") if line.strip()]
    if not lines:
        return OcrQuality(total_chars=0, n_lines=0, short_line_ratio=0.0, avg_line_len=0.0)
    total = sum(len(line) for line in lines)
    short = sum(1 for line in lines if len(line) <= SHORT_LINE_MAX_LEN)
    return OcrQuality(
        total_chars=total,
        n_lines=len(lines),
        short_line_ratio=short / len(lines),
        avg_line_len=total / len(lines),
    )


@dataclass(frozen=True)
class MediaDescription:
    """一张配图的描述。``source`` 取值：``"ocr"`` / ``"none"``（未来 ``"vision"``）。"""

    sha256: str
    text: str
    source: str
    has_text: bool
    langs: tuple[str, ...] = ()
    described_at: str = ""
    #: 队列 #26：OCR 原始文本（当 `source="vision"` 时保留，便于回溯"OCR 当时看到了什么"）。
    ocr_text: str = ""

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
            "ocr_text": self.ocr_text,
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
            ocr_text=str(payload.get("ocr_text") or ""),
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
        vision: Any | None = None,
    ) -> None:
        self._root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
        self._store_path = Path(store_path) if store_path is not None else default_store_path(self._root)
        self._engine = engine if engine is not None else OcrEngine(root=self._root)
        #: B 阶段：**仅当 OCR 无文字**时才调用的本地视觉后端；None = 不启用视觉。
        self._vision = vision if vision is not None else VisionEngine()
        self._entries: dict[str, MediaDescription] = {}
        self._dirty = False
        self._loaded = False
        self.stats = {"hit": 0, "ocr": 0, "garbled": 0, "vision": 0, "no_text": 0, "failed": 0}

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
            quality = classify_ocr_quality(text)
            if not quality.garbled:
                # 质量好的 OCR：**不调视觉**（省时间），直接用 OCR 文字做 caption
                self.stats["ocr"] += 1
                return MediaDescription(sha256=sha, text=text, source="ocr", has_text=True,
                                        langs=result.languages, described_at=stamp)
            # 队列 #26：OCR **乱码/过碎** ⇒ 也走视觉"补描述"（视觉失败则退回 OCR 原文）
            self.stats["garbled"] = self.stats.get("garbled", 0) + 1
            vision_text = self._try_vision(path)
            if vision_text:
                self.stats["vision"] += 1
                return MediaDescription(sha256=sha, text=vision_text, source="vision",
                                        has_text=True, langs=result.languages,
                                        described_at=stamp, ocr_text=text)
            self.stats["ocr"] += 1
            return MediaDescription(sha256=sha, text=text, source="ocr", has_text=True,
                                    langs=result.languages, described_at=stamp)
        # —— OCR 无文字 ⇒ 走本地视觉模型"看图说话"（A 阶段优先级不变）——
        vision_text = self._try_vision(path)
        if vision_text:
            self.stats["vision"] += 1
            return MediaDescription(sha256=sha, text=vision_text, source="vision", has_text=True,
                                    langs=result.languages, described_at=stamp)
        self.stats["no_text"] += 1
        return MediaDescription(sha256=sha, text="", source="none", has_text=False,
                                langs=result.languages, described_at=stamp)

    def _try_vision(self, path: Path) -> str:
        """尝试用本地视觉模型描述；不可用/失败一律返回空串（**不伪造、不阻断**）。"""

        if self._vision is None:
            return ""
        try:
            if hasattr(self._vision, "available") and not self._vision.available():
                return ""
            described = self._vision.describe(path)
        except (VisionUnavailableError, VisionError, OSError):
            # 单张失败不能拖垮整批渲染：只统计，不抛出
            self.stats["vision_failed"] = self.stats.get("vision_failed", 0) + 1
            return ""
        return " ".join(str(getattr(described, "text", "") or "").split())

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
