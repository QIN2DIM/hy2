"""Remove 命令"""

import typer

from hy2d.core.manager import Hysteria2Manager

app = typer.Typer(help="停止并移除 Hysteria2 服务。")


@app.callback(invoke_without_command=True)
def remove():
    """
    停止并移除 Hysteria2 服务。
    """
    manager = Hysteria2Manager()
    manager.remove()
