"""Stop 命令"""

import typer

from heyhy.core.manager import AnyTLSManager

app = typer.Typer(help="停止服务。")


@app.callback(invoke_without_command=True)
def stop():
    """
    停止服务。
    """
    manager = AnyTLSManager()
    manager.stop()
