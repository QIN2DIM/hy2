"""Start 命令"""

import typer

from hy2d.core.manager import Hysteria2Manager

app = typer.Typer(help="启动服务。")


@app.callback(invoke_without_command=True)
def start():
    """
    启动服务。
    """
    manager = Hysteria2Manager()
    manager.start()
