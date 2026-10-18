"""Markdown 产物层（Phase 7）：把一条书签渲染为一份独立 Markdown 文件。

边界
----
* 只做"渲染 + 写盘"，不联网、不下载媒体。
* `## media` 段落可接收 Phase 8 本地化结果（`render_markdown(..., media_files=...)`）：
  命中本地文件时引用知识库内的相对路径，否则保留远程 URL。
* 幂等：同路径文件若内容一致则跳过（不覆盖）；内容不同且 `overwrite_existing=false` 时抛错。
* 来源数据：
  - 原始与富化载荷来自 `data/raw/{tweet_id}.json`（其中 `upstream` 是上游 JSONL 记录、
    `enrichment` 是 `fieldtheory list|show --json` 的富化记录，可含 article 正文与 quoted tweet）；
  - 数据库行（`BookmarkRecord`）提供 `markdown_path` 等状态。
"""

from __future__ import annotations

import html
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from src.collector.contract import parse_twitter_datetime

__all__ = [
    "DEFAULT_FILENAME_PATTERN",
    "YEAR_MONTH_LAYOUT",
    "MarkdownError",
    "MarkdownRenderError",
    "MarkdownConflictError",
    "RenderOptions",
    "render_markdown",
    "build_frontmatter",
    "section_names_for",
    "relative_output_path",
    "date_parts",
]

logger = logging.getLogger(__name__)

DEFAULT_FILENAME_PATTERN = "{yyyymmdd}-{tweet_id}.md"
YEAR_MONTH_LAYOUT = "year_month"

FRONTMATTER_KEYS: tuple[str, ...] = (
    "title",
    "tags",
    "tags_ai",
    "posted_at",
)

#: `## external_links` 段落里显示的状态标签（Phase 9）；`PENDING` 不显示备注。
_LINK_STATUS_LABELS: Mapping[str, str] = {"FAILED": "抓取失败", "SKIPPED": "已跳过"}


@dataclass(frozen=True)
class _SectionContext:
    """渲染所需的、来自 Markdown 之外的产物（媒体本地化、外链正文）。"""

    media_files: Mapping[str, str] | None = None
    link_details: Mapping[str, Mapping[str, Any]] | None = None
    #: 配图描述：`{source_url: MediaDescription}`（队列 #24 A 阶段：OCR 文字；B 阶段：视觉描述）
    media_captions: Mapping[str, Any] | None = None
    #: 本地翻译产物：`{"text": 中文译文, "title": 中文标题}`（用户要求：英文书签翻中文）
    translation: Mapping[str, Any] | None = None
    #: Phase 11：AI 分析（summary/insights/tags_ai）
    ai_analysis: Any | None = None


def _now_iso(now: Any = None) -> str:
    if now is None:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(now, datetime):
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(now)


class MarkdownError(RuntimeError):
    """Markdown 渲染或写入失败。"""


class MarkdownRenderError(MarkdownError):
    """渲染阶段失败（来源数据不完整）。"""


class MarkdownConflictError(MarkdownError):
    """目标文件已存在且内容不同，且不允许覆盖。"""


@dataclass(frozen=True)
class RenderOptions:
    """一次渲染的参数。"""

    filename_pattern: str = DEFAULT_FILENAME_PATTERN
    layout: str = YEAR_MONTH_LAYOUT
    frontmatter: bool = True
    # 顺序与 config.example.yaml 的 markdown.include_sections 保持一致。
    #: 默认**不再**有独立 `media` 段 —— 图片改为内嵌在 `tweet` 段之后（队列 #24 A 阶段）。
    #: 若确需旧的独立媒体段，显式把 "media" 加回本元组即可（向后兼容）。
    include_sections: tuple[str, ...] = (
        "tweet",
        "thread",
        "article",
        "external_links",
        "ai_analysis",
        "source",
    )
    overwrite_existing: bool = False
    clock: Callable[[Any], str] = _now_iso


# ── 工具 ─────────────────────────────────────────────────────────────────────


