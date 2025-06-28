"""Remove 命令"""

import typer

from hy2d.core.manager import AnyTLSManager

app = typer.Typer(help="停止并移除 AnyTLS 服务。")


@app.callback(invoke_without_command=True)
def remove():
    """
    停止并移除 AnyTLS 服务。
    """
    manager = AnyTLSManager()
    manager.remove()
