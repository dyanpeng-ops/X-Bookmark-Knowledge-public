"""封面图下载（队列 #30 / F-BYNLUY-01）：把外链的 `og:image` 落到知识库本地。

设计：
* 复用现有**媒体通道**的目录约定：`assets/<tweet_id>/links/<hash>.cover.<ext>`；
* **失败降级**：任何异常（网络/超时/过大/非图片）一律返回 None，**不抛、不阻断、不伪造**；
* 纯 stdlib；带 timeout 与大小上限；原子写（`.part` → `os.replace`）。
"""

from __future__ import annotations

import hashlib
import os
import urllib.parse
import urllib.request
from pathlib import Path

__all__ = ["download_cover", "cover_filename", "DEFAULT_MAX_BYTES", "DEFAULT_TIMEOUT"]

#: 封面大小上限（5 MB）与超时（20s）——封面是缩略图，没必要更大。
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_TIMEOUT = 20.0

_EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def cover_filename(image_url: str, extension: str) -> str:
    """稳定命名：`<url 的 sha256 前 16 位>.cover.<ext>`（同一 URL 永远同名）。"""

    digest = hashlib.sha256(str(image_url).encode("utf-8")).hexdigest()[:16]
    return f"{digest}.cover{extension}"


def download_cover(
    image_url: str,
    target_dir: str | os.PathLike[str],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Path | None:
    """下载封面到 ``target_dir``，返回本地路径；失败/非图片/超限一律返回 None。"""

    url = str(image_url or "").strip()
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        return None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (bookmark-cover)"})
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            content_type = str(resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            extension = _EXT_BY_TYPE.get(content_type)
            if extension is None:
                # Content-Type 不给力时按 URL 后缀兜底；仍不是图片则放弃
                suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
                extension = suffix if suffix in (".jpg", ".jpeg", ".png", ".webp", ".gif") else None
            if extension is None:
                return None
            if extension == ".jpeg":
                extension = ".jpg"
            payload = resp.read(max_bytes + 1)
    except Exception:  # noqa: BLE001 - 下载失败只降级，绝不阻断
        return None
    if not payload or len(payload) > max_bytes:
        return None
    directory = Path(target_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / cover_filename(url, extension)
        tmp = target.with_name(target.name + ".part")
        tmp.write_bytes(payload)
        os.replace(tmp, target)
    except OSError:
        return None
    return target
