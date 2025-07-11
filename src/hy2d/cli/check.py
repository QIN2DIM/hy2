"""Start 命令"""

import typer

from hy2d.core.manager import Hysteria2Manager

app = typer.Typer(help="检查并输出配置。")


@app.callback(invoke_without_command=True)
def check():
    """
    启动服务。
    """
    manager = Hysteria2Manager()
    manager.check()