def _md_escape(text: str) -> str:
    """只转义最可能在 Markdown 中断句的字符；保留中文与链接。"""

    value = str(text).replace("\r\n", "\n").replace("\r", "\n")
    # 先转义反斜杠再转义竖线，避免把 `|`→`\|` 再被误转成 `\\|`。
    return value.replace("\\", "\\\\").replace("|", "\\|")


def _escape_link_text(text: str) -> str:
    """链接文字的安全化：`[` / `]` 与换行会破坏 `[text](url)`，必须收敛。"""

    value = str(text).replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    return " ".join(value.split())


def _note_text(status: str, note: str) -> str:
    """去掉 `skipped: ` 前缀，避免渲染成"已跳过：skipped: xxx"。"""

    if status == "SKIPPED" and note.lower().startswith("skipped:"):
        return note.split(":", 1)[1].strip()
    return note


def _iso_created_at(upstream: Mapping[str, Any]) -> str | None:
    """把 `postedAt`（RFC822 风格）转成 ISO UTC；失败返回 None。"""

    raw = upstream.get("postedAt")
    if not raw:
        return None
    try:
        parsed = parse_twitter_datetime(raw)
    except Exception:  # noqa: BLE001 - 渲染不应因单个字段崩溃
        logger.warning("unparseable postedAt %r", raw)
        return None
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _engagement_lines(engagement: Mapping[str, Any]) -> list[str]:
    labels = [
        ("likeCount", "Likes"),
        ("repostCount", "Reposts"),
        ("replyCount", "Replies"),
        ("quoteCount", "Quotes"),
        ("bookmarkCount", "Bookmarks"),
    ]
    return [
        f"- {label}: {int(engagement.get(key) or 0)}"
        for key, label in labels
        if engagement.get(key) is not None
    ]


def section_names_for(options: RenderOptions) -> list[str]:
    """返回应包含的段落名（已按 `include_sections` 去重、保序）。"""

    result: list[str] = []
    for name in options.include_sections:
        if name not in result:
            result.append(name)
    return result


#: 一条推文正文若"只有链接/转发短链"，视为**无可读标题**的类目（队列 #27 ②）。
_BARE_LINK_RE = re.compile(r"^(?:https?://|x\.com/|t\.co/|www\.)", re.IGNORECASE)


def _looks_like_bare_link(text: str) -> bool:
    stripped = str(text or "").strip()
    if not stripped:
        return True
    # 去掉所有 URL（含无 scheme 的域名与 X 短链）后若几乎没剩内容，就是"纯链接"
    without_urls = re.sub(r"(?:https?://|www\.)\S+", "", stripped)
    without_urls = re.sub(r"\b(?:x\.com|twitter\.com|t\.co)/\S*", "", without_urls)
    without_urls = re.sub(r"[…\.\s]+", "", without_urls)
    return len(without_urls) < 10


def derive_title(
    upstream: Mapping[str, Any],
    enrichment: Mapping[str, Any] | None = None,
    link_title: str | None = None,
    translation: Mapping[str, Any] | None = None,
) -> str | None:
    """给出可读标题（队列 #27 ②，用户选 A：允许**派生标签**，但绝不冒充原文标题）。

    优先级：
    1. 真实标题（`enrichment.articleTitle`）；
    2. 中文译文首句（若存在非空翻译，优先使用译文避免外语截断）；
    3. 正文**首句**（正文是真实文字时取首句，截断 40 字）；
    4. 纯链书签无可用标题时，用外链自身标题（排除通用壳标题）；
    5. 正文为空 / 纯链接 ⇒ **派生标签**：`<作者> 分享的链接（YYYY-MM-DD）`
       —— 事实性描述（作者＋日期＋类型），不伪造文章名。
    """

    enrich = enrichment or {}
    real = str(enrich.get("articleTitle") or "").strip()
    if real:
        return html.unescape(real)

    # 优先检查译文首句
    trans = translation or {}
    zh_text = str(trans.get("text") or "").strip()
    if zh_text and not _looks_like_bare_link(zh_text):
        first_zh = re.split(r"[。！？!?\n]", zh_text, maxsplit=1)[0].strip()
        if first_zh:
            first_zh = html.unescape(first_zh)
            return first_zh[:40] + ("…" if len(first_zh) > 40 else "")

    text = str(upstream.get("text") or "").strip()
    if text and not _looks_like_bare_link(text):
        first = re.split(r"[。！？!?\n]", text, maxsplit=1)[0].strip()
        if first:
            first = html.unescape(first)
            return first[:40] + ("…" if len(first) > 40 else "")

    # 队列 #30 审计更新：纯链书签无可用标题时，用**外链自身标题**（og:title/<title>）当标题
    external = str(link_title or "").strip()
    if external:
        clean_ext = html.unescape(external)
        if clean_ext.lower() not in ("- youtube", "youtube", "twitter", "x", "github"):
            return clean_ext[:80]
    author = str(upstream.get("authorName") or upstream.get("authorHandle") or "").strip()
    created = _iso_created_at(upstream) or ""
    day = created[:10] if created else ""
    label = "分享的链接"
    if not author and not day:
        return None
    return f"{author} {label}（{day}）".strip()


