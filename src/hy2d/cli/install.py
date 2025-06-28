"""Install 命令"""

from typing import Annotated, Optional

import typer

from hy2d.core import constants
from hy2d.core.manager import AnyTLSManager

app = typer.Typer(help="安装并启动 AnyTLS 服务。")


@app.callback(invoke_without_command=True)
def install(
    domain: Annotated[
        str, typer.Option("-d", "--domain", help="绑定的域名", prompt="请输入您的域名")
    ],
    password: Annotated[
        Optional[str],
        typer.Option("-p", "--password", help="手动指定连接密码 (可选，默认随机生成)"),
    ] = None,
    ip: Annotated[
        Optional[str], typer.Option("--ip", help="手动指定服务器公网 IP (可选，默认自动检测)")
    ] = None,
    port: Annotated[
        Optional[int], typer.Option("--port", help="指定监听端口 (可选，默认 8443)")
    ] = constants.LISTEN_PORT,
    image: Annotated[
        Optional[str], typer.Option("--image", help="指定用于托管 AnyTLS server 的服务镜像")
    ] = constants.SERVICE_IMAGE,
):
    """
    安装并启动 AnyTLS 服务。
    """
    manager = AnyTLSManager()
    manager.install(domain=domain, password=password, ip=ip, port=port, image=image)
