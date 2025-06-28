"""日志配置模块"""

import logging

from rich.logging import RichHandler


def setup_logging():
    """配置全局日志记录器"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False, show_time=False)],
    )
