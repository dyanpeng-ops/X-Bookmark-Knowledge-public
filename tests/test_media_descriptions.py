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


# ── B 阶段：视觉后端 ─────────────────────────────────────────────────────────


class _StubVision:
    """视觉桩：记录调用次数，按需返回描述或抛错。"""

    def __init__(self, text: str = "一张卡通插画。", *, available: bool = True,
                 fail: bool = False):
        self.calls = 0
        self._text = text
        self._available = available
        self._fail = fail

    def available(self) -> bool:
        return self._available

    def describe(self, path):  # noqa: ANN001
        from src.media.vision import VisionDescription, VisionError
        self.calls += 1
        if self._fail:
            raise VisionError("vision boom")
        return VisionDescription(text=self._text, model="stub")


class VisionIntegrationTests(unittest.TestCase):
    """队列 #24 B 阶段：**只有 OCR 无文字的图片**才走视觉；失败如实降级。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="xbook-vis-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.img = self.tmp / "photo.jpg"
        self.img.write_bytes(b"fake-jpeg")

    def store(self, ocr_lines, vision):
        return MediaDescriptionStore(store_path=self.tmp / "d.json", engine=_StubEngine(ocr_lines),
                                     vision=vision)

    def test_vision_used_only_when_ocr_finds_no_text(self):
        vision = _StubVision("一张海边日落的照片。")
        desc = self.store([], vision).describe(self.img)
        self.assertEqual(vision.calls, 1)
        self.assertEqual(desc.source, "vision")
        self.assertTrue(desc.has_text)
        self.assertIn("海边日落", desc.text)

    def test_vision_not_called_when_ocr_has_text(self):
        # 队列 #26 起：**质量好**的 OCR 才不调视觉；乱码/过碎会补视觉（另有专门用例）
        good = ["这是一段足够长、成句的中文说明文本，用来证明质量门不会误伤它。"] * 3
        vision = _StubVision()
        desc = self.store(good, vision).describe(self.img)
        self.assertEqual(vision.calls, 0, "质量好的 OCR 不得调用视觉（省时间）")
        self.assertEqual(desc.source, "ocr")

    def test_vision_failure_degrades_to_none(self):
        store = self.store([], _StubVision(fail=True))
        desc = store.describe(self.img)
        self.assertEqual(desc.source, "none")
        self.assertFalse(desc.has_text)
        self.assertEqual(store.stats.get("vision_failed"), 1)

    def test_vision_unavailable_degrades_to_none(self):
        store = self.store([], _StubVision(available=False))
        desc = store.describe(self.img)
        self.assertEqual(desc.source, "none")
        self.assertEqual(store.stats.get("vision"), 0)

    def test_no_vision_engine_keeps_none(self):
        store = MediaDescriptionStore(store_path=self.tmp / "d.json",
                                      engine=_StubEngine([]), vision=None)
        desc = store.describe(self.img)
        self.assertEqual(desc.source, "none")


class VisionEngineHttpTests(unittest.TestCase):
    """用 stdlib 起一个极简 OpenAI 兼容 stub，验证真实 HTTP 客户端（不依赖 Bionic）。"""

    @classmethod
    def setUpClass(cls) -> None:
        import http.server
        import json as _json
        import threading

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = _json.dumps({"data": [{"id": "stub-vision"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(length)
                body = _json.dumps({"model": "stub-vision",
                                    "choices": [{"message": {"content": " 描述：一只猫 。 "}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):  # 静默
                return

        cls._server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()
        cls.base_url = f"http://127.0.0.1:{cls._server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._server.server_close()

    def test_available_and_describe(self):
        from src.media.vision import VisionEngine
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "a.jpg"
            img.write_bytes(b"jpeg-bytes")
            engine = VisionEngine(base_url=self.base_url, model="stub-vision", timeout=10)
            self.assertTrue(engine.available())
            desc = engine.describe(img)
            self.assertEqual(desc.text, "描述：一只猫 。")

    def test_unavailable_when_model_missing(self):
        from src.media.vision import VisionEngine
        engine = VisionEngine(base_url=self.base_url, model="not-there", timeout=5)
        self.assertFalse(engine.available())


# ── 队列 #26：OCR 质量门（乱码/过碎 ⇒ 也补视觉）────────────────────────────


class OcrQualityGateTests(unittest.TestCase):
    """阈值边界、乱码触发、好文本不触发（纯函数，不依赖 OCR/视觉）。"""

    def test_short_but_good_english_page_not_flagged(self):
        from src.media.descriptions import classify_ocr_quality
        q = classify_ocr_quality("README\nContributing\nApache-2.0 License\nDeepSeek Bot")
        self.assertFalse(q.garbled, "英文页 CJK 占比天然为 0，不应据此判乱码")

    def test_long_flowing_text_not_flagged(self):
        from src.media.descriptions import classify_ocr_quality
        text = "\n".join(["这是一段完整的中文说明文字，用于验证质量门不会误伤成句文本。"] * 5)
        self.assertFalse(classify_ocr_quality(text).garbled)

    def test_fragmented_short_lines_flagged(self):
        from src.media.descriptions import classify_ocr_quality
        q = classify_ocr_quality("设置\n通用\n连接器\n钱包\n安全存储\n权限\n消息渠道")
        self.assertTrue(q.garbled, "短行占比高 + 平均行长过短 ⇒ 过碎")

    def test_garbled_sample_flagged(self):
        from src.media.descriptions import classify_ocr_quality
        q = classify_ocr_quality("＜把链接粘贴到这里\n冷汽车\n灯T声音的\nN 沉默的\n层粘贴")
        self.assertTrue(q.garbled)

    def test_empty_text_not_flagged(self):
        from src.media.descriptions import classify_ocr_quality
        self.assertFalse(classify_ocr_quality("").garbled)

    def test_threshold_boundary_total_chars(self):
        """有效字数刚过阈值 ⇒ 不因 H1 触发（用单行好文本验证边界）。"""

        from src.media.descriptions import classify_ocr_quality
        just_above = "字" * 41
        self.assertFalse(classify_ocr_quality(just_above).garbled)
        self.assertTrue(classify_ocr_quality("字" * 10).garbled)


class GarbledSupplementTests(unittest.TestCase):
    """乱码/过碎 ⇒ 调视觉补描述；视觉失败 ⇒ 退回 OCR 原文（不伪造、不阻断）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="xbook-garb-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.img = self.tmp / "shot.png"
        self.img.write_bytes(b"png")

    def store(self, lines, vision):
        return MediaDescriptionStore(store_path=self.tmp / "d.json",
                                     engine=_StubEngine(lines), vision=vision)

    GARBLED_LINES = ["设置", "通用", "连接器", "钱包", "安全存储", "权限", "消息渠道"]

    def test_garbled_ocr_triggers_vision_supplement(self):
        vision = _StubVision("一张设置页面的截图，左侧是菜单项。")
        desc = self.store(self.GARBLED_LINES, vision).describe(self.img)
        self.assertEqual(vision.calls, 1)
        self.assertEqual(desc.source, "vision")
        self.assertIn("设置页面", desc.text)
        self.assertTrue(desc.ocr_text, "应保留 OCR 原文以便回溯")
        self.assertIn("连接器", desc.ocr_text)

    def test_good_ocr_does_not_trigger_vision(self):
        vision = _StubVision()
        good = ["这是一段足够长、成句的中文说明文本，用来证明质量门不会误伤它。"] * 3
        desc = self.store(good, vision).describe(self.img)
        self.assertEqual(vision.calls, 0)
        self.assertEqual(desc.source, "ocr")

    def test_garbled_vision_failure_falls_back_to_ocr(self):
        vision = _StubVision(fail=True)
        desc = self.store(self.GARBLED_LINES, vision).describe(self.img)
        self.assertEqual(desc.source, "ocr", "视觉失败应退回 OCR 原文，而不是丢弃")
        self.assertIn("连接器", desc.text)

    def test_cache_schema_migration_invalidates_old_entries(self):
        """旧 schema（v3）缓存应整体失效 ⇒ 重跑（从而给乱码图补视觉）。"""

        import json as _json
        from src.media.descriptions import DESCRIPTION_SCHEMA
        stale = self.tmp / "d.json"
        stale.write_text(_json.dumps({"schema": DESCRIPTION_SCHEMA - 1, "entries": [
            {"sha256": "x" * 64, "text": "旧缓存", "source": "ocr", "has_text": True}
        ]}), encoding="utf-8")
        vision = _StubVision("视觉描述")
        store = MediaDescriptionStore(store_path=stale, engine=_StubEngine(self.GARBLED_LINES),
                                      vision=vision)
        desc = store.describe(self.img)
        self.assertEqual(desc.source, "vision", "旧 schema 失效后应重判并补视觉")