def build_frontmatter(
    upstream: Mapping[str, Any], enrichment: Mapping[str, Any] | None
) -> dict[str, Any]:
    """frontmatter **只保留可读标题**（用户要求：精简笔记属性）。"""

    return {"title": derive_title(upstream, enrichment)}


def date_parts(created_at: str | None) -> tuple[str, str, str]:
    """把 ISO `created_at` 拆成知识库布局用的 `(年, 月, YYYYMMDD)`。

    缺失或不可解析时三点都回退为 `unknown`（与 `relative_output_path` 同一约定，
    Phase 8 的媒体 `assets/` 目录复用它，保证两处布局永远一致）。
    """

    if not created_at:
        return "unknown", "unknown", "unknown"
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(created_at))
    if not match:
        return "unknown", "unknown", "unknown"
    year, month, day = match.groups()
    return year, month, year + month + day


#: 文件名里不允许/不友好的字符（Obsidian 与常见文件系统）
_UNSAFE_FILENAME_RE = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def sanitize_filename(title: str, max_len: int = 50) -> str:
    """把标题清洗成可用的文件名（队列 #27：按标题命名）。

    * 非法字符（`\\ / : * ? " < > |` 与换行/制表符）→ 空格；
    * 连续空白折叠；去掉首尾空格、点号与省略号（避免跨平台尾部点与特殊符问题）；
    * 超长按 ``max_len`` 截断（按字符，不切坏多字节）。
    """

    cleaned = _UNSAFE_FILENAME_RE.sub(" ", html.unescape(str(title or ""))).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .…_-")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip(" .…_-")
    return cleaned


def relative_output_path(
    tweet_id: str,
    created_at: str | None,
    options: RenderOptions,
    title: str | None = None,
) -> Path:
    """计算知识库内的相对路径。

    * `filename_pattern` 含 `{title}` 且标题可用 ⇒ 格式化标题；
    * 标题为空/清洗后为空 ⇒ **回退**无标题形式（如 `{yyyymmdd}-{tweet_id}.md`，不留悬空下划线）。

    `created_at` 必须是 ISO-8601 字符串（或 None）；年份/月份缺失时落到 `unknown/unknown/`。
    """

    year, month, yyyymmdd = date_parts(created_at)
    pattern = options.filename_pattern
    if "{tweet_id}" not in pattern:
        pattern = "{tweet_id}_" + pattern
    safe_title = sanitize_filename(title or "")
    if "{title}" in pattern:
        if safe_title:
            filename = pattern.format(
                title=safe_title, yyyymmdd=yyyymmdd, tweet_id=tweet_id
            )
        else:   # 无标题 ⇒ 回退日期-id（不留悬空符号）
            fallback = pattern.replace("_{title}", "").replace("-{title}", "").replace("{title}", "")
            filename = fallback.format(yyyymmdd=yyyymmdd, tweet_id=tweet_id)
            if not filename.endswith(".md"):
                filename += ".md"
    else:
        filename = pattern.format(yyyymmdd=yyyymmdd, tweet_id=tweet_id)
    return Path(year) / month / filename


# ── 段落渲染 ─────────────────────────────────────────────────────────────────


