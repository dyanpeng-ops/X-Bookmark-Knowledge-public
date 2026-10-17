"""本地视觉描述后端（队列 #24 B 阶段）：调用 **Bionic / Saluki** 的 OpenAI 兼容 API。

设计目标
--------
* **零 API 花费、数据不出本机**：请求发往 ``http://127.0.0.1:<port>/v1/chat/completions``，
  图片以 base64 data-URI 内联，**不经过任何外部服务**；
* **只在 OCR 无文字的图片上使用**（A 阶段优先级不变）—— 由 :mod:`src.media.descriptions` 调度；
* **串行**：16GB 显存紧张，本模块一次只处理一张（调用方也串行），且与 OCR 错峰；
* **可降级**：服务不可用 / 超时 / 返回异常 ⇒ 抛 :class:`VisionUnavailableError` /
  :class:`VisionError`，由上层**如实标记、绝不伪造**；
* **可测试**：引擎可替换（``engine`` 注入），并支持 ``XBK_VISION_*`` 环境变量覆盖。

实测（2026-10-17，本机）：`underdog-saluki-27b-1.0`（Saluki-27B Q8_0 + mmproj，ctx 16384），
单张 ~48s，中文描述质量良好。
"""

from __future__ import annotations

import base64
import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "VisionDescription",
    "VisionEngine",
    "VisionError",
    "VisionUnavailableError",
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "DEFAULT_PROMPT",
]

#: 默认端点与模型（可用 ``XBK_VISION_BASE_URL`` / ``XBK_VISION_MODEL`` 覆盖）
DEFAULT_BASE_URL = "http://127.0.0.1:1235"
DEFAULT_MODEL = "underdog-saluki-27b-1.0"

#: 中文描述提示词：要求"主体/场景 + 显眼文字/细节"，短而具体（便于写进 caption 检索）。
DEFAULT_PROMPT = (
    "用中文简洁描述这张图片的内容（1-3 句）：先说主体与场景，再说画面里显眼的文字或细节。"
    "不要寒暄、不要复述本提示。"
)

#: 单张图片的超时（秒）——实测 27B Q8 单张 ~48s，给足余量。
DEFAULT_TIMEOUT = 900.0

_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".webp": "image/webp", ".gif": "image/gif"}


class VisionError(RuntimeError):
    """视觉调用失败（服务返回异常/超时等）。"""


class VisionUnavailableError(VisionError):
    """本机视觉服务不可用（未启动 / 端点不通 / 模型缺失）。"""


@dataclass(frozen=True)
class VisionDescription:
    text: str
    model: str
    elapsed_ms: int = 0


class VisionEngine:
    """OpenAI 兼容的本地视觉客户端（stdlib HTTP，无第三方依赖）。

    ``base_url`` / ``model`` 缺省取 ``XBK_VISION_BASE_URL`` / ``XBK_VISION_MODEL``，再退化为默认值。
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        prompt: str = DEFAULT_PROMPT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = (base_url or os.environ.get("XBK_VISION_BASE_URL")
                         or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("XBK_VISION_MODEL") or DEFAULT_MODEL
        self.prompt = prompt
        self.timeout = timeout
        self._probed: bool | None = None

    # ── 能力探测 ────────────────────────────────────────────────────────────

    def available(self) -> bool:
        """轻量探测：``GET /v1/models`` 是否可达（不加载/不推理，秒级）。"""

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

    # ── 调用 ────────────────────────────────────────────────────────────────

    def describe(self, image_path: str | os.PathLike[str]) -> VisionDescription:
        """对单张图片生成中文描述。线程/调用方需自行串行（本方法不做并发控制）。"""

        path = Path(image_path)
        if not path.is_file():
            raise VisionError(f"图片不存在: {path}")
        mime = _MIME.get(path.suffix.lower())
        if mime is None:
            raise VisionError(f"不支持的图片后缀: {path.suffix}")
        if not self.available():
            raise VisionUnavailableError(
                f"本地视觉服务不可用（{self.base_url}，模型 {self.model}）"
            )
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        body = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": self.prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
                ],
            }],
            "max_tokens": 320,
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8", "replace"))
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            raise VisionUnavailableError(f"视觉调用失败（网络/超时）: {exc}") from exc
        except (OSError, ValueError) as exc:
            raise VisionError(f"视觉调用失败: {exc}") from exc
        try:
            message = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise VisionError(f"视觉响应结构异常: {str(payload)[:200]}") from exc
        text = " ".join(str(message).split())
        if not text:
            raise VisionError("视觉返回了空描述")
        usage = payload.get("usage") or {}
        elapsed = usage.get("total_time_ms") or 0
        return VisionDescription(
            text=text, model=str(payload.get("model") or self.model),
            elapsed_ms=int(elapsed) if isinstance(elapsed, (int, float)) else 0,
        )
