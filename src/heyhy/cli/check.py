"""Start 命令"""

import typer

from heyhy.core.manager import AnyTLSManager

app = typer.Typer(help="检查并输出配置。")


@app.callback(invoke_without_command=True)
def check():
    """
    启动服务。
    """
    manager = AnyTLSManager()
    manager.check()
