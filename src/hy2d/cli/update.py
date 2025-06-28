"""Update 命令"""

import logging
from typing import Annotated, Optional

import typer

from hy2d.core.manager import Hysteria2Manager

app = typer.Typer(help="更新 Hysteria2 服务。默认仅拉取最新镜像并重启。也可用于更新部分服务配置。")


@app.callback(invoke_without_command=True)
def update(
    password: Annotated[
        Optional[str], typer.Option("-p", "--password", help="更新连接密码")
    ] = None,
    port: Annotated[Optional[int], typer.Option("--port", help="更新监听端口")] = None,
    image: Annotated[Optional[str], typer.Option("--image", help="更新服务镜像")] = None,
):
    """
    更新 Hysteria2 服务。

    默认情况下，此命令仅会拉取最新的 Docker 镜像并重启服务。

    您也可以通过指定可选参数来更新服务配置：
    - `--password`: 更新客户端连接密码。
    - `--port`: 更新服务监听端口。
    - `--image`: 更新使用的 Docker 镜像。

    注意：不支持通过此命令修改域名。如需修改域名，请重新运行 `install` 命令。
    """
    import sys

    # 检查是否尝试修改域名
    if any(arg in sys.argv for arg in ["-d", "--domain", "--ip"]):
        logging.error("错误：`update` 命令不支持通过 `-d` 或 `--domain` 修改域名。")
        logging.error("如果您需要更改域名，请备份现有重要配置后，重新运行 `install` 命令。")
        raise typer.Exit(code=1)

    manager = Hysteria2Manager()
    manager.update(password=password, port=port, image=image)