def _render_section_tweet(
    upstream: Mapping[str, Any], context: "_SectionContext | None" = None
) -> str:
    text = html.unescape(str(upstream.get("text") or "")).strip()
    if not text:
        body = "> （本条没有可展示的文本）"
    else:
        lines = _md_escape(text).split("\n")
        body = "\n".join(f"> {line}" for line in lines) if len(lines) > 1 else f"> {lines[0]}"
    translation = (context.translation if context is not None else None) or {}
    zh = str(translation.get("text") or "").strip()
    if zh:
        # 用户要求：中文译文放最前，原文保留在下面（可对照，不丢信息）
        zh_lines = zh.split("\n")
        zh_block = "\n".join(f"> {line}" for line in zh_lines)
        body = f"{zh_block}\n\n> **原文**\n>\n{body}"
    inline = _render_inline_media(upstream, context)
    return f"{body}\n\n{inline}" if inline else body


def _render_inline_media(
    upstream: Mapping[str, Any], context: "_SectionContext | None" = None
) -> str:
    """**内嵌**媒体（队列 #24 A 阶段）：图片紧跟正文、多图并排、每图带可检索 caption。

    * 图片：所有 `![](path)` 写在同一行 ⇒ Markdown 并排渲染；
    * alt 文本 = 描述首行（无描述时给中性占位，**不伪造**）；
    * 下方引用块写 "🖼 图 N：<OCR 文字>"，纯文本 ⇒ **可被全文搜索**；
    * 视频/GIF：本机无 ffmpeg ⇒ A 阶段退化为**原链**（不静默丢信息），B 阶段再补首帧。
    """

    urls = [str(item) for item in (upstream.get("media") or ())]
    if not urls:
        return ""
    files = (context.media_files if context is not None else None) or {}
    captions = (context.media_captions if context is not None else None) or {}
    images: list[str] = []
    caption_lines: list[str] = []
    for index, url in enumerate(urls, 1):
        target = files.get(url) or url
        desc = captions.get(url)
        alt = str(getattr(desc, "alt_text", "") or "") if desc is not None else ""
        alt = alt.replace("\n", " ").strip() or "配图"
        images.append(f"![{_md_escape(alt)}]({target})")
        if desc is not None and bool(getattr(desc, "has_text", False)):
            caption = str(getattr(desc, "caption", "") or "").strip()
            if caption:
                first, *rest = caption.split("\n")
                caption_lines.append(f"> 🖼 图 {index}：{first}")
                caption_lines.extend(f"> {line}" for line in rest if line.strip())
    parts: list[str] = []
    if images:
        parts.append(" ".join(images))
    if caption_lines:
        parts.append("\n".join(caption_lines))
    return "\n\n".join(parts)


def _render_section_media(
    upstream: Mapping[str, Any], media_files: Mapping[str, str] | None = None
) -> str:
    """媒体段落。

    `media_files`：`{source_url: 相对本 Markdown 文件的路径}`（Phase 8 本地化后的产物）。
    命中则引用知识库内的本地相对路径，未命中则保留远程 URL——本地化失败或未开启时
    **不丢信息**（与 Phase 9 外链"失败也保留原始 URL"同一原则）。
    """

    urls = upstream.get("media") or ()
    if not urls:
        return "_无媒体_"
    mapping = media_files or {}
    blocks: list[str] = []
    for url in urls:
        key = str(url)
        local = mapping.get(key)
        blocks.append(f"![]({local})" if local else f"![]({key})")
        blocks.append("")
    return "\n".join(blocks).rstrip()


#: 单行正文的最大长度（超过则在句末断开，避免 Obsidian 显示成一坨"二进制"观感）。
MAX_LINE_CHARS = 120


