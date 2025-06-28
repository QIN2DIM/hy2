"""Stop 命令"""

import typer

from hy2d.core.manager import Hysteria2Manager

app = typer.Typer(help="停止服务。")


@app.callback(invoke_without_command=True)
def stop():
    """
    停止服务。
    """
    manager = Hysteria2Manager()
    manager.stop()