class TranslationTests(unittest.TestCase):
    """用户要求：英文书签翻成中文、只翻日常用语（专有名词保留）。"""

    def test_should_translate_language_and_heuristics(self):
        from src.media.translate import should_translate
        self.assertTrue(should_translate("en"))
        self.assertTrue(should_translate("es"))
        self.assertFalse(should_translate("zh", "这是中文正文"))
        # 语言未知但字母为主 ⇒ 翻
        self.assertTrue(should_translate(None, "What if your X bookmarks could be read locally?"))
        self.assertFalse(should_translate(None, "这是中文正文，长度也够"))

    def test_prompt_protects_proper_nouns(self):
        from src.media.translate import TRANSLATE_PROMPT
        for word in ("软件名", "公司名", "产品名", "代码", "URL"):
            self.assertIn(word, TRANSLATE_PROMPT)
        self.assertIn("只翻译日常用语", TRANSLATE_PROMPT)

    def test_translate_returns_model_output(self):
        import threading, http.server, json as _json
        from src.media.translate import TranslationEngine

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = _json.dumps({"data": [{"id": "stub"}]}).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
                self.wfile.write(body)
            def do_POST(self):  # noqa: N802
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                body = _json.dumps({"choices": [{"message": {"content": " 这是译文 "}}]}).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
                self.wfile.write(body)
            def log_message(self, *a): return

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        engine = TranslationEngine(base_url=f"http://127.0.0.1:{server.server_address[1]}", model="stub",
                                   timeout=10)
        self.assertEqual(engine.translate("hello world"), "这是译文")
        self.assertEqual(engine.translate("  "), "")