def wrap_long_text(text: str, width: int = MAX_LINE_CHARS) -> str:
    """把无换行的长文本按**句末**断行（中文倾向，兼容英文句号）；不改内容语义。"""

    import re as _re

    raw = str(text or "").strip()
    if not raw:
        return ""
    sentences = _re.split(r"(?<=[。！？!?；;\n])", raw)
    lines: list[str] = []
    current = ""
    for sentence in sentences:
        piece = sentence.strip()
        if not piece:
            continue
        if not current:
            current = piece
        elif len(current) + len(piece) <= width:
            current += piece
        else:
            lines.append(current)
            current = piece
        # 单句本身超长 ⇒ 硬切
        while len(current) > width * 3:
            lines.append(current[: width * 3])
            current = current[width * 3:]
    if current:
        lines.append(current)
    return "\n\n".join(lines)


def _render_section_article(enrichment: Mapping[str, Any] | None) -> str:
    if not enrichment:
        return "_未展开文章_"
    title = enrichment.get("articleTitle")
    body = enrichment.get("articleText")
    if not body:
        return f"- 标题：{_md_escape(title) if title else '（无）'}"
    parts: list[str] = []
    if title:
        parts.append(f"## 文章标题：{_md_escape(title)}")
    parts.append(wrap_long_text(_md_escape(body)))     # 超长单行按句末断行（用户反馈"像二进制"）
    return "\n\n".join(parts)


#: X/推特站内链（`links` 抓取按域名跳过）→ 用派生标签做成卡片（用户要求「做卡片」）。
_X_INTERNAL_RE = re.compile(
    r"^https?://(?:www\.)?(?:x\.com|twitter\.com)/", re.IGNORECASE
)


def _x_link_label(url: str, upstream: Mapping[str, Any]) -> str:
    """为 X 站内链生成**派生标签**（不伪造原文标题）：X 文章（YYYY-MM-DD）。"""

    created = _iso_created_at(upstream) or ""
    day = created[:10]
    if "/i/article/" in url:
        kind = "X 文章"
    elif "/i/" in url:
        kind = "X 链接"
    else:
        kind = "X 推文"
    return f"{kind}（{day}）" if day else kind


