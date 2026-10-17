"""轻量再导出：让 Markdown 写入层用 `should_translate` 而不引入媒体包的重依赖。"""

from src.media.translate import should_translate

__all__ = ["should_translate"]
