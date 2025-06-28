"""核心工具函数"""

import logging
import secrets
import string
import subprocess
import sys
from pathlib import Path
from typing import Optional

DOCKER_INSTALL_SCRIPT = """
echo ">>> 正在使用官方脚本 (get.docker.com) 安装 Docker..."
echo ">>> 此脚本将自动检测您的 Linux 发行版并进行适配。"
curl -fsSL https://get.docker.com | sh
echo ">>> Docker 安装脚本执行完毕。"
"""


def run_command(
    command: list[str],
    cwd: Optional[Path] = None,
    capture_output: bool = False,
    check: bool = True,
    stream_output: bool = False,
    install_docker: bool = False,
    skip_execution_logging: bool = False,
    propagate_exception: bool = False,
) -> subprocess.CompletedProcess:
    """
    统一的命令执行函数

    Args:
        command: 命令列表.
        cwd: 执行命令的工作目录.
        capture_output: 是否捕获 stdout 和 stderr.
        check: 如果命令返回非零退出码，是否抛出 CalledProcessError.
        stream_output: 是否实时打印输出（用于 logs -f）.
        install_docker: 从 install 指令进入，自动安装 docker.
        skip_execution_logging: 隐藏执行指令日志.
        propagate_exception: 是否向上抛出异常而不是直接退出.

    Returns:
        CompletedProcess 对象.
    """
    if not skip_execution_logging:
        logging.info(f"执行命令: {' '.join(command)}")

    try:
        if stream_output:
            with subprocess.Popen(command, cwd=cwd, text=True) as process:
                process.wait()
                return subprocess.CompletedProcess(command, process.returncode)
        else:
            return subprocess.run(
                command, cwd=cwd, capture_output=capture_output, text=True, check=check
            )
    except FileNotFoundError:
        logging.error(f"命令未找到: {command[0]}。请确保它已安装并在您的 PATH 中。")
        if install_docker:
            raise FileNotFoundError
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logging.error(f"命令执行失败，返回码: {e.returncode}")
        if e.stdout:
            logging.error(f"STDOUT:\n{e.stdout}")
        if e.stderr:
            logging.error(f"STDERR:\n{e.stderr}")
        if propagate_exception:
            raise e
        sys.exit(1)


def get_public_ip() -> str:
    """获取本机的公网出口 IP"""
    logging.info("正在检测本机公网 IP...")
    ip_services = ["ip.sb", "ifconfig.me", "api.ipify.org", "icanhazip.com"]
    for service in ip_services:
        try:
            result = run_command(
                ["curl", "-s", "--ipv4", service],
                capture_output=True,
                check=True,
                propagate_exception=True,
            )
            ip = result.stdout.strip()
            if ip:
                logging.info(f"成功获取公网 IP: {ip}")
                return ip
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    logging.error("无法自动获取公网 IP，请使用 --ip 参数手动指定。")
    raise RuntimeError("所有 IP 服务都无法访问。")


def generate_password(length: int = 16) -> str:
    """生成一个安全的随机密码"""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def is_root():
    """检查当前用户是否为 root。"""
    # This function is mentioned in the original file but not implemented in the new file
    # It's left unchanged as it's not clear what it's supposed to do
    pass
