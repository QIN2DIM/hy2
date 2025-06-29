"""Hysteria2 服务核心管理逻辑"""

import logging
import os
import shutil
import subprocess
import sys
import uuid
from typing import Optional

import yaml
from rich.console import Console
from rich.syntax import Syntax

from hy2d.core import constants, utils
from hy2d.core.constants import MASQUERADE_WEBSITE


class Hysteria2Manager:
    """封装 Hysteria2 服务管理的所有逻辑"""

    def __init__(self):
        """初始化管理器"""
        self.console = Console()
        self.compose_cmd: Optional[list[str]] = None

    def _get_compose_cmd(self) -> list[str]:
        """检测并返回可用的 docker compose 命令，并缓存结果。"""
        if self.compose_cmd:
            return self.compose_cmd

        try:
            # 优先使用 "docker compose" (V2)
            utils.run_command(
                ["docker", "compose", "version"],
                capture_output=True,
                install_docker=True,
                skip_execution_logging=True,
                propagate_exception=True,
            )
            self.compose_cmd = ["docker", "compose"]
            logging.debug("检测到 Docker Compose V2 (docker compose)，将使用此命令。")
            return self.compose_cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 回退到 "docker-compose" (V1)
            logging.debug("未检测到 'docker compose' (V2)，尝试 'docker-compose' (V1)...")
            try:
                utils.run_command(
                    ["docker-compose", "--version"],
                    capture_output=True,
                    install_docker=True,
                    skip_execution_logging=True,
                    propagate_exception=True,
                )
                self.compose_cmd = ["docker-compose"]
                logging.debug("检测到 Docker Compose V1 (docker-compose)，将使用此命令。")
                return self.compose_cmd
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 两个都找不到，这个异常将在 _check_dependencies 中被捕获并处理
                raise FileNotFoundError("未找到 'docker compose' 或 'docker-compose'。")

    @staticmethod
    def _ensure_service_installed():
        """确保服务已安装，否则退出"""
        if not constants.DOCKER_COMPOSE_PATH.is_file():
            logging.error(f"配置文件 ({constants.DOCKER_COMPOSE_PATH}) 未找到。")
            logging.error("请先运行 'install' 命令来安装服务。")
            sys.exit(1)

    @staticmethod
    def _get_domain_from_config() -> str:
        """从 docker-compose.yaml 文件中解析出域名"""
        if not constants.DOCKER_COMPOSE_PATH.exists():
            logging.error(
                f"配置文件 {constants.DOCKER_COMPOSE_PATH} 不存在。您是否已经安装了服务？"
            )
            sys.exit(1)

        with constants.DOCKER_COMPOSE_PATH.open("r") as f:
            data = yaml.safe_load(f)
            container_name = data["services"]["hysteria2-inbound"]["container_name"]
            domain = container_name.split("hysteria2-inbound-")[-1]
            if not domain:
                raise ValueError
            return domain

    @staticmethod
    def _as_share_link(client_config: dict) -> str:
        tpl = "hy2://{pwd}@{server}:{port}?sni={sni}#{alias}"
        return tpl.format(
            pwd=client_config.get("password", ""),
            server=client_config.get("server", ""),
            port=client_config.get("port", ""),
            sni=client_config.get("sni", ""),
            alias=client_config.get("sni", ""),
        )

    def _preview_fmt_client_config(
        self, *, domain: str, public_ip: str, port: int | str, password: str
    ):
        client_config_dict = {
            "name": domain,
            "type": "hysteria2",
            "server": public_ip,
            "port": port,
            "password": password,
            "sni": domain,
            "skip_cert_verify": False,
        }

        client_yaml = yaml.dump([client_config_dict], sort_keys=False)
        share_link = self._as_share_link(client_config_dict)

        self.console.print("\n" + "=" * 20 + " 客户端配置信息[mihomo] " + "=" * 20)
        self.console.print(Syntax(client_yaml, "yaml"))

        self.console.print("\n" + "=" * 20 + " Hysteria2 分享链接 " + "=" * 20)
        self.console.print(Syntax("\n" + share_link + "\n", "markdown"))

        self.console.print("=" * 58 + "\n")

        self.console.print(f"详见客户端配置文档：{constants.MIHOMO_PROXIES_DOCS}\n")

    def _check_dependencies(self, auto_install: bool = False) -> bool:
        """
        检查 Docker 和 Docker Compose 是否安装。
        :param auto_install: 如果为 True，当 Docker 未安装时，会提示并尝试自动安装。
        :return: 如果 Docker 之前未安装，并且本次成功安装了，则返回 True。否则返回 False。
        """
        logging.info("正在检查 Docker 和 Docker Compose 环境...")
        try:
            utils.run_command(["docker", "--version"], capture_output=True, install_docker=True)
            self._get_compose_cmd()  # 检测并缓存 docker compose 命令
            logging.info("Docker 和 Docker Compose 已安装。")
            return False  # 已安装，未执行安装
        except (FileNotFoundError, subprocess.CalledProcessError):
            logging.warning("未检测到 Docker 或 Docker Compose。")
            if auto_install:
                logging.info("开始自动安装 Docker 和 Docker Compose...")
                utils.run_command(["/bin/bash", "-c", utils.DOCKER_INSTALL_SCRIPT])
                logging.info(
                    "安装完成。您可能需要重新登录或运行 `newgrp docker` "
                    "以便非 root 用户无需 sudo 即可运行 docker。"
                )
                return True  # 执行了安装
            else:
                # 如果不是在主安装流程中，仅检查而不安装
                logging.error("请先运行 'install' 命令来安装所有依赖。")
                sys.exit(1)
        except Exception as e:
            logging.error(e)
            # 在这种未知错误下，我们应该退出而不是继续
            sys.exit(1)

    def _check_certbot(self, auto_install: bool = False) -> bool:
        """
        检查 Certbot 是否安装，并根据需要自动安装。
        采用 Certbot 官方推荐的 Snap 方式安装，以确保版本最新并能自动续期。
        :param auto_install: 如果为 True，当 certbot 未安装时，会尝试自动安装。
        :return: 如果 Certbot 之前未安装，并且本次成功安装了，则返回 True。否则返回 False。
        """
        logging.info("正在检查 Certbot 是否安装...")
        if shutil.which("certbot"):
            logging.info("Certbot 已安装。")
            return False  # Certbot 已存在，未进行安装

        logging.warning("未检测到 Certbot。Certbot 是申请 HTTPS 证书所必需的。")

        if not auto_install:
            # 如果不是在主安装流程中，仅检查而不安装
            logging.error("请先运行 'install' 命令来安装所有依赖。")
            sys.exit(1)

        logging.info("将自动为您安装 Certbot (通过 Snap)。")
        logging.info("此过程需要 sudo 权限，且可能需要几分钟。")

        try:
            # 检查 snapd 是否安装，如果没有，则尝试通过 apt 安装
            if not shutil.which("snap"):
                logging.warning("未检测到 'snap' 命令, 正在尝试使用 apt 安装 'snapd'...")
                try:
                    utils.run_command(["sudo", "apt-get", "update", "-y"], propagate_exception=True)
                    utils.run_command(
                        ["sudo", "apt-get", "install", "-y", "snapd"], propagate_exception=True
                    )
                    logging.info("snapd 安装成功。")
                except Exception as apt_e:
                    logging.error(f"使用 apt 安装 snapd 失败: {apt_e}")
                    logging.error("您的系统可能不是基于 Debian/Ubuntu，或没有 apt 工具。")
                    logging.error(
                        "请参考 https://snapcraft.io/docs/installing-snapd 手动安装 snapd 后重试。"
                    )
                    sys.exit(1)

            # 使用 Snap 安装 Certbot
            utils.run_command(["sudo", "snap", "install", "core"])
            utils.run_command(["sudo", "snap", "refresh", "core"])
            utils.run_command(["sudo", "snap", "install", "--classic", "certbot"])
            utils.run_command(
                ["sudo", "ln", "-s", "/snap/bin/certbot", "/usr/bin/certbot"], check=False
            )
            logging.info("Certbot 安装成功！它将自动处理证书续期。")
            return True  # 进行了安装
        except Exception as e:
            logging.error(f"使用 Snap 安装 Certbot 失败: {e}")
            logging.error("请参考 https://certbot.eff.org/instructions 手动安装后重试。")
            sys.exit(1)

    def _check_bbr(self):
        """
        检查并尝试开启 BBR 拥塞控制算法。
        这是一个尽力而为的操作，任何失败都不会中断主安装流程。
        """
        logging.info("正在检查并尝试开启 BBR...")
        try:
            # 1. 检查 BBR 是否已经开启
            qdisc_res = utils.run_command(
                ["sysctl", "net.core.default_qdisc"],
                capture_output=True,
                check=False,
                skip_execution_logging=True,
            )
            tcp_cong_res = utils.run_command(
                ["sysctl", "net.ipv4.tcp_congestion_control"],
                capture_output=True,
                check=False,
                skip_execution_logging=True,
            )

            qdisc_ok = qdisc_res.returncode == 0 and "fq" in qdisc_res.stdout
            tcp_cong_ok = tcp_cong_res.returncode == 0 and "bbr" in tcp_cong_res.stdout

            if qdisc_ok and tcp_cong_ok:
                logging.info("BBR 已成功开启。")
                return

            logging.info("检测到 BBR 未开启或未完全开启，将尝试自动配置。")
            self.console.print("此操作需要 [bold yellow]sudo[/bold yellow] 权限来修改系统配置。")

            # 2. 写入配置
            bbr_config = {"net.core.default_qdisc": "fq", "net.ipv4.tcp_congestion_control": "bbr"}
            for key, value in bbr_config.items():
                cmd = f"grep -qxF '{key}={value}' /etc/sysctl.conf || echo '{key}={value}' | sudo tee -a /etc/sysctl.conf > /dev/null"
                utils.run_command(
                    ["bash", "-c", cmd], propagate_exception=True, skip_execution_logging=True
                )
            logging.info("BBR 配置已写入 /etc/sysctl.conf。")

            # 3. 应用配置
            logging.info("正在应用新的 sysctl 配置...")
            utils.run_command(["sudo", "sysctl", "-p"], propagate_exception=True)

            # 4. 再次检查
            logging.info("正在验证 BBR 是否成功开启...")
            qdisc_res_after = utils.run_command(
                ["sysctl", "net.core.default_qdisc"], capture_output=True, propagate_exception=True
            )
            tcp_cong_res_after = utils.run_command(
                ["sysctl", "net.ipv4.tcp_congestion_control"],
                capture_output=True,
                propagate_exception=True,
            )

            if "fq" in qdisc_res_after.stdout and "bbr" in tcp_cong_res_after.stdout:
                logging.info("BBR 成功开启！")
            else:
                logging.warning("BBR 配置已应用，但验证未完全成功。可能需要重启系统才能生效。")
                logging.warning(
                    f"当前 qdisc: {qdisc_res_after.stdout.strip()}, tcp_congestion_control: {tcp_cong_res_after.stdout.strip()}"
                )

        except Exception as e:
            logging.warning(f"自动开启 BBR 失败: {e}")
            logging.warning("这通常不会影响 Hysteria2 的核心功能，但可能会影响网络性能。")
            logging.warning("您可以参考相关文档手动开启 BBR。")

    def install(
        self, domain: str, password: Optional[str], ip: Optional[str], port: int, image: str
    ):
        """安装并启动 Hysteria2 服务"""
        # --- 步骤 1/4: 初始检查和依赖安装 ---
        logging.info("--- 步骤 1/4: 开始环境检查与依赖安装 ---")

        # 检查并安装 Docker & Certbot
        # 如果安装了任何一个，脚本需要重启以加载新环境
        docker_installed_now = self._check_dependencies(auto_install=True)
        certbot_installed_now = self._check_certbot(auto_install=True)

        # 检查并开启 BBR (尽力而为)
        self._check_bbr()

        if docker_installed_now or certbot_installed_now:
            logging.warning("依赖项已成功安装。为了使环境更改完全生效，脚本将自动重新执行。")
            logging.warning("如果脚本没有自动重启，请手动重新运行您刚才执行的命令。")
            try:
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception as e:
                logging.error(f"脚本自动重启失败: {e}")
                logging.error("请手动重新运行您刚才执行的命令以继续安装。")
                sys.exit(1)

            # execv会替换当前进程，所以下面的代码在新进程中才会执行
            return  # 在当前进程中，到此为止

        logging.info("--- 所有依赖均已满足 ---")

        logging.info(f"--- 步骤 2/4: 开始安装 Hysteria2 服务 (域名: {domain}) ---")
        if constants.BASE_DIR.exists():
            logging.warning(f"工作目录 {constants.BASE_DIR} 已存在。继续操作将可能覆盖现有配置。")
            if self.console.input("是否继续？ (y/n): ").lower() != "y":
                logging.info("安装已取消。")
                return

        public_ip = ip or utils.get_public_ip()
        service_password = password or utils.generate_password()

        logging.info("--- 步骤 3/4: 申请证书与生成配置 ---")
        logging.info(f"正在为域名 {domain} 申请 Let's Encrypt 证书...")
        try:
            utils.run_command(
                [
                    "certbot",
                    "certonly",
                    "--standalone",
                    "--register-unsafely-without-email",
                    "--agree-tos",
                    "--non-interactive",
                    "-d",
                    domain,
                ],
                propagate_exception=True,
            )
            logging.info("证书申请成功。")
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            logging.error(f"证书申请失败: {e}")
            logging.error("请检查：")
            logging.error(f"  1. 域名 '{domain}' 是否正确解析到本机 IP 地址 ({public_ip})。")
            logging.error("  2. 服务器防火墙是否已放开 80 端口。")
            sys.exit(1)

        logging.info(f"正在创建工作目录: {constants.BASE_DIR}")
        constants.BASE_DIR.mkdir(exist_ok=True)

        # 创建 Mihomo 配置
        mihomo_cfg_dict = {
            "listeners": [
                {
                    "name": f"hysteria2-in-{uuid.uuid4()}",
                    "type": "hysteria2",
                    "port": port,
                    "listen": "0.0.0.0",
                    "users": {f"user_{uuid.uuid4().hex[:8]}": service_password},
                    "masquerade": MASQUERADE_WEBSITE,
                    "certificate": f"/etc/letsencrypt/live/{domain}/fullchain.pem",
                    "private-key": f"/etc/letsencrypt/live/{domain}/privkey.pem",
                }
            ]
        }

        with constants.CONFIG_PATH.open("w", encoding="utf8") as f:
            yaml.dump(mihomo_cfg_dict, f, sort_keys=False)
        logging.info(f"已生成配置文件: {constants.CONFIG_PATH}")

        # 创建 Docker Compose 配置
        docker_compose_cfg_dict = {
            "services": {
                "hysteria2-inbound": {
                    "image": image,
                    "container_name": f"hysteria2-inbound-{domain}",
                    "restart": "always",
                    "network_mode": "host",
                    "ports": [f"{port}:{port}"],
                    "working_dir": "/app/proxy-inbound/",
                    "volumes": [
                        "/etc/letsencrypt/:/etc/letsencrypt/",
                        "./config.yaml:/app/proxy-inbound/config.yaml",
                    ],
                    "command": ["-f", "config.yaml", "-d", "/"],
                }
            }
        }
        with constants.DOCKER_COMPOSE_PATH.open("w", encoding="utf8") as f:
            yaml.dump(docker_compose_cfg_dict, f, sort_keys=False)
        logging.info(f"已生成 Docker Compose 文件: {constants.DOCKER_COMPOSE_PATH}")

        compose_cmd = self._get_compose_cmd()
        logging.info("--- 步骤 4/4: 启动服务 ---")
        logging.info("正在拉取最新的 Docker 镜像...")
        utils.run_command(compose_cmd + ["pull"], cwd=constants.BASE_DIR)
        logging.info("正在启动服务...")
        utils.run_command(compose_cmd + ["down"], cwd=constants.BASE_DIR, check=False)
        utils.run_command(compose_cmd + ["up", "-d"], cwd=constants.BASE_DIR)

        logging.info("--- Hysteria2 服务安装并启动成功！ ---")

        # 打印客户端配置
        self._preview_fmt_client_config(
            domain=domain, public_ip=public_ip, port=port, password=service_password
        )

    def remove(self):
        """停止并移除 Hysteria2 服务和相关文件"""
        logging.info("--- 开始卸载 Hysteria2 服务 ---")
        if not constants.BASE_DIR.exists():
            logging.warning(f"工作目录 {constants.BASE_DIR} 不存在，可能服务未安装或已被移除。")
            return

        domain = self._get_domain_from_config()
        logging.info(f"检测到正在管理的域名为: {domain}")

        compose_cmd = self._get_compose_cmd()
        logging.info("正在停止并移除 Docker 容器...")
        utils.run_command(compose_cmd + ["down", "--volumes"], cwd=constants.BASE_DIR, check=False)

        logging.info(f"正在删除工作目录: {constants.BASE_DIR}")
        shutil.rmtree(constants.BASE_DIR)

        logging.info(f"正在删除 {domain} 的 Let's Encrypt 证书...")
        utils.run_command(
            ["certbot", "delete", "--cert-name", domain, "--non-interactive"], check=False
        )
        logging.info("--- Hysteria2 服务已成功卸载。 ---")

    def start(self):
        """启动服务"""
        self._ensure_service_installed()
        logging.info("正在启动 Hysteria2 服务...")
        compose_cmd = self._get_compose_cmd()
        utils.run_command(compose_cmd + ["up", "-d"], cwd=constants.BASE_DIR)
        logging.info("Hysteria2 服务已启动。")

    def stop(self):
        """停止服务"""
        self._ensure_service_installed()
        logging.info("正在停止 Hysteria2 服务...")
        compose_cmd = self._get_compose_cmd()
        utils.run_command(compose_cmd + ["down"], cwd=constants.BASE_DIR)
        logging.info("Hysteria2 服务已停止。")

    def update(self, password: Optional[str], port: Optional[int], image: Optional[str]):
        """
        更新服务。
        如果未提供任何参数，则仅拉取新镜像并重启。
        如果提供了参数，则更新相应的配置，然后拉取镜像并重启。
        """
        self._ensure_service_installed()
        logging.info("--- 开始更新 Hysteria2 服务 ---")
        config_changed = False

        try:
            # --- 步骤 1: 加载现有配置 ---
            logging.debug("正在加载现有配置文件...")
            with constants.DOCKER_COMPOSE_PATH.open("r", encoding="utf8") as f:
                docker_compose_cfg = yaml.safe_load(f)
            with constants.CONFIG_PATH.open("r", encoding="utf8") as f:
                mihomo_cfg = yaml.safe_load(f)

            # --- 步骤 2: 按需更新配置 ---
            if password:
                logging.info("正在更新连接密码...")
                # user key 是随机生成的，所以直接替换整个 users 字典
                mihomo_cfg["listeners"][0]["users"] = {f"user_{uuid.uuid4().hex[:8]}": password}
                config_changed = True
                logging.info("连接密码已在配置中更新。")

            if port:
                logging.info(f"正在更新监听端口为 {port}...")
                mihomo_cfg["listeners"][0]["port"] = port
                docker_compose_cfg["services"]["hysteria2-inbound"]["ports"] = [f"{port}:{port}"]
                config_changed = True
                logging.info(f"监听端口已在配置中更新为 {port}。")

            if image:
                logging.info(f"正在更新服务镜像为 {image}...")
                docker_compose_cfg["services"]["hysteria2-inbound"]["image"] = image
                config_changed = True
                logging.info(f"服务镜像已在配置中更新为 {image}。")

            # --- 步骤 3: 如果配置有变，则写回文件 ---
            if config_changed:
                logging.info("正在保存更新后的配置文件...")
                with constants.CONFIG_PATH.open("w", encoding="utf8") as f:
                    yaml.dump(mihomo_cfg, f, sort_keys=False)
                with constants.DOCKER_COMPOSE_PATH.open("w", encoding="utf8") as f:
                    yaml.dump(docker_compose_cfg, f, sort_keys=False)
                logging.info("配置文件保存成功。")

        except FileNotFoundError:
            logging.error("配置文件未找到。请确认服务已正确安装。")
            sys.exit(1)
        except Exception as e:
            logging.error(f"更新配置时发生错误: {e}")
            sys.exit(1)

        # --- 步骤 4: 拉取镜像并重启服务 ---
        compose_cmd = self._get_compose_cmd()
        if image:
            logging.info(f"正在拉取指定的 Docker 镜像 ({image})...")
        else:
            logging.info("正在拉取最新的 Docker 镜像...")
        utils.run_command(compose_cmd + ["pull"], cwd=constants.BASE_DIR)

        logging.info("正在使用新配置重启服务...")
        utils.run_command(compose_cmd + ["down"], cwd=constants.BASE_DIR, check=False)
        utils.run_command(compose_cmd + ["up", "-d"], cwd=constants.BASE_DIR)

        logging.info("--- Hysteria2 服务更新完成。 ---")

        # --- 步骤 5: 显示更新后的状态 ---
        self.console.print("\n--- 更新后服务状态 ---")
        self.check()

    def log(self):
        """查看服务日志"""
        self._ensure_service_installed()
        logging.info("正在显示服务日志... (按 Ctrl+C 退出)")
        compose_cmd = self._get_compose_cmd()
        utils.run_command(compose_cmd + ["logs", "-f"], cwd=constants.BASE_DIR, stream_output=True)

    def check(self):
        """检查服务状态并打印客户端配置"""
        self._ensure_service_installed()
        self.console.print("\n--- 开始检查 Hysteria2 服务状态 ---")

        # rich Components
        from rich.table import Table

        table = Table(title="Hysteria2 服务状态一览")
        table.add_column("检查项", justify="right", style="cyan", no_wrap=True)
        table.add_column("状态", style="magenta")

        try:
            # 1. 获取域名
            domain = self._get_domain_from_config()
            table.add_row("管理域名", domain)

            # 2. 检查 Docker 容器状态
            container_name = f"hysteria2-inbound-{domain}"
            try:
                result = utils.run_command(
                    [
                        "docker",
                        "ps",
                        "--filter",
                        f"name={container_name}",
                        "--format",
                        "{{.Status}}",
                    ],
                    capture_output=True,
                    check=True,
                )
                status_output = result.stdout.strip()
                if "Up" in status_output:
                    container_status = f"[green]✔ 正在运行[/green] ({status_output})"
                elif status_output:
                    container_status = f"[yellow]❗ 已停止[/yellow] ({status_output})"
                else:
                    container_status = "[red]❌ 未找到容器[/red]"
            except (subprocess.CalledProcessError, FileNotFoundError):
                container_status = "[red]❌ 检查失败 (Docker 命令错误)[/red]"
            table.add_row("服务容器状态", container_status)

            # 3. 检查配置文件
            if constants.CONFIG_PATH.exists() and constants.DOCKER_COMPOSE_PATH.exists():
                config_status = "[green]✔ 正常[/green]"
            else:
                config_status = "[red]❌ 缺失[/red]"
            table.add_row("核心配置文件", config_status)

            # 获取公网 IP
            public_ip = utils.get_public_ip()
        except Exception as e:
            self.console.print(f"[red]检查过程中出现错误: {e}[/red]")
            return

        self.console.print(table)

        # 4. 基于实时服务端配置生成并打印客户端配置
        try:
            # 从 config.yaml 获取密码和端口
            with constants.CONFIG_PATH.open("r", encoding="utf8") as f:
                server_config = yaml.safe_load(f)
            listener_config = server_config["listeners"][0]
            port = listener_config["port"]
            password = list(listener_config["users"].values())[0]
            self._preview_fmt_client_config(
                domain=domain, public_ip=public_ip, port=port, password=password
            )
        except FileNotFoundError:
            self.console.print("\n[yellow]配置文件未找到，无法生成客户端配置。[/yellow]")
            self.console.print(
                "[yellow]可能是通过旧版本安装的。可以尝试重新运行 'install' 命令以生成。[/yellow]"
            )
            self.console.print("=" * 58 + "\n")
        except Exception as e:
            self.console.print(f"\n[red]生成客户端配置时出错: {e}[/red]")
            self.console.print("=" * 58 + "\n")