def _render_section_external_links(
    upstream: Mapping[str, Any],
    link_details: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    """外链段落。

    `link_details`：`{原始 URL: {title, resolved_url, content_path, fetch_status, error_message}}`
    （Phase 9 外链层产物，`content_path` 已是相对本 Markdown 文件的路径）。
    缺失该映射（或某条外链仍为 `PENDING`）时，输出与 Phase 7 完全一致的纯 URL 列表——
    未跑 `links` 时 Markdown 不会凭空变化。
    """

    raw_links = [str(url) for url in (upstream.get("links") or ()) if str(url).strip()]
    details = link_details or {}
    for url in details:
        if url not in raw_links:
            raw_links.append(url)
    text = upstream.get("text") or ""
    if text:
        for u in re.findall(r"https?://[^\s<>\"'，。；！？）\]\}]+", text):
            cleaned = u.rstrip(".,;!?。，！？；:）)］]｝}>\"'”’…")
            if cleaned and cleaned not in raw_links:
                raw_links.append(cleaned)

    if not raw_links:
        return "_无外链_"
    seen: list[str] = []
    for url in raw_links:
        if url not in seen:
            seen.append(url)

    blocks: list[str] = []
    for url in seen:
        detail = details.get(url)
        info: Mapping[str, Any] = detail if isinstance(detail, Mapping) else {}
        title = html.unescape(str(info.get("title") or "")).strip()
        if not title and _X_INTERNAL_RE.match(url):
            title = _x_link_label(url, upstream)      # X 站内链：派生卡片（不伪造标题）
        blocks.append(f"- [{_escape_link_text(title)}]({url})" if title else f"- {url}")
        cover = str(info.get("image_path") or "").strip()
        if cover:
            # 用户要求：纯链书签抓链接图片做封面卡（image_path 已是 vault 相对路径）
            blocks.append(f"  ![封面]({cover})")

        status = str(info.get("fetch_status") or "").strip().upper()
        resolved = str(info.get("resolved_url") or "").strip()
        content_path = str(info.get("content_path") or "").strip()
        note = _note_text(status, str(info.get("error_message") or "").strip())

        if resolved and resolved != url:
            blocks.append(f"  - 最终地址：{resolved}")
        if status == "FETCHED":
            if content_path:
                blocks.append(f"  - 正文：`{content_path}`")
            if note:
                blocks.append(f"  - 备注：{_md_escape(note)}")
        elif status in _LINK_STATUS_LABELS and note:
            blocks.append(f"  - {_LINK_STATUS_LABELS[status]}：{_md_escape(note)}")
    return "\n".join(blocks)


def _render_section_metadata(upstream: Mapping[str, Any], enrichment: Mapping[str, Any] | None) -> str:
    lines: list[str] = []
    engagement = upstream.get("engagement") or {}
    eng_lines = _engagement_lines(engagement)
    author = upstream.get("author") or {}
    if author.get("name"):
        lines.append(f"- 作者：{_md_escape(author['name'])}（@{_md_escape(upstream.get('authorHandle'))}）")
    if upstream.get("postedAt"):
        lines.append(f"- 发布于：`{_md_escape(str(upstream['postedAt']))}`")
    if upstream.get("language"):
        lines.append(f"- 语言：{upstream['language']}")
    if upstream.get("conversationId"):
        lines.append(f"- 会话 ID：`{upstream['conversationId']}`")
    if eng_lines:
        lines.append("- 互动：" + "；".join(eng_lines))
    enriched = enrichment or {}
    if enriched.get("primaryCategory"):
        lines.append(f"- 分类：{enriched['primaryCategory']}")
    folders = list(enriched.get("folderNames") or ())
    if folders:
        lines.append(f"- 文件夹：{', '.join(str(f) for f in folders)}")
    return "\n".join(lines) if lines else "_无更多元数据_"


def _render_section_thread(
    enrichment: Mapping[str, Any] | None,
    upstream: Mapping[str, Any] | None = None,
) -> str:
    """引用推文/线程上下文。

    数据源优先级（2026-10-16 起）：
    1. **富化** ``enrichment['quotedTweet']``（`fieldtheory list|show --json`）；
    2. **JSONL** ``upstream['quotedTweet']`` —— 旧注释称"JSONL 中不携带"，**已证伪**：
       实机复采显示 **5/49** 条 JSONL 记录确实携带 ``quotedTweet``。

    两种形状的键名不同（富化用 ``tweetId``；JSONL 用 ``id``），两者都认。
    """

    quoted = (enrichment or {}).get("quotedTweet") or (upstream or {}).get("quotedTweet")
    if not isinstance(quoted, Mapping) or not quoted:
        return "_无引用推文_"
    lines: list[str] = []
    header: list[str] = []
    if quoted.get("authorHandle"):
        header.append(f"@{_md_escape(str(quoted['authorHandle']))}")
    quoted_id = quoted.get("tweetId") or quoted.get("id")
    if quoted_id:
        header.append(f"`{str(quoted_id)}`")
    if header:
        lines.append("- 引用：" + " ".join(header))
    text = html.unescape(str(quoted.get("text") or "")).strip()
    if text:
        lines.extend(f"> {line}" for line in _md_escape(text).split("\n"))
    return "\n".join(lines) if lines else "_无引用推文内容_"


def _render_section_ai_analysis(analysis: Any | None = None) -> str:
    """Phase 11：有 AI 分析结果就渲染三段（要点/建议/扩展标签）；否则保留占位。

    失败/未启用时**保留占位文案**，绝不伪造分析内容。
    """

    if analysis is not None:
        try:
            body = analysis.to_markdown()
        except Exception:  # noqa: BLE001 - 分析对象异常不该中断渲染
            body = ""
        if body:
            return body
    return "_预留段：AI 分析将于 Phase 11 生成（当前不含任何分析内容）_"


def _render_section_source(upstream: Mapping[str, Any]) -> str:
    url = upstream.get("url")
    if not url:
        return "_无来源链接_"
    return f"原文：<{url}>"


_SECTION_RENDERERS: dict[str, Any] = {
    "tweet": lambda u, e, c: _render_section_tweet(u, c),
    "thread": lambda u, e, c: _render_section_thread(e, u),
    "media": lambda u, e, c: _render_section_media(u, c.media_files),
    "article": lambda u, e, c: _render_section_article(e),
    "external_links": lambda u, e, c: _render_section_external_links(u, c.link_details),
    "metadata": lambda u, e, c: _render_section_metadata(u, e),
    "ai_analysis": lambda u, e, c: _render_section_ai_analysis(getattr(c, "ai_analysis", None)),
    "source": lambda u, e, c: _render_section_source(u),
}


def render_markdown(
    upstream: Mapping[str, Any],
    enrichment: Mapping[str, Any] | None,
    options: RenderOptions,
    *,
    media_files: Mapping[str, str] | None = None,
    link_details: Mapping[str, Mapping[str, Any]] | None = None,
    media_captions: Mapping[str, Any] | None = None,
    translation: Mapping[str, Any] | None = None,
    tags: "Sequence[str] | None" = None,
    ai_analysis: Any | None = None,
) -> str:
    """渲染整份 Markdown 文本（含可选 frontmatter + 各段落）。

    `media_files` 为可选的 `{source_url: 相对本文件的路径}` 映射（Phase 8 媒体本地化），
    缺省时图片沿用远程 URL。

    `media_captions` 为可选的 `{source_url: MediaDescription}`（队列 #24 A 阶段）：
    图片会**内嵌在正文之后**并附带可检索 caption（alt 文本 + 引用块）。

    `link_details` 为可选的 `{原始 URL: {title, resolved_url, content_path, fetch_status,
    error_message}}`（Phase 9 外链层），缺省时 `## external_links` 也保持 Phase 7 行为。
    """

    context = _SectionContext(
        media_files=media_files, link_details=link_details, media_captions=media_captions,
        translation=translation,
        ai_analysis=ai_analysis,
    )
    parts: list[str] = []
    zh_title = str((translation or {}).get("title") or "").strip()
    if options.frontmatter:
        frontmatter = dict(build_frontmatter(upstream, enrichment))
        if zh_title:
            frontmatter["title"] = zh_title
        if tags:
            frontmatter["tags"] = list(tags)[:3]        # 队列 #28：预设标签，1–3 个
            # 用户要求：**投资理财**类书签额外带「推文时间」属性（便于按时间复盘行情）
            if "投资理财" in list(tags) or "美股QDII" in list(tags) or "宏观经济" in list(tags):
                posted = _iso_created_at(upstream)
                if posted:
                    frontmatter["posted_at"] = posted
        _tags_ai = getattr(ai_analysis, "tags_ai", None) if ai_analysis is not None else None
        if _tags_ai:
            frontmatter["tags_ai"] = list(_tags_ai)[:3]  # Phase 11：扩展标签单独字段（不动预设 tags）
        lines = ["---"]
        for key in FRONTMATTER_KEYS:
            if key in frontmatter:
                lines.append(f"{key}: {_dump_scalar(frontmatter[key])}")
        lines.append("---")
        parts.append("\n".join(lines))

    # 队列 #27 ②：正文前加可读标题（真实标题优先，纯链接类用派生标签；有译文标题则用译文）
    first_link_title = ""
    for _url, _detail in (link_details or {}).items():
        _title = str((_detail or {}).get("title") or "").strip()
        if _title:
            first_link_title = _title
            break
    doc_title = zh_title or derive_title(upstream, enrichment, first_link_title)
    if doc_title:
        parts.append(f"# {doc_title}")

    for name in section_names_for(options):
        renderer = _SECTION_RENDERERS.get(name)
        if renderer is None:
            logger.warning("unknown markdown section requested: %s", name)
            continue
        try:
            body = renderer(upstream, enrichment, context)
        except Exception as exc:  # noqa: BLE001 - 单段失败不能丢弃整份
            logger.warning("section %r failed: %s", name, exc)
            body = f"_（段落 {name} 渲染失败）_"
        parts.append(f"## {name}\n\n{body}")

    return "\n\n".join(parts).rstrip() + "\n"


def _dump_scalar(value: Any) -> str:
    """把 frontmatter 值转成可被 YAML 解析的标量行。"""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    text = str(value)
    if "\n" in text or text.startswith(("#", "!", "&", "*", "{", "[", ">", "|", "'", '"')):
        return json.dumps(text, ensure_ascii=False)
    return text