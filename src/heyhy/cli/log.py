"""Log 命令"""

import typer

from heyhy.core.manager import AnyTLSManager

app = typer.Typer(help="查看实时日志。")


@app.callback(invoke_without_command=True)
def log():
    """
    查看实时日志。
    """
    manager = AnyTLSManager()
    manager.log()