class TranslationStoreTests(unittest.TestCase):
    """翻译缓存：原文不变不重翻；失败不伪造。"""

    class _Engine:
        def __init__(self, out="译文", fail=False):
            self.calls = 0; self._out = out; self._fail = fail
        def translate(self, text):
            self.calls += 1
            if self._fail:
                from src.media.vision import VisionError
                raise VisionError("boom")
            return self._out

    def test_cache_hit_skips_engine(self):
        import tempfile
        from pathlib import Path as _P
        from src.media.translate import TranslationStore
        with tempfile.TemporaryDirectory() as tmp:
            eng = self._Engine()
            store = TranslationStore(store_path=_P(tmp) / "t.json", engine=eng)
            self.assertEqual(store.translate("hello"), "译文")
            self.assertEqual(store.translate("hello"), "译文")
            self.assertEqual(eng.calls, 1)

    def test_failure_returns_empty(self):
        import tempfile
        from pathlib import Path as _P
        from src.media.translate import TranslationStore
        with tempfile.TemporaryDirectory() as tmp:
            store = TranslationStore(store_path=_P(tmp) / "t.json", engine=self._Engine(fail=True))
            self.assertEqual(store.translate("hello"), "")
            self.assertEqual(store.stats["failed"], 1)


class TaggingTests(unittest.TestCase):
    """队列 #28：只允许预设 12 标签、每篇 1–3 个、失败不伪造。"""

    def test_preset_tags_are_the_twelve(self):
        from src.media.tagging import PRESET_TAGS
        self.assertEqual(len(PRESET_TAGS), 12)
        for tag in ("AI大模型", "AI工具", "Agent自动化", "编程开发", "投资理财", "宏观经济",
                    "美股QDII", "iPhone技巧", "效率工具", "科技新闻", "设计创意", "生活随笔"):
            self.assertIn(tag, PRESET_TAGS)

    def test_parse_tags_keeps_only_preset_and_max_three(self):
        from src.media.tagging import parse_tags
        self.assertEqual(parse_tags('["AI工具","编程开发"]'), ("AI工具", "编程开发"))
        # 非预设一律丢弃
        self.assertEqual(parse_tags('["随便编的标签","AI工具"]'), ("AI工具",))
        # 超过 3 个截断，且按预设顺序
        many = '["科技新闻","AI工具","AI大模型","编程开发","投资理财"]'
        picked = parse_tags(many)
        self.assertLessEqual(len(picked), 3)
        self.assertEqual(picked, ("AI大模型", "AI工具", "编程开发"))

    def test_parse_tags_fallback_without_json(self):
        from src.media.tagging import parse_tags
        self.assertEqual(parse_tags("我觉得这篇属于 AI工具 吧"), ("AI工具",))

    def test_classify_returns_empty_when_unavailable(self):
        from src.media.tagging import TagClassifier
        classifier = TagClassifier(base_url="http://127.0.0.1:9", model="nope", timeout=1)
        self.assertEqual(classifier.classify("很长的正文内容"), ())

    def test_classify_parses_stub_response(self):
        import threading, http.server, json as _json
        from src.media.tagging import TagClassifier

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                b = _json.dumps({"data": [{"id": "stub"}]}).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            def do_POST(self):  # noqa: N802
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                b = _json.dumps({"choices": [{"message": {"content": '["AI工具","效率工具"]'}}]}).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            def log_message(self, *a): return

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        c = TagClassifier(base_url=f"http://127.0.0.1:{server.server_address[1]}", model="stub", timeout=5)
        self.assertEqual(c.classify("some content"), ("AI工具", "效率工具"))
