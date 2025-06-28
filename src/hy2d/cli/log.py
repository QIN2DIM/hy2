"""Log 命令"""

import typer

from hy2d.core.manager import Hysteria2Manager

app = typer.Typer(help="查看实时日志。")


@app.callback(invoke_without_command=True)
def log():
    """
    查看实时日志。
    """
    manager = Hysteria2Manager()
    manager.log()
