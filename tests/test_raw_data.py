"""``RawCollectorData`` / ``RawBookmarkItem`` 契约测试（Phase 3，Test A）。

对应任务书
----------
* §6 冻结契约：``collector`` / ``items`` / ``cursor`` 与 ``tweet_id`` / ``payload``；
* §18 Test A：最小 RawCollectorData 结构正确；
* §22 Collector 接口被复用（不另起第二套），且 Phase 3 的 Collector 只读。

全部离线：不读真实 ``data/``、不联网、不写盘。
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collector.base import Collector  # noqa: E402  (path bootstrap first)
from src.collector.fieldtheory import FieldTheoryCollector  # noqa: E402
from src.collector.raw_data import (  # noqa: E402
    RawBookmarkItem,
    RawCollectorData,
    RawDataContractError,
)


def make_item(tweet_id: str = "1900000000000000101", **overrides) -> RawBookmarkItem:
    payload = overrides.pop("payload", {"tweetId": tweet_id, "text": "sample"})
    return RawBookmarkItem(tweet_id=tweet_id, payload=payload, **overrides)


class RawBookmarkItemTests(unittest.TestCase):
    """§6.1：``tweet_id`` 负责身份，``payload`` 保留 Collector 原始结构。"""

    def test_minimal_item(self):
        item = make_item()
        self.assertEqual(item.tweet_id, "1900000000000000101")
        self.assertEqual(item.payload["text"], "sample")
        self.assertIsNone(item.enrichment)

    def test_payload_keeps_raw_camel_case(self):
        # payload 不得被 snake_case 化：FT 专属字段原样保留。
        item = make_item(
            payload={"tweetId": "1900000000000000101", "engagement": {"likeCount": 1}}
        )
        self.assertIn("engagement", item.payload)
        self.assertNotIn("like_count", item.payload)

    def test_empty_tweet_id_rejected(self):
        with self.assertRaises(RawDataContractError):
            make_item(tweet_id="")

    def test_non_str_tweet_id_rejected(self):
        with self.assertRaises(RawDataContractError):
            RawBookmarkItem(tweet_id=123, payload={})  # type: ignore[arg-type]

    def test_non_numeric_tweet_id_is_accepted(self):
        # 契约只要求「非空字符串」以容纳其它采集器（审计 A3：文档与实现对齐）。
        self.assertEqual(make_item(tweet_id="savebox:abc-123").tweet_id, "savebox:abc-123")

    def test_non_mapping_payload_rejected(self):
        with self.assertRaises(RawDataContractError):
            RawBookmarkItem(tweet_id="1", payload=["not", "a", "mapping"])  # type: ignore[arg-type]

    def test_enrichment_accepts_mapping_or_none(self):
        self.assertIsNone(make_item(enrichment=None).enrichment)
        self.assertEqual(make_item(enrichment={"articleText": "x"}).enrichment, {"articleText": "x"})

    def test_enrichment_rejects_other_types(self):
        with self.assertRaises(RawDataContractError):
            make_item(enrichment="article")  # type: ignore[arg-type]

    def test_item_is_frozen(self):
        item = make_item()
        with self.assertRaises(FrozenInstanceError):
            item.tweet_id = "other"  # type: ignore[misc]


class RawCollectorDataTests(unittest.TestCase):
    """§6：Collector 与 Normalizer 之间的边界，不是项目最终数据模型。"""

    def test_minimal_container(self):
        data = RawCollectorData(collector="fieldtheory", items=(make_item(),), cursor=None)
        self.assertEqual(data.collector, "fieldtheory")
        self.assertEqual(len(data.items), 1)
        self.assertIsNone(data.cursor)

    def test_items_coerced_to_tuple(self):
        # Phase 3 决策：list 入参被收敛为不可变 tuple，保证幂等语义。
        data = RawCollectorData(collector="fieldtheory", items=[make_item()])  # type: ignore[arg-type]
        self.assertIsInstance(data.items, tuple)

    def test_default_items_is_empty_tuple(self):
        data = RawCollectorData(collector="fieldtheory")
        self.assertEqual(data.items, ())
        self.assertEqual(len(data), 0)
        self.assertEqual(data.tweet_ids, ())

    def test_tweet_ids_preserves_order(self):
        data = RawCollectorData(
            collector="fieldtheory",
            items=(make_item("2"), make_item("1"), make_item("3")),
        )
        self.assertEqual(data.tweet_ids, ("2", "1", "3"))

    def test_empty_collector_rejected(self):
        with self.assertRaises(RawDataContractError):
            RawCollectorData(collector="", items=())

    def test_item_type_enforced(self):
        with self.assertRaises(RawDataContractError):
            RawCollectorData(collector="fieldtheory", items=({"tweet_id": "1"},))  # type: ignore[arg-type]

    def test_items_must_be_sequence(self):
        with self.assertRaises(RawDataContractError):
            RawCollectorData(collector="fieldtheory", items="not-a-sequence")  # type: ignore[arg-type]

    def test_cursor_must_be_str_or_none(self):
        self.assertEqual(RawCollectorData(collector="c", cursor="next").cursor, "next")
        for bad in ("", 0, []):
            with self.assertRaises(RawDataContractError):
                RawCollectorData(collector="c", cursor=bad)  # type: ignore[arg-type]

    def test_container_is_frozen(self):
        data = RawCollectorData(collector="fieldtheory")
        with self.assertRaises(FrozenInstanceError):
            data.collector = "other"  # type: ignore[misc]


class CollectorInterfaceTests(unittest.TestCase):
    """§22：复用既有 Protocol，只新增 ``collect()``，不设计第二套接口。"""

    def test_protocol_declares_collect(self):
        self.assertTrue(hasattr(Collector, "collect"))
        self.assertTrue(callable(Collector.collect))

    def test_protocol_keeps_phase5_surface(self):
        for name in ("check_ready", "sync", "read_bookmarks", "collect"):
            self.assertTrue(hasattr(Collector, name), name)

    def test_fieldtheory_collector_surface_matches_protocol_with_explicit_opt_in(self):
        """D-1=a（2026-10-13 用户裁定）之后的边界口径（原 ``…_surface_is_read_only``）。

        护栏**意图**不变（读路径离线、写操作显式 opt-in），表达随已批准的新语义更新
        （2026-10-15 裁决 ``D1-LA-4=A``，仅此一次）：

        * ① ``sync()`` / ``read_bookmarks()`` 存在且为**薄委托**（Collector 内无业务逻辑）；
        * ② ``collect()`` 读路径**不调用**上游 CLI（不触发 ``sync()``）；
        * ③ ``sync()`` 仅在**显式调用**时执行（opt-in）。
        """

        # ① 薄委托（源码可核查）：方法体只做一次同名转发。
        import inspect

        for name in ("check_ready", "sync", "read_bookmarks", "collect"):
            self.assertTrue(callable(getattr(FieldTheoryCollector, name)), name)
        for name in ("sync", "read_bookmarks"):
            self.assertIn(
                f"self._adapter.{name}(",
                inspect.getsource(getattr(FieldTheoryCollector, name)),
            )

        # ① 行为核查：返回值原样透传（无复制、无包装、无伪造）。
        class _FakeBookmark:
            tweet_id = "1900000000000000101"
            raw = {"tweetId": "1900000000000000101"}

        class _RecordingAdapter:
            def __init__(self):
                self.calls = []
                self.bookmarks = (_FakeBookmark(),)
                self.run_result = object()

            def read_bookmarks(self):
                self.calls.append(("read_bookmarks", {}))
                return self.bookmarks

            def sync(self, **options):
                self.calls.append(("sync", dict(options)))
                return self.run_result

        recorder = _RecordingAdapter()
        collector = FieldTheoryCollector(adapter=recorder)
        self.assertIs(collector.read_bookmarks(), recorder.bookmarks)
        self.assertIs(collector.sync(browser="none"), recorder.run_result)
        self.assertEqual(
            recorder.calls,
            [("read_bookmarks", {}), ("sync", {"browser": "none"})],
        )

        # ② 读路径 collect() 只读上游、绝不触发上游 CLI。
        recorder.calls.clear()
        self.assertEqual(
            collector.collect(with_enrichment=False).tweet_ids,
            ("1900000000000000101",),
        )
        self.assertEqual(recorder.calls, [("read_bookmarks", {})])

        # ③ 只有显式调用才执行：上一步无 sync 记录，显式调用后才有。
        collector.sync()
        self.assertEqual(
            recorder.calls,
            [("read_bookmarks", {}), ("sync", {})],
        )


if __name__ == "__main__":
    unittest.main()
