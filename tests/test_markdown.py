"""`src/markdown` 的验收测试（Phase 7）。

覆盖范围
--------
* 渲染（`render_markdown`）：frontmatter、各段落、占位、转义。
* 路径（`relative_output_path`）：年份/月份/文件名、缺日期回退。
* 写盘（`MarkdownWriter`）：首写、内容不变跳过、内容不同拒绝覆盖、单条失败隔离、状态推进。
* CLI `process`：端到端（离线桩）——M3 的核心断言（第二次不再产生新文件）。

运行方式（项目根目录）::

    .venv\\Scripts\\python.exe -m unittest discover -s tests -t . -v
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cli import EXIT_FAILURE, EXIT_OK, main as cli_main  # noqa: E402
from src.database import connect  # noqa: E402
from src.markdown import (  # noqa: E402

    MarkdownWriter,
    RenderOptions,
    build_frontmatter,
    relative_output_path,
    render_markdown,
)

STUB = PROJECT_ROOT / "tests" / "support" / "stub_fieldtheory.py"

POSTED_AT = "Mon Sep 14 01:24:21 +0000 2026"
UPMAP = {
    "tweetId": "1900000000000000101",
    "url": "https://x.com/sample/status/1900000000000000101",
    "text": "第一行\n第二行",
    "authorHandle": "sample",
    "authorName": "Sample Author",
    "authorProfileImageUrl": "https://pbs.twimg.com/profile_images/1/x.jpg",
    "postedAt": POSTED_AT,
    "bookmarkedAt": None,
    "syncedAt": "2026-09-16T00:00:01.000Z",
    "conversationId": "1900000000000000101",
    "language": "zh",
    "possiblySensitive": False,
    "engagement": {"likeCount": 10, "repostCount": 2, "replyCount": 1, "quoteCount": 0, "bookmarkCount": 5},
    "media": ["https://pbs.twimg.com/media/AAA.png"],
    "mediaObjects": (),
    "links": ["https://example.com/a", "https://example.com/a"],
    "tags": ["tag1"],
    "ingestedVia": "graphql",
    "sortIndex": "1",
    "author": {"id": "1", "handle": "sample", "name": "Sample Author"},
}
ENRICH = {
    "articleTitle": "测试文章",
    "articleText": "这是文章正文。",
    "primaryCategory": "tools",
    "folderNames": ["A", "B"],
}


import os as _os
_os.environ.setdefault("XBK_TRANSLATE", "0")   # 测试不调用真实本地模型（F-BYNLUY-03）

def render(overrides=None, enrich=None, **kwargs):
    up = dict(UPMAP)
    up.update(overrides or {})
    return render_markdown(up, enrich, RenderOptions(), **kwargs)


class RenderTests(unittest.TestCase):
    def test_frontmatter_has_required_keys_in_order(self):
        """队列 #27 起：frontmatter **只保留 title**（用户要求精简属性）。"""

        text = render()
        fm = text.split("---\n", 1)[1].split("\n---")[0]
        keys = [ln.split(":", 1)[0].strip() for ln in fm.split("\n") if ln.strip()]
        self.assertEqual(keys, ["title"])

    def test_frontmatter_values(self):
        text = render()
        self.assertIn("title: ", text)
        self.assertNotIn("tweet_id:", text)

    def test_sections_are_rendered(self):
        """队列 #24 起：`media` **不再是独立段落**，图片内嵌在 `## tweet` 之后。"""

        text = render()
        for section in ("## tweet", "## external_links", "## source"):
            self.assertIn(section, text)
        self.assertNotIn("## media", text)
        self.assertIn("> 第一行", text)
        self.assertIn("> 第二行", text)
        self.assertIn("https://pbs.twimg.com/media/AAA.png", text)
        self.assertIn("https://example.com/a", text)

    def test_media_is_inline_after_tweet_text(self):
        """图片紧跟正文（`## tweet` 内、`## thread` 之前），而不是独立段。"""

        text = render()
        tweet_at = text.index("## tweet")
        image_at = text.index("![")
        thread_at = text.index("## thread")
        self.assertLess(tweet_at, image_at)
        self.assertLess(image_at, thread_at)

    def test_media_captions_rendered_and_searchable(self):
        """caption = alt 文本（首行）＋ 引用块（OCR 文字）⇒ 纯文本、可检索。"""

        class _Desc:
            alt_text = "截图标题：粘贴链接"
            has_text = True
            caption = "截图标题：粘贴链接\n第二行说明"

        text = render(media_captions={"https://pbs.twimg.com/media/AAA.png": _Desc()})
        self.assertIn("![截图标题：粘贴链接]", text)
        self.assertIn("> 🖼 图 1：截图标题：粘贴链接", text)
        self.assertIn("> 第二行说明", text)

    def test_media_multiple_side_by_side_on_one_line(self):
        """多图并排 ⇒ 所有 `![]()` 写在同一行。"""

        text = render({"media": ["https://pbs.twimg.com/media/A.png",
                                 "https://pbs.twimg.com/media/B.png"]})
        image_lines = [line for line in text.split("\n") if line.startswith("![")]
        self.assertEqual(len(image_lines), 1, image_lines)
        self.assertEqual(image_lines[0].count("!["), 2, image_lines)

    def test_local_content_media_is_always_referenced(self):
        """队列 #27 回归：**有本地内容图就必须被引用**（且改用本地路径，不再留远程 URL）。"""

        text = render(media_files={"https://pbs.twimg.com/media/AAA.png": "assets/6000/abc.png"})
        self.assertIn("](assets/6000/abc.png)", text)
        self.assertNotIn("https://pbs.twimg.com/media/AAA.png", text)
        self.assertNotIn("## media", text)

    def test_media_placeholder_when_none(self):
        """无媒体 ⇒ **不渲染任何图片块**（旧版会给 `_无媒体_` 占位段）。"""

        text = render({"media": []})
        self.assertNotIn("![", text)
        self.assertNotIn("## media", text)

    def test_article_section_only_when_enrichment_present(self):
        self.assertIn("_未展开文章_", render(enrich=None))
        text = render(enrich=ENRICH)
        self.assertIn("## 文章标题：测试文章", text)
        self.assertIn("这是文章正文。", text)

    def test_links_are_deduplicated_in_section(self):
        text = render()
        self.assertEqual(text.count("- https://example.com/a"), 1)

    def test_pipe_is_escaped(self):
        text = render({"text": "a | b"})
        self.assertIn("a \\| b", text)

    def test_thread_section_renders_quoted_tweet(self):
        enrich = dict(ENRICH)
        enrich["quotedTweet"] = {
            "tweetId": "1900000000000000999",
            "text": "被引用的内容。",
            "authorHandle": "quoted_author",
        }
        text = render(enrich=enrich)
        self.assertIn("## thread", text)
        self.assertIn("@quoted_author", text)
        self.assertIn("`1900000000000000999`", text)
        self.assertIn("> 被引用的内容。", text)

    def test_thread_section_placeholder_when_missing(self):
        self.assertIn("_无引用推文_", render(enrich=None))
        self.assertIn("_无引用推文_", render(enrich=dict(ENRICH, quotedTweet=None)))

    def test_thread_section_falls_back_to_jsonl_quoted_tweet(self):
        """2026-10-16 接入：**无富化**时也必须渲染 JSONL 自带的 `quotedTweet`。

        回归：旧实现只读富化，旧注释还写着"JSONL 中不携带"——实机复采证明 **5/49 条 JSONL 携带**。
        JSONL 形状的 tweet id 键是 `id`（非 `tweetId`），必须一并识别。
        """

        text = render(
            {
                "quotedTweet": {
                    "id": "1933333333333333333",
                    "authorHandle": "jsonl_author",
                    "text": "来自 JSONL 的引用。",
                }
            },
            enrich=None,
        )
        self.assertIn("## thread", text)
        self.assertIn("@jsonl_author", text)
        self.assertIn("`1933333333333333333`", text)
        self.assertIn("> 来自 JSONL 的引用。", text)

    def test_thread_section_prefers_enrichment_over_jsonl(self):
        """两处都有时以**富化**为准（数据更全），不得因回退而改变既有优先级。"""

        text = render(
            {"quotedTweet": {"id": "1933333333333333999", "authorHandle": "jsonl_a", "text": "旧"}},
            enrich=dict(ENRICH, quotedTweet={
                "tweetId": "1900000000000000999", "authorHandle": "quoted_author", "text": "新",
            }),
        )
        self.assertIn("@quoted_author", text)
        self.assertNotIn("@jsonl_a", text)

    def test_ai_analysis_section_is_placeholder(self):
        text = render()
        self.assertIn("## ai_analysis", text)
        self.assertIn("_预留段：AI 分析将于 Phase 11 生成", text)


