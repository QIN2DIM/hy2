"""Start 命令"""

import typer

from hy2d.core.manager import AnyTLSManager

app = typer.Typer(help="启动服务。")


@app.callback(invoke_without_command=True)
def start():
    """
    启动服务。
    """
    manager = AnyTLSManager()
    manager.start()
