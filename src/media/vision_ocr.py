"""本地 OCR：调用 macOS Vision 框架（经 `scripts/vision_ocr.swift` 编译的二进制）。

设计目标（队列 #24 A 阶段）：

* **零安装**：macOS 自带 `swiftc` + Vision 框架，不引入 tesseract / 云 API；
* **零 API 花费、数据不出本机**：纯本地进程调用，不联网；
* **可降级**：非 macOS、无 swiftc、编译失败 ⇒ 返回"不可用"，调用方如实记为"未识别"，
  **绝不伪造**识别结果；
* **可测试**：二进制路径可用环境变量 ``XBK_OCR_BIN`` 覆盖（测试注入桩）。

首次调用会把 ``scripts/vision_ocr.swift`` 编译到 ``data/state/bin/vision_ocr``（gitignored），
之后复用；单张图片 ~0.2–1.4s（实测 2026-10-17，12 张共 ~5s）。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

__all__ = ["OcrResult", "OcrUnavailableError", "OcrError", "OcrEngine", "default_binary_path"]

#: 源码位置（相对项目根）：`scripts/vision_ocr.swift`
_SWIFT_RELATIVE = Path("scripts") / "vision_ocr.swift"
#: 编译产物位置（相对项目根，gitignored）：`data/state/bin/vision_ocr`
_BINARY_RELATIVE = Path("data") / "state" / "bin" / "vision_ocr"
#: 单张图片 OCR 超时（秒）——实测最慢 ~1.4s，给足余量但不无限等待。
DEFAULT_TIMEOUT = 60.0


class OcrError(RuntimeError):
    """OCR 调用本身失败（二进制报错/超时）。"""


class OcrUnavailableError(OcrError):
    """本机不具备本地 OCR 能力（非 macOS / 无 swiftc / 编译失败）。"""


@dataclass(frozen=True)
class OcrResult:
    """单张图片的 OCR 结果。"""

    path: Path
    lines: tuple[str, ...]
    languages: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        """按行拼接的文本（保留换行，便于阅读与检索）。"""

        return "\n".join(self.lines)

    @property
    def has_text(self) -> bool:
        return bool(self.lines)


def default_binary_path(project_root: str | os.PathLike[str] | None = None) -> Path:
    root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[2]
    return root / _BINARY_RELATIVE


class OcrEngine:
    """本地 OCR 引擎（惰性编译 + 复用二进制）。

    ``binary_path`` 为空时依次取：环境变量 ``XBK_OCR_BIN`` → 默认编译产物路径。
    若显式指定了已存在的可执行文件，则**不会**尝试编译（测试注入桩的路径）。
    """

    def __init__(
        self,
        *,
        root: str | os.PathLike[str] | None = None,
        binary_path: str | os.PathLike[str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
        override = binary_path or os.environ.get("XBK_OCR_BIN")
        self._override = Path(override) if override else None
        self._timeout = timeout
        self._compiled: Path | None = None
        self._unavailable_reason: str | None = None

    # ── 能力探测 ────────────────────────────────────────────────────────────

    def binary(self) -> Path:
        """返回可用的 OCR 二进制路径；不可用时抛 :class:`OcrUnavailableError`。"""

        if self._compiled is not None:
            return self._compiled
        if self._override is not None:
            if not self._override.is_file():
                raise OcrUnavailableError(f"XBK_OCR_BIN 指向的文件不存在: {self._override}")
            self._compiled = self._override
            return self._compiled
        if self._unavailable_reason is not None:
            raise OcrUnavailableError(self._unavailable_reason)
        if sys.platform != "darwin":
            self._unavailable_reason = "本地 OCR 仅在 macOS（Vision 框架）可用"
            raise OcrUnavailableError(self._unavailable_reason)
        swiftc = shutil.which("swiftc")
        if swiftc is None:
            self._unavailable_reason = "未找到 swiftc（需 Xcode Command Line Tools）"
            raise OcrUnavailableError(self._unavailable_reason)
        source = self._root / _SWIFT_RELATIVE
        if not source.is_file():
            self._unavailable_reason = f"OCR 源码缺失: {source}"
            raise OcrUnavailableError(self._unavailable_reason)
        self._compiled = self._compile(swiftc, source)
        return self._compiled

    def available(self) -> bool:
        try:
            self.binary()
        except OcrUnavailableError:
            return False
        return True

    def _compile(self, swiftc: str, source: Path) -> Path:
        target = default_binary_path(self._root)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Swift 编译需要可写的模块缓存；默认缓存目录在沙箱/只读环境下会失败。
        cache = target.parent / "swift-module-cache"
        cache.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, CLANG_MODULE_CACHE_PATH=str(cache))
        proc = subprocess.run(
            [swiftc, "-O", "-module-cache-path", str(cache), "-o", str(target), str(source)],
            capture_output=True, text=True, timeout=600, env=env,
        )
        if proc.returncode != 0 or not target.is_file():
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
            self._unavailable_reason = "OCR 二进制编译失败: " + " | ".join(detail)
            raise OcrUnavailableError(self._unavailable_reason)
        return target

    # ── 识别 ────────────────────────────────────────────────────────────────

    def ocr(self, image_path: str | os.PathLike[str]) -> OcrResult:
        """对单张图片做 OCR；返回识别到的文本行（可能为空 = 图中无文字）。"""

        path = Path(image_path)
        if not path.is_file():
            raise OcrError(f"图片不存在: {path}")
        binary = self.binary()
        try:
            proc = subprocess.run(
                [str(binary), str(path)], capture_output=True, text=True, timeout=self._timeout
            )
        except subprocess.TimeoutExpired as exc:  # pragma: no cover - 依赖真实进程
            raise OcrError(f"OCR 超时（>{self._timeout}s）: {path}") from exc
        if proc.returncode != 0:
            raise OcrError(
                f"OCR 失败（exit={proc.returncode}）: {path}: {(proc.stderr or '').strip()[:200]}"
            )
        try:
            payload = json.loads(proc.stdout or "{}")
        except ValueError as exc:
            raise OcrError(f"OCR 输出不是合法 JSON: {path}") from exc
        lines = tuple(str(line) for line in (payload.get("lines") or []) if str(line).strip())
        langs = tuple(str(lang) for lang in (payload.get("langs") or []))
        return OcrResult(path=path, lines=lines, languages=langs)