class PathTests(unittest.TestCase):
    def test_year_month_filename(self):
        rel = relative_output_path("123", "2026-09-14T01:24:21Z", RenderOptions())
        self.assertEqual(rel, Path("2026") / "09" / "20260914-123.md")

    def test_unknown_date_falls_back(self):
        rel = relative_output_path("123", None, RenderOptions())
        self.assertEqual(rel, Path("unknown") / "unknown" / "unknown-123.md")

    def test_custom_pattern(self):
        rel = relative_output_path(
            "123", "2026-09-14T01:24:21Z", RenderOptions(filename_pattern="note-{tweet_id}.md")
        )
        self.assertEqual(rel, Path("2026") / "09" / "note-123.md")


class WriterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="xbook-md-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.knowledge = self.tmp / "knowledge"
        self.knowledge.mkdir()
        self.raw = self.tmp / "data" / "raw"
        self.raw.mkdir(parents=True)

    def _archive(self, tweet_id, up=None, enrich=None):
        payload = {
            "schema_version": 1,
            "tweet_id": tweet_id,
            "source": "fieldtheory",
            "upstream": up or dict(UPMAP),
            "enrichment": enrich,
        }
        (self.raw / f"{tweet_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def _writer(self, options=None, status_updater=None):
        return MarkdownWriter(
            self.knowledge,
            options=options or RenderOptions(),
            status_updater=status_updater,
        )

    def test_write_creates_file_and_records_path(self):
        self._archive("1")
        calls = []
        writer = self._writer(status_updater=lambda i, s, p: calls.append((i, s, p)))
        stats = writer.run(["1"])
        self.assertEqual(stats.written, 1)
        self.assertEqual(stats.failed, 0)
        self.assertTrue((self.knowledge / "2026" / "09" / "20260914-1.md").is_file())
        self.assertEqual(calls[0][0], "1")
        self.assertEqual(calls[0][1], "PROCESSED")
        self.assertIsNotNone(calls[0][2])

    def test_second_run_creates_no_new_files(self):
        self._archive("1")
        writer = self._writer()
        first = writer.run(["1"])
        second = writer.run(["1"])
        self.assertEqual(first.written, 1)
        self.assertEqual(second.written, 0)
        self.assertEqual(second.unchanged, 1)
        files = sorted(p.name for p in (self.knowledge / "2026" / "09").glob("*.md"))
        self.assertEqual(files, ["20260914-1.md"])

    def test_different_content_refuses_overwrite(self):
        self._archive("1", up=dict(UPMAP, text="原版"))
        self._writer().run(["1"])
        self._archive("1", up=dict(UPMAP, text="改版"))
        stats = self._writer().run(["1"])
        self.assertEqual(stats.conflicts, 1)
        self.assertEqual(stats.written, 0)
        content = (self.knowledge / "2026" / "09" / "20260914-1.md").read_text(encoding="utf-8")
        self.assertIn("原版", content)

    def test_overwrite_allowed_flag(self):
        self._archive("1", up=dict(UPMAP, text="原版"))
        self._writer().run(["1"])
        self._archive("1", up=dict(UPMAP, text="改版"))
        stats = self._writer(options=RenderOptions(overwrite_existing=True)).run(["1"])
        self.assertEqual(stats.written, 1)
        content = (self.knowledge / "2026" / "09" / "20260914-1.md").read_text(encoding="utf-8")
        self.assertIn("改版", content)

    def test_missing_archive_fails_only_that_record(self):
        self._archive("1")
        stats = self._writer().run(["1", "missing"])
        self.assertEqual(stats.written, 1)
        self.assertEqual(stats.failed, 1)
        self.assertEqual(stats.errors[0][0], "missing")

    def test_default_loader_reads_real_archive_layout(self):
        self._archive("7", up=dict(UPMAP, tweetId="7", url="https://x.com/sample/status/7"))
        writer = MarkdownWriter(self.knowledge)  # 无注入 loader
        stats = writer.run(["7"])
        self.assertEqual(stats.written, 1)


class CliProcessTests(unittest.TestCase):
    """`python -m src.cli process` 端到端（离线桩 + 临时目录）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="xbook-cliproc-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.config = self.tmp / "config.yaml"
        self.upstream = self.tmp / "upstream"
        self.config.write_text(
            "version: 1\n"
            f"paths:\n  project_root: '{self.tmp.as_posix()}'\n"
            "  data_dir: 'data'\n  raw_dir: 'data/raw'\n  state_dir: 'data/state'\n"
            "  log_dir: 'data/logs'\n  knowledge_dir: 'knowledge/X-Bookmarks'\n"
            "collector:\n"
            f"  executable: '{sys.executable}'\n  executable_args: ['-B', '{STUB.as_posix()}']\n"
            f"  upstream_data_dir: '{self.upstream.as_posix()}'\n"
            "  auth:\n    method: 'firefox'\n    browser: 'firefox'\n"
            "markdown:\n"
            "  filename_pattern: '{yyyymmdd}-{tweet_id}.md'\n  frontmatter: true\n"
            "  include_sections: [tweet, media, article, external_links, metadata, source]\n"
            "  overwrite_existing: false\n"
            "logging:\n  level: 'INFO'\n  file_per_day: true\n  console: false\n",
            encoding="utf-8",
        )

    def _run(self, *argv):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli_main(["--config", str(self.config), *argv])
        return code, out.getvalue(), err.getvalue()

    def _conn(self):
        return connect(self.tmp / "data" / "state" / "state.db")

    def test_process_after_sync_generates_markdown_and_advances_state(self):
        self._run("sync")
        conn = self._conn()
        collected = conn.execute("SELECT COUNT(*) FROM bookmarks WHERE status='COLLECTED'").fetchone()[0]
        conn.close()
        self.assertEqual(collected, 3)

        code, out, _ = self._run("process")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("written       : 3", out)

        conn = self._conn()
        processed = conn.execute("SELECT COUNT(*) FROM bookmarks WHERE status='PROCESSED'").fetchone()[0]
        with_path = conn.execute("SELECT COUNT(*) FROM bookmarks WHERE markdown_path IS NOT NULL").fetchone()[0]
        conn.close()
        self.assertEqual(processed, 3)
        self.assertEqual(with_path, 3)
        # 布局按发帖年月分目录：fixture 中 101/103 在 9 月、102 在 6 月。
        md_files = sorted(p.name for p in (self.tmp / "knowledge" / "X-Bookmarks").rglob("*.md"))
        self.assertEqual(len(md_files), 3)
        self.assertTrue(
            (self.tmp / "knowledge" / "X-Bookmarks" / "2026" / "06" / "20260620-1900000000000000102.md").is_file()
        )

    def test_second_process_run_creates_no_new_files(self):
        """M3：第二次运行不产生新文件、不重写。"""

        self._run("sync")
        self._run("process")
        root = self.tmp / "knowledge" / "X-Bookmarks"
        first_files = sorted(str(p.relative_to(root)) for p in root.rglob("*.md"))
        code, out, _ = self._run("process")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("written       : 0", out)
        self.assertIn("unchanged     : 3", out)
        second_files = sorted(str(p.relative_to(root)) for p in root.rglob("*.md"))
        self.assertEqual(first_files, second_files)

    def test_process_missing_archive_fails_alone(self):
        self._run("sync")
        self._run("process")
        (self.tmp / "data" / "raw" / "1900000000000000101.json").unlink()
        conn = self._conn()
        conn.execute("UPDATE bookmarks SET status='COLLECTED' WHERE tweet_id='1900000000000000101'")
        conn.commit()
        conn.close()
        code, out, err = self._run("process")
        self.assertEqual(code, EXIT_FAILURE)
        self.assertIn("failed        : 1", out)
        self.assertIn("[fail]", err)

    def test_tweet_id_filter(self):
        self._run("sync")
        code, out, _ = self._run("process", "--tweet-id", "1900000000000000102")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("attempted     : 1", out)
        self.assertIn("written       : 1", out)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

class DeriveTitleTests(unittest.TestCase):
    """队列 #27 ②：真实标题优先；纯链接类用派生标签（用户选 A，不冒充原文标题）。"""

    def test_real_article_title_wins(self):
        from src.markdown.render import derive_title
        self.assertEqual(
            derive_title({"text": "https://t.co/x"}, {"articleTitle": "真正的文章标题"}),
            "真正的文章标题",
        )

    def test_prose_uses_first_sentence(self):
        from src.markdown.render import derive_title
        title = derive_title({"text": "别再问我拿啥下载视频了。这篇全给你兜住",
                              "authorName": "某作者",
                              "postedAt": "Thu Sep 13 00:00:00 +0000 2026"})
        self.assertEqual(title, "别再问我拿啥下载视频了")

    def test_bare_link_gets_derived_label(self):
        from src.markdown.render import derive_title
        title = derive_title({"text": "x.com/i/article/2029…", "authorName": "逸尘",
                              "postedAt": "Thu Mar 05 14:50:22 +0000 2026"})
        self.assertEqual(title, "逸尘 分享的链接（2026-03-05）")

    def test_frontmatter_and_h1_contain_title(self):
        from src.markdown.render import RenderOptions, render_markdown
        up = {"tweetId": "1", "text": "x.com/i/article/9…", "authorName": "逸尘",
              "postedAt": "Thu Mar 05 14:50:22 +0000 2026", "media": [], "links": []}
        text = render_markdown(up, None, RenderOptions())
        self.assertIn("title: 逸尘 分享的链接（2026-03-05）", text)
        self.assertIn("# 逸尘 分享的链接（2026-03-05）", text)


class XLinkCardTests(unittest.TestCase):
    """队列 #27 续：X 站内链（links 跳过的）用派生标签渲染成卡片，不伪造标题。"""

    def test_x_article_link_becomes_derived_card(self):
        from src.markdown.render import RenderOptions, render_markdown
        up = {"tweetId": "1", "text": "x.com/i/article/9…",
              "postedAt": "Thu Mar 05 14:50:22 +0000 2026",
              "links": ["http://x.com/i/article/2029556151587946496"]}
        text = render_markdown(up, None, RenderOptions())
        self.assertIn(
            "- [X 文章（2026-03-05）](http://x.com/i/article/2029556151587946496)", text
        )

    def test_other_bare_link_stays_plain(self):
        from src.markdown.render import RenderOptions, render_markdown
        up = {"tweetId": "1", "text": "看这个", "links": ["https://example.com/x"]}
        text = render_markdown(up, None, RenderOptions())
        self.assertIn("- https://example.com/x", text)


class LinkCoverCardTests(unittest.TestCase):
    """用户要求：纯链书签的链接卡片带封面图（渲染层，只认 image_path）。"""

    def test_cover_image_rendered_when_image_path_present(self):
        from src.markdown.render import RenderOptions, render_markdown
        up = {"tweetId": "1", "text": "看这个", "links": ["https://example.com/x"]}
        text = render_markdown(
            up, None, RenderOptions(),
            link_details={"https://example.com/x": {
                "title": "示例站点", "fetch_status": "FETCHED",
                "image_path": "X-Bookmarks/2026/09/assets/1/links/cover.jpg",
            }},
        )
        self.assertIn("  ![封面](X-Bookmarks/2026/09/assets/1/links/cover.jpg)", text)

    def test_no_cover_when_image_path_absent(self):
        from src.markdown.render import RenderOptions, render_markdown
        up = {"tweetId": "1", "text": "看这个", "links": ["https://example.com/x"]}
        text = render_markdown(up, None, RenderOptions(),
                               link_details={"https://example.com/x": {"title": "示例站点"}})
        self.assertNotIn("![封面]", text)


class TranslationRenderTests(unittest.TestCase):
    """用户要求：英文书签中文译文在前、原文在下；标题也翻译。"""

    UP = {"tweetId": "1", "text": "What if your bookmarks could be read locally?",
          "postedAt": "Thu Sep 13 00:00:00 +0000 2026", "media": [], "links": []}

    def test_chinese_first_then_original(self):
        from src.markdown.render import RenderOptions, render_markdown
        text = render_markdown(self.UP, None, RenderOptions(),
                               translation={"text": "如果书签能在本地阅读会怎样？",
                                            "title": "如果书签能在本地阅读会怎样"})
        self.assertIn("> 如果书签能在本地阅读会怎样？", text)
        self.assertIn("> **原文**", text)
        self.assertIn("> What if your bookmarks could be read locally?", text)
        self.assertLess(text.index("如果书签能在本地阅读"), text.index("**原文**"))
        self.assertIn("# 如果书签能在本地阅读会怎样", text)
        self.assertIn("title: 如果书签能在本地阅读会怎样", text)

    def test_no_translation_keeps_behaviour(self):
        from src.markdown.render import RenderOptions, render_markdown
        text = render_markdown(self.UP, None, RenderOptions())
        self.assertNotIn("**原文**", text)


class TagsRenderTests(unittest.TestCase):
    """队列 #28：frontmatter 写入预设标签（1–3 个）。"""

    def test_tags_in_frontmatter(self):
        from src.markdown.render import RenderOptions, render_markdown
        up = {"tweetId": "1", "text": "用 AI 工具提升效率", "media": [], "links": []}
        text = render_markdown(up, None, RenderOptions(), tags=["AI工具", "效率工具"])
        self.assertIn("tags: ", text)
        self.assertIn("AI工具", text)
        self.assertIn("效率工具", text)

    def test_no_tags_keeps_structure(self):
        from src.markdown.render import RenderOptions, render_markdown
        up = {"tweetId": "1", "text": "正文", "media": [], "links": []}
        text = render_markdown(up, None, RenderOptions())
        self.assertNotIn("tags:", text)


class LinkTitleAsNoteTitleTests(unittest.TestCase):
    """#30 审计更新：纯链书签无可用标题时，用外链自身标题当笔记标题。"""

    def test_link_title_used_when_tweet_has_no_title(self):
        from src.markdown.render import RenderOptions, render_markdown
        up = {"tweetId": "1", "text": "https://t.co/abc", "media": [], "links": ["https://example.com/a"]}
        text = render_markdown(up, None, RenderOptions(),
                               link_details={"https://example.com/a": {"title": "真实外链标题"}})
        self.assertIn("# 真实外链标题", text)

    def test_prose_title_wins_over_link_title(self):
        from src.markdown.render import RenderOptions, render_markdown
        up = {"tweetId": "1", "text": "这是一条有真实正文的推文，讲的是别的事情。", "media": [],
              "links": ["https://example.com/a"]}
        text = render_markdown(up, None, RenderOptions(),
                               link_details={"https://example.com/a": {"title": "外链标题"}})
        self.assertIn("# 这是一条有真实正文的推文", text)


class InvestTagTimePropertyTests(unittest.TestCase):
    """用户要求：投资理财（及财经相关）标签的书签，frontmatter 带推文时间属性。"""

    UP = {"tweetId": "1", "text": "纳指定投策略", "media": [], "links": [],
          "postedAt": "Thu Sep 13 01:24:21 +0000 2026"}

    def test_invest_tag_gets_posted_at(self):
        from src.markdown.render import RenderOptions, render_markdown
        text = render_markdown(self.UP, None, RenderOptions(), tags=["投资理财"])
        self.assertIn("posted_at: 2026-09-13T01:24:21Z", text)

    def test_non_finance_tag_has_no_posted_at(self):
        from src.markdown.render import RenderOptions, render_markdown
        text = render_markdown(self.UP, None, RenderOptions(), tags=["AI工具"])
        self.assertNotIn("posted_at:", text)
