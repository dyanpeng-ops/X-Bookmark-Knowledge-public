"""封面卡管线（队列 #30 / F-BYNLUY-01 步骤 1）：抓 `og:image` → 下载 → 落库。

流程（每条外链）：
1. 取 `resolved_url`（缺失则原始 URL）；
2. GET 页面 HTML（stdlib、timeout、失败即跳过）；
3. `extract_og_image(html, url)` 拿封面 URL（拿不到即跳过）；
4. `download_cover()` 落到 `assets/<tweet_id>/links/<hash>.cover.<ext>`；
5. 把 `image_url` 写回 `external_links`（下载成功才写，**失败不伪造**）。

设计取舍：**只处理需要封面的行**（增量）；任何一步失败都只影响该条；
封面下载失败时仍记录 `image_url`（下次可重试），但**不写本地路径假数据**。
"""

from __future__ import annotations

import sqlite3
import urllib.request
from pathlib import Path

from src.external.covers import DEFAULT_TIMEOUT, download_cover
from src.external.fetcher import extract_og_image

__all__ = ["fill_link_covers", "link_assets_dir"]

#: 页面下载上限（2 MB）——只取首部就够，og:image 在 <head> 里。
MAX_HTML_BYTES = 2 * 1024 * 1024


def link_assets_dir(knowledge_dir: str | Path, tweet_id: str, created_at: str | None) -> Path:
    """外链封面目录：`<知识库>/<YYYY>/<MM>/assets/<tweet_id>/links`（与既有资产布局一致）。"""

    from src.markdown.render import date_parts

    year, month, _ = date_parts(created_at)
    return Path(knowledge_dir) / year / month / "assets" / str(tweet_id) / "links"


def _fetch_html(url: str, *, timeout: float = DEFAULT_TIMEOUT) -> str | None:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (bookmark-cover)"})
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            payload = resp.read(MAX_HTML_BYTES)
        return payload.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - 单条失败不影响整批
        return None


def fill_link_covers(
    conn: sqlite3.Connection,
    knowledge_dir: str | Path,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    limit: int | None = None,
) -> dict[str, int]:
    """为 `external_links` 里**已抓取但无封面**的外链补齐封面（增量、逐条隔离）。

    返回统计：``{"candidates", "with_image_url", "downloaded", "failed"}``。
    """

    stats = {"candidates": 0, "with_image_url": 0, "downloaded": 0, "failed": 0}
    rows = conn.execute(
        "SELECT l.tweet_id, l.url, l.resolved_url, l.image_url, b.created_at "
        "FROM external_links l LEFT JOIN bookmarks b ON b.tweet_id = l.tweet_id "
        "WHERE l.fetch_status = 'FETCHED' AND (l.image_url IS NULL OR l.image_url = '')"
    ).fetchall()
    for tweet_id, url, resolved, _image_url, created_at in rows:
        if limit is not None and stats["candidates"] >= limit:
            break
        stats["candidates"] += 1
        page_url = str(resolved or url or "").strip()
        html = _fetch_html(page_url, timeout=timeout)
        if not html:
            stats["failed"] += 1
            continue
        image_url = extract_og_image(html, page_url)
        if not image_url:
            stats["failed"] += 1
            continue
        stats["with_image_url"] += 1
        target_dir = link_assets_dir(knowledge_dir, str(tweet_id), created_at)
        path = download_cover(image_url, target_dir, timeout=timeout)
        if path is None:
            stats["failed"] += 1
        else:
            stats["downloaded"] += 1
        try:
            conn.execute(
                "UPDATE external_links SET image_url = ? WHERE tweet_id = ? AND url = ?",
                (image_url, tweet_id, url),
            )
        except sqlite3.Error:
            stats["failed"] += 1
    conn.commit()
    return stats
