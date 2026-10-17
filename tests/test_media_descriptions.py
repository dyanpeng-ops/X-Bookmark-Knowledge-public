"""图片描述（caption）生成与增量缓存测试 —— 队列 #24 A 阶段，全离线、不依赖真实 OCR。

覆盖：
* OCR 文字 → caption / alt 文本；
* **增量**：同图只识别一次；换实例仍命中磁盘缓存；**图片内容变了才重跑**；
* **不伪造**：无文字 / OCR 不可用 / OCR 失败 ⇒ 如实标记，不编造描述；
* 超长截断；缺失图片报错；
* 引擎可注入（``XBK_OCR_BIN`` 桩），保证 CI 上不需要 macOS Vision。
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.media.descriptions import CAPTION_MAX_CHARS, MediaDescriptionStore  # noqa: E402
from src.media.vision_ocr import OcrEngine, OcrError, OcrResult, OcrUnavailableError  # noqa: E402


class _StubEngine:
    """最小 OCR 桩：按需返回文本行 / 抛错 / 标记不可用，并统计调用次数。"""

    def __init__(self, lines=(), *, fail: bool = False, unavailable: bool = False):
        self.calls = 0
        self._lines = tuple(lines)
        self._fail = fail
        self._unavailable = unavailable

    def available(self) -> bool:
        return not self._unavailable

    def ocr(self, path):  # noqa: ANN001 - 与 OcrEngine.ocr 同形
        self.calls += 1
        if self._unavailable:
            raise OcrUnavailableError("ocr unavailable")
        if self._fail:
            raise OcrError("boom")
        return OcrResult(path=Path(path), lines=self._lines, languages=("zh-Hans",))


class MediaDescriptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="xbook-desc-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.img = self.tmp / "shot.png"
        self.img.write_bytes(b"fake-png-bytes")

    def store(self, engine, **kwargs) -> MediaDescriptionStore:
        return MediaDescriptionStore(store_path=self.tmp / "desc.json", engine=engine, **kwargs)

    # ── 基本行为 ────────────────────────────────────────────────────────────

    def test_ocr_text_becomes_caption_and_alt(self):
        store = self.store(_StubEngine(["第一行", "第二行"]))
        desc = store.describe(self.img)
        self.assertTrue(desc.has_text)
        self.assertEqual(desc.source, "ocr")
        self.assertIn("第一行", desc.caption)
        self.assertIn("第二行", desc.caption)
        self.assertEqual(desc.alt_text, "第一行")

    def test_no_text_image_marks_none_without_faking(self):
        store = self.store(_StubEngine([]))
        desc = store.describe(self.img)
        self.assertFalse(desc.has_text)
        self.assertEqual(desc.source, "none")
        self.assertEqual(desc.text, "")
        self.assertIn("未识别到文字", desc.alt_text)

    # ── 增量 ────────────────────────────────────────────────────────────────

    def test_same_image_is_only_ocred_once(self):
        engine = _StubEngine(["x"])
        store = self.store(engine)
        store.describe(self.img)
        store.describe(self.img)
        self.assertEqual(engine.calls, 1)
        self.assertEqual(store.stats["hit"], 1)

    def test_cache_persists_across_instances(self):
        first = self.store(_StubEngine(["x"]))
        first.describe(self.img)
        first.save()
        second_engine = _StubEngine(["y"])
        second = self.store(second_engine)
        desc = second.describe(self.img)
        self.assertEqual(second_engine.calls, 0, "命中磁盘缓存，不应重跑 OCR")
        self.assertEqual(desc.text, "x")

    def test_changed_image_is_redescribed(self):
        engine = _StubEngine(["old"])
        store = self.store(engine)
        store.describe(self.img)
        self.img.write_bytes(b"different-bytes")     # 内容变了 ⇒ 缓存键变
        store.describe(self.img)
        self.assertEqual(engine.calls, 2)

    # ── 降级 / 边界 ─────────────────────────────────────────────────────────

    def test_unavailable_engine_degrades_without_raising(self):
        store = self.store(_StubEngine(unavailable=True))
        desc = store.describe(self.img)
        self.assertFalse(desc.has_text)
        self.assertEqual(store.stats["failed"], 1)

    def test_ocr_error_degrades_without_raising(self):
        store = self.store(_StubEngine(fail=True))
        desc = store.describe(self.img)
        self.assertFalse(desc.has_text)
        self.assertEqual(store.stats["failed"], 1)

    def test_caption_is_truncated(self):
        store = self.store(_StubEngine(["长" * (CAPTION_MAX_CHARS + 50)]))
        desc = store.describe(self.img)
        self.assertLessEqual(len(desc.caption), CAPTION_MAX_CHARS + 1)
        self.assertTrue(desc.caption.endswith("…"))

    def test_missing_image_raises(self):
        store = self.store(_StubEngine([]))
        with self.assertRaises(FileNotFoundError):
            store.describe(self.tmp / "nope.png")


class OcrEngineTests(unittest.TestCase):
    def test_missing_binary_override_is_unavailable(self):
        engine = OcrEngine(binary_path="/nonexistent/vision_ocr")
        with self.assertRaises(OcrUnavailableError):
            engine.binary()
        self.assertFalse(engine.available())

    def test_binary_override_is_used_and_output_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "ocr-stub"
            script.write_text(
                "#!/bin/sh\n"
                "echo '{\"lines\":[\"hi\",\"there\"],\"langs\":[\"zh-Hans\"]}'\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
            image = Path(tmp) / "a.png"
            image.write_bytes(b"x")
            engine = OcrEngine(binary_path=script)
            result = engine.ocr(image)
            self.assertEqual(result.lines, ("hi", "there"))
            self.assertEqual(result.languages, ("zh-Hans",))
            self.assertTrue(result.has_text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
