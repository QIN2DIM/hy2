# -*- coding: utf-8 -*-
# Time       : 2023/9/2 12:12
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
from __future__ import annotations

import argparse
import getpass
import inspect
import json
import logging
import os
import random
import secrets
import shutil
import socket
import subprocess
import sys
import time
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Literal, NoReturn, Union, Tuple, Any
from urllib.request import urlretrieve, urlopen
from uuid import uuid4

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s - %(levelname)s - %(message)s"
)

if not sys.platform.startswith("linux"):
    logging.error(" Opps~ 你只能在 Linux 操作系统上运行该脚本")
    sys.exit()
if getpass.getuser() != "root":
    logging.error(" Opps~ 你需要手动切换到 root 用户运行该脚本")
    sys.exit()

base_prefix = "https://github.com/apernet/hysteria/releases/download"
executable_name = "hysteria-linux-amd64"

URL = f"{base_prefix}/app%2Fv2.2.3/{executable_name}"

TEMPLATE_SERVICE = """
[Unit]
Description=hysteria2 Service
Documentation=https://v2.hysteria.network/zh/
After=network.target nss-lookup.target

[Service]
Type=simple
User=root
ExecStart={exec_start}
Restart=on-failure
LimitNPROC=512
LimitNOFILE=infinity
WorkingDirectory={working_directory}

[Install]
WantedBy=multi-user.target
"""

# https://adguard-dns.io/kb/zh-CN/general/dns-providers
# https://github.com/MetaCubeX/Clash.Meta/blob/53f9e1ee7104473da2b4ff5da29965563084482d/config/config.go#L891
TEMPLATE_META_CONFIG = """
dns:
  enable: true
  prefer-h3: true
  enhanced-mode: fake-ip
  nameserver:
    - "https://dns.google/dns-query#PROXY"
    - "https://security.cloudflare-dns.com/dns-query#PROXY"
    - "quic://dns.adguard-dns.com"
  proxy-server-nameserver:
    - "https://223.5.5.5/dns-query"
  nameserver-policy:
    "geosite:cn":
      - "https://223.5.5.5/dns-query#h3=true"
rules:
  - GEOSITE,category-scholar-!cn,PROXY
  - GEOSITE,category-ads-all,REJECT
  - GEOSITE,youtube,PROXY
  - GEOSITE,google,PROXY
  - GEOSITE,cn,DIRECT
  - GEOSITE,private,DIRECT
  # - GEOSITE,tracker,DIRECT
  - GEOSITE,steam@cn,DIRECT
  - GEOSITE,category-games@cn,DIRECT
  - GEOSITE,geolocation-!cn,PROXY
  - GEOIP,private,DIRECT,no-resolve
  - GEOIP,telegram,PROXY
  - GEOIP,CN,DIRECT
  - DST-PORT,80/8080/443/8443,PROXY
  - MATCH,DIRECT
"""

TEMPLATE_META_PROXY_ADDONS = """
proxies:
  - {proxy}
proxy-groups:
  - {proxy_group}
"""


def attach_latest_download_url():
    global URL

    with suppress(Exception):
        res = urlopen("https://api.github.com/repos/apernet/hysteria/releases/latest")
        data = json.loads(res.read().decode("utf8"))["tag_name"]
        tag_name = data["tag_name"]
        download_url = f"{base_prefix}/{tag_name}/{executable_name}"
        URL = download_url


@dataclass
class Project:
    workstation_dir = Path("/home/hysteria2")
    executable_path = workstation_dir.joinpath(executable_name)
    server_config_path = workstation_dir.joinpath("server.json")

    nekoray_config_path = workstation_dir.joinpath("nekoray_config.json")
    singbox_config_path = workstation_dir.joinpath("singbox_config.json")
    clash_meta_config_path = workstation_dir.joinpath("clash_meta_config.json")

    service_path = Path("/etc/systemd/system/hysteria2.service")

    cert_path_log = workstation_dir.joinpath("cert_path_log.json")

    # 设置别名
    root_dir = Path(os.path.expanduser("~"))
    bash_aliases_path = root_dir.joinpath(".bashrc")
    _remote_command = "python3 <(curl -fsSL https://ros.services/heyhy.py)"
    _alias = "heyhy"

    _server_ip = ""
    _server_port = -1

    def __post_init__(self):
        os.makedirs(self.workstation_dir, exist_ok=True)

    @staticmethod
    def is_port_in_used(_port: int, proto: Literal["tcp", "udp"]) -> bool | None:
        """Check socket UDP/data_gram or TCP/data_stream"""
        proto2type = {"tcp": socket.SOCK_STREAM, "udp": socket.SOCK_DGRAM}
        socket_type = proto2type[proto]
        with suppress(socket.error), socket.socket(socket.AF_INET, socket_type) as s:
            s.bind(("127.0.0.1", _port))
            return False
        return True

    @property
    def server_ip(self):
        return self._server_ip

    @server_ip.setter
    def server_ip(self, ip: str):
        self._server_ip = ip

    @property
    def server_port(self):
        if self._server_port > 0:
            return self._server_port

        # Try to bind default HTTP/3 port
        http3_port = 443

        if not self.is_port_in_used(http3_port, proto="udp"):
            self._server_port = http3_port
            logging.info(f"正在为 Hysteria2 绑定默认的 HTTP/3 端口 - port={http3_port}")
            return self._server_port

        # Catch-all rule
        rand_ports = list(range(41670, 46990))
        random.shuffle(rand_ports)
        for p in rand_ports:
            if not self.is_port_in_used(p, proto="udp"):
                self._server_port = p
                logging.info(f"正在初始化监听端口 - port={p}")
                return self._server_port

    @property
    def alias(self):
        # redirect to https://raw.githubusercontent.com/QIN2DIM/hy2/main/heyhy.py
        return f"alias {self._alias}='{self._remote_command}'"

    def set_alias(self):
        if self.bash_aliases_path.exists():
            pre_text = self.bash_aliases_path.read_text(encoding="utf8")
            for ck in [f"\n{self.alias}\n", f"\n{self.alias}", f"{self.alias}\n", self.alias]:
                if ck in pre_text:
                    return
        with open(self.bash_aliases_path, "a", encoding="utf8") as file:
            file.write(f"\n{self.alias}\n")
        logging.info(f"✅ 现在你可以通过别名唤起脚本 - alias={self._alias}")

    def remove_alias(self):
        histories = [self.root_dir.joinpath(".bash_aliases"), self.bash_aliases_path]
        for hp in histories:
            if not hp.exists():
                continue
            text = hp.read_text(encoding="utf8")
            for ck in [f"\n{self.alias}\n", f"\n{self.alias}", f"{self.alias}\n", self.alias]:
                text = text.replace(ck, "")
            hp.write_text(text, encoding="utf8")

    @staticmethod
    def reset_shell() -> NoReturn:
        # Reload Linux SHELL and refresh alias values
        os.execl(os.environ["SHELL"], "bash", "-l")

    @property
    def systemd_template(self) -> str:
        # https://v2.hysteria.network/zh/docs/getting-started/Server/
        return TEMPLATE_SERVICE.format(
            exec_start=f"{self.executable_path} server -c {self.server_config_path}",
            working_directory=f"{self.workstation_dir}",
        )

    def log_cert(self, cert: Certificate):
        msg = {"fullchain": cert.fullchain, "privkey": cert.privkey}
        self.cert_path_log.write_text(json.dumps(msg))


@dataclass
class Certificate:
    domain: str
    _fullchain = ""
    _privkey = ""

    def __post_init__(self):
        self._fullchain = f"/etc/letsencrypt/live/{self.domain}/fullchain.pem"
        self._privkey = f"/etc/letsencrypt/live/{self.domain}/privkey.pem"

    @property
    def fullchain(self):
        return self._fullchain

    @fullchain.setter
    def fullchain(self, cert_path: Path):
        self._fullchain = str(cert_path)

    @property
    def privkey(self):
        return self._privkey

    @privkey.setter
    def privkey(self, key_path: Path):
        self._privkey = str(key_path)


class CertBot:
    def __init__(self, domain: str):
        self._domain = domain

        self._should_revive_port_80 = False
        self._is_success = True

    def _cert_pre_hook(self):
        # Fallback strategy: Ensure smooth flow of certificate requests
        p = Path("/etc/letsencrypt/live/")
        if p.exists():
            logging.info("移除證書殘影...")
            for k in os.listdir(p):
                k_full = p.joinpath(k)
                if (
                    not p.joinpath(self._domain).exists()
                    and k.startswith(f"{self._domain}-")
                    and k_full.is_dir()
                ):
                    shutil.rmtree(k_full, ignore_errors=True)

        logging.info("正在为解析到本机的域名申请免费证书")

        logging.info("正在更新包索引")
        os.system("apt update -y > /dev/null 2>&1 ")

        logging.info("安装 certbot")
        os.system("apt install certbot -y > /dev/null 2>&1")

        # Pre-hook strategy: stop process running in port 80
        logging.info("检查 80 端口占用")
        if Project.is_port_in_used(80, proto="tcp"):
            os.system("systemctl stop nginx > /dev/null 2>&1 && nginx -s stop > /dev/null 2>&1")
            os.system("kill $(lsof -t -i:80)  > /dev/null 2>&1")
            self._should_revive_port_80 = True

    def _cert_post_hook(self):
        # Post-hook strategy: restart process running in port 80
        if self._should_revive_port_80:
            os.system("systemctl restart nginx > /dev/null 2>&1")
            self._should_revive_port_80 = False

        # Exception: certs 5 per 7 days
        if not self._is_success:
            sys.exit()

        # This operation ensures that certbot.timer is started
        logging.info(f"运行证书续订服务 - service=certbot.timer")
        os.system(f"systemctl daemon-reload && systemctl enable --now certbot.timer")

    def _run(self):
        logging.info("开始申请证书")
        cmd = (
            "certbot certonly "
            "--standalone "
            "--register-unsafely-without-email "
            "--agree-tos "
            "--keep "
            "--non-interactive "
            "-d {domain}"
        )
        p = subprocess.Popen(
            cmd.format(domain=self._domain).split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            text=True,
        )
        output = p.stderr.read().strip()
        if output and "168 hours" in output:
            logging.warning(
                """
                一个域名每168小时只能申请5次免费证书，
                你可以为当前主机创建一条新的域名A纪录来解决这个问题。
                在解决这个问题之前你没有必要进入到后续的安装步骤。
                """
            )
            self._is_success = False

    def run(self):
        self._cert_pre_hook()
        self._run()
        self._cert_post_hook()

    def remove(self):
        """可能存在重复申请的 domain-0001"""
        logging.info("移除可能残留的证书文件")
        p = subprocess.Popen(
            f"certbot delete --cert-name {self._domain}".split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        p.stdin.write("y\n")
        p.stdin.flush()

        # 兜底
        shutil.rmtree(Path(Certificate(self._domain).fullchain).parent, ignore_errors=True)


@dataclass
class Service:
    path: Path
    name: str = "hysteria2"

    @classmethod
    def build_from_template(cls, path: Path, template: str | None = ""):
        if template:
            path.write_text(template, encoding="utf8")
            os.system("systemctl daemon-reload")
        return cls(path=path)

    def download_server(self, workstation: Path):
        ex_path = workstation.joinpath(executable_name)

        try:
            urlretrieve(URL, f"{ex_path}")
            logging.info(f"下载完毕 - ex_path={ex_path}")
        except OSError:
            logging.info("服务正忙，尝试停止任务...")
            self.stop()
            time.sleep(0.5)
            return self.download_server(workstation)
        else:
            os.system(f"chmod +x {ex_path}")
            os.system(f"sudo setcap cap_net_bind_service=+ep {ex_path}")
            logging.info(f"授予执行权限 - ex_path={ex_path}")

    def start(self):
        """部署服务之前需要先初始化服务端配置并将其写到工作空间"""
        os.system(f"systemctl enable --now {self.name}")
        logging.info("系统服务已启动")
        logging.info("已设置服务开机自启")

    def stop(self):
        logging.info("停止系统服务")
        os.system(f"systemctl stop {self.name} > /dev/null 2>&1")

    def restart(self):
        logging.info("重启系统服务")
        os.system(f"systemctl daemon-reload && systemctl restart {self.name}")

    def status(self) -> Tuple[bool, str]:
        result = subprocess.run(
            f"systemctl is-active {self.name}".split(), capture_output=True, text=True
        )
        text = result.stdout.strip()
        response = None
        if text == "inactive":
            text = "\033[91m" + text + "\033[0m"
        elif text == "active":
            text = "\033[32m" + text + "\033[0m"
            response = True
        return response, text

    def remove(self, workstation: Path):
        logging.info("注销系统服务")
        os.system(f"systemctl disable --now {self.name} > /dev/null 2>&1")

        logging.info("移除系统服务配置文件")
        if self.path.exists():
            os.remove(self.path)

        logging.info("移除工作空间")
        shutil.rmtree(workstation)


# =================================== Runtime Settings ===================================


def from_dict_to_cls(cls, data):
    return cls(
        **{
            key: (data[key] if val.default == val.empty else data.get(key, val.default))
            for key, val in inspect.signature(cls).parameters.items()
        }
    )


@dataclass
class User:
    username: str
    password: str

    @classmethod
    def gen(cls):
        return cls(username=str(uuid4()), password=secrets.token_hex()[:32])


@dataclass
class ServerConfig:
    """
    Config template of hysteria2
    https://v2.hysteria.network/zh/docs/getting-started/Server/
    """

    listen: str | int
    tls: Dict[str, str]
    auth: Dict[str, str]
    masquerade: Dict[str, str]
    quic: Dict[str, str]
    bandwidth: Dict[str, str]
    ignoreClientBandwidth: bool = False
    disableUDP: bool = False
    udpIdleTimeout: str = "60s"

    def __post_init__(self):
        if isinstance(self.listen, int):
            self.listen = str(self.listen)
        if not self.listen.startswith(":"):
            self.listen = f":{self.listen}"

    @classmethod
    def from_automation(cls, user: User, path_fullchain: str, path_privkey: str, server_port: int):
        tls = {"cert": path_fullchain, "key": path_privkey}
        auth = {"type": "password", "password": user.password}
        masquerade = {
            "type": "proxy",
            "proxy": {"url": "https://cocodataset.org/", "rewriteHost": True},
        }
        quic = {
            "initStreamReceiveWindow": 8388608,
            "maxStreamReceiveWindow": 8388608,
            "initConnReceiveWindow": 20971520,
            "maxConnReceiveWindow": 20971520,
            "maxIdleTimeout": "30s",
            "maxIncomingStreams": 1024,
            "disablePathMTUDiscovery": False,
        }
        bandwidth = {"up": "1 gbps", "down": "1 gbps"}
        return cls(
            listen=server_port,
            tls=tls,
            auth=auth,
            masquerade=masquerade,
            quic=quic,
            bandwidth=bandwidth,
        )

    def to_json(self, sp: Path):
        sp.write_text(json.dumps(self.__dict__, indent=4, ensure_ascii=True))
        logging.info(f"保存服务端配置文件 - save_path={sp}")


@dataclass
class NekoRayConfig:
    """
    https://v2.hysteria.network/zh/docs/getting-started/Client/
    Config template of hysteria2 client
    Apply on the NekoRay(v3.8+)
    """

    server: str
    auth: str
    tls: Dict[str, str]
    fastOpen: bool = True
    lazy: bool = True
    socks5: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_server(cls, user: User, server_addr: str, server_port: int, server_ip: str):
        auth = user.password
        tls = {"sni": server_addr, "insecure": False}
        socks5 = {"listen": "127.0.0.1:%socks_port%"}
        return cls(server=f"{server_ip}:{server_port}", auth=auth, tls=tls, socks5=socks5)

    @classmethod
    def from_json(cls, sp: Path):
        data = json.loads(sp.read_text(encoding="utf8"))
        return from_dict_to_cls(cls, data)

    def to_json(self, sp: Path):
        sp.write_text(json.dumps(self.__dict__, indent=4, ensure_ascii=True))

    @property
    def showcase(self) -> str:
        return json.dumps(self.__dict__, indent=4, ensure_ascii=True)

    @property
    def sharelink(self) -> str:
        """https://hysteria.network/zh/docs/developers/URI-Scheme/"""
        return f"hysteria2://{self.auth}@{self.server}?sni={self.tls['sni']}#{self.tls['sni']}"

    @property
    def serv_peer(self) -> Tuple[str, str]:
        serv_addr, serv_port = self.server.split(":")
        return serv_addr, serv_port


@dataclass
class SingBoxConfig:
    """
    https://sing-box.sagernet.org/zh/configuration/outbound/hysteria2/#server
    """

    server: str
    server_port: int
    password: str
    tls: Dict[str, Any] = field(default_factory=dict)
    type: str = "hysteria2"
    tag: str = "hy2-out"

    @classmethod
    def from_server(cls, user: User, server_addr: str, server_port: int, server_ip: str):
        return cls(
            server=server_ip,
            server_port=server_port,
            password=user.password,
            tls={
                "enabled": True,
                "disable_sni": False,
                "server_name": server_addr,
                "insecure": False,
            },
        )

    @classmethod
    def from_json(cls, sp: Path):
        data = json.loads(sp.read_text(encoding="utf8"))
        return from_dict_to_cls(cls, data)

    def to_json(self, sp: Path):
        sp.write_text(json.dumps(self.__dict__, indent=4, ensure_ascii=True))

    @property
    def showcase(self) -> str:
        return json.dumps(self.__dict__, indent=4, ensure_ascii=True)


@dataclass
class ClashMetaConfig:
    # 在 meta_config.yaml 中的配置内容
    contents: str

    @classmethod
    def from_server(cls, user: User, server_addr: str, server_port: int, server_ip: str):
        def from_string_to_yaml(s: str):
            _suffix = ", "
            fs = _suffix.join([i.strip() for i in s.split("\n") if i])
            fs = fs[: len(fs) - len(_suffix)]
            return "{ " + fs + " }"

        def remove_empty_lines(s: str):
            lines = s.split("\n")
            non_empty_lines = [line for line in lines if line.strip()]
            return "\n".join(non_empty_lines)

        name = "hysteria2"

        # https://github.com/MetaCubeX/Clash.Meta/blob/f6bf9c08577060bb199c2f746c7d91dd3c0ca7b9/adapter/outbound/hysteria2.go#L41
        proxy = f"""
        name: "{name}"
        type: hysteria2
        server: {server_ip}
        port: {server_port}
        password: {user.password}
        sni: {server_addr}
        skip-cert-verify: false
        """

        # https://wiki.metacubex.one/config/proxy-groups/select/
        proxy_group = f"""
        name: PROXY
        type: select
        proxies: ["{name}"]
        """

        proxy = from_string_to_yaml(proxy)
        proxy_group = from_string_to_yaml(proxy_group)

        addons = TEMPLATE_META_PROXY_ADDONS.format(proxy=proxy, proxy_group=proxy_group)
        contents = TEMPLATE_META_CONFIG + addons
        contents = remove_empty_lines(contents)

        return cls(contents=contents)

    def to_yaml(self, sp: Path):
        sp.write_text(self.contents + "\n")


# =================================== DataModel ===================================


TEMPLATE_PRINT_NEKORAY = """
\033[36m--> NekoRay 自定义核心配置\033[0m
# 名称：(custom)
# 地址：{server_addr}
# 端口：{listen_port}
# 核心：hysteria2
# 命令：-c %config%

{nekoray_config}
"""

TEMPLATE_PRINT_SHARELINK = """
\033[36m--> Hysteria2 通用订阅\033[0m
\033[34m{sharelink}\033[0m
"""

TEMPLATE_PRINT_META = """
\033[36m--> Clash.Meta 配置文件输出路径\033[0m
{meta_path}
"""

TEMPLATE_PRINT_SINGBOX = """
\033[36m--> sing-box hysteria2 客户端出站配置\033[0m
{singbox_config}
"""


class Template:
    def __init__(self, project: Project, mode: Literal["install", "check"] = "check"):
        self.project = project
        self.mode = mode

    def gen_clients(self, server_addr: str, user: User, server_config: ServerConfig):
        logging.info("正在生成客户端配置文件")
        project = self.project

        # 生成客户端通用实例
        server_ip, server_port = project.server_ip, project.server_port

        # 生成 NekoRay 客户端配置实例
        # https://matsuridayo.github.io/n-extra_core/
        nekoray = NekoRayConfig.from_server(user, server_addr, server_port, server_ip)
        nekoray.to_json(project.nekoray_config_path)

        # 生成 sing-box 客户端出站配置
        # https://sing-box.sagernet.org/configuration/outbound/hysteria2/
        singbox = SingBoxConfig.from_server(user, server_addr, server_port, server_ip)
        singbox.to_json(project.singbox_config_path)

        # 生成 Clash.Meta 客户端配置
        # https://github.com/MetaCubeX/Clash.Meta/blob/Alpha/adapter/outbound/hysteria2.go#L41
        meta = ClashMetaConfig.from_server(user, server_addr, server_port, server_ip)
        meta.to_yaml(project.clash_meta_config_path)

    def print_nekoray(self):
        if not self.project.nekoray_config_path.exists():
            logging.error(f"❌ 客户端配置文件不存在 - path={self.project.nekoray_config_path}")
        else:
            nekoray = NekoRayConfig.from_json(self.project.nekoray_config_path)
            serv_addr, serv_port = nekoray.serv_peer
            print(TEMPLATE_PRINT_SHARELINK.format(sharelink=nekoray.sharelink))
            print(
                TEMPLATE_PRINT_NEKORAY.format(
                    server_addr=serv_addr, listen_port=serv_port, nekoray_config=nekoray.showcase
                )
            )

    def print_clash_meta(self):
        if not self.project.clash_meta_config_path.exists():
            logging.error(f"❌ 客户端配置文件不存在 - path={self.project.clash_meta_config_path}")
        elif self.mode == "install":
            print(TEMPLATE_PRINT_META.format(meta_path=self.project.clash_meta_config_path))
        elif self.mode == "check":
            print(TEMPLATE_PRINT_META.format(meta_path=self.project.clash_meta_config_path))
            print("\033[36m--> Clash.Meta 配置信息\033[0m")
            print(self.project.clash_meta_config_path.read_text())

    def print_singbox(self):
        if not self.project.singbox_config_path.exists():
            logging.error(f"❌ 客户端配置文件不存在 - path={self.project.singbox_config_path}")
        else:
            singbox = SingBoxConfig.from_json(self.project.singbox_config_path)
            print(TEMPLATE_PRINT_SINGBOX.format(singbox_config=singbox.showcase))

    def parse(self, params: argparse):
        show_all = not any([params.nekoray, params.singbox, params.server, params.clash])
        if show_all:
            self.print_nekoray()
            self.print_singbox()
            self.print_clash_meta()
            return

        # select mode
        os.system("clear")
        if params.nekoray:
            self.print_nekoray()
        elif params.singbox:
            self.print_singbox()
        elif params.server:
            os.system(f"more {Project.server_config_path}")
        elif params.clash:
            self.print_clash_meta()
        elif params.v2ray:
            logging.warning("Unimplemented feature")


class Scaffold:
    @staticmethod
    def _handle_cert(domain: str, params: argparse.Namespace) -> Certificate | NoReturn:
        cert = Certificate(domain)

        if any([params.cert, params.key]) and not all([params.cert, params.key]):
            logging.error("參數 `--cert` 与 `--key` 需要一起使用")
            sys.exit()

        # 当指定 fullchain 时，认为宿主机已安装证书并存到参数指向的绝对路径
        # 而不是自定义一个路径用于修改 certbot 默认的着陆点
        if all([params.cert, params.key]):
            fullchain_path = Path(params.cert)
            privkey_path = Path(params.key)
            # 期望用户给出 *.pem 格式的证书，无法使用 cryptography 做前置验证
            # 错误的证书链接不影响脚本运行，但最终 hy2 服务端必然启动失败
            for p in [fullchain_path, privkey_path]:
                if not p.is_absolute():
                    logging.error(f"配置证书时必须使用绝对路径 - path={p}")
                    sys.exit()
                if not p.is_file():
                    logging.error(f"应指向证书文件而非文件夹 - path={p}")
                    sys.exit()
                if not p.exists():
                    logging.error(f"拼写错误或指定的证书文件不存在 - path={p}")
                    sys.exit()

            cert.fullchain = fullchain_path
            cert.privkey = privkey_path

        # 调用 certbot 安装证书或跳过已存在的步骤
        if not Path(cert.fullchain).exists():
            CertBot(domain).run()
        else:
            logging.info(f"证书文件已存在 - path={Path(cert.fullchain).parent}")

        return cert

    @staticmethod
    def _validate_domain(domain: str | None) -> Union[NoReturn, Tuple[str, str]]:
        """
        # Check dualstack: socket.getaddrinfo(DOMAIN, PORT=None)
        # Check only IPv4: socket.gethostbyname(DOMAIN)
        addrs = socket.getaddrinfo(domain, None)
            for info in addrs:
                ip = info[4][0]
                if ":" not in ip:
                    server_ipv4 = ip
            server_ip = server_ipv4
        :param domain:
        :return: Tuple[domain, server_ip]
        """
        if not domain:
            domain = input("> 解析到本机的域名：")

        server_ipv4, my_ip = "", ""

        # 查詢傳入的域名鏈接的端點 IPv4
        try:
            server_ipv4 = socket.gethostbyname(domain)
        except socket.gaierror:
            logging.error(f"域名不可达或拼写错误的域名 - domain={domain}")

        # 查詢本機訪問公網的 IPv4
        response = urlopen("https://ifconfig.me")
        my_ip = response.read().decode("utf-8") or my_ip

        # 判斷傳入的域名是否链接到本机 fixme
        if my_ip == server_ipv4 or ":" in my_ip:
            return domain, server_ipv4

        logging.error(
            f"你的主机外网IP与域名解析到的IP不一致 - my_ip={my_ip} domain={domain} server_ip={server_ipv4}"
        )

        # 域名解析错误，应当阻止用户执行安装脚本
        sys.exit()

    @staticmethod
    def _recv_stream(script: str, pipe: Literal["stdout", "stderr"] = "stdout") -> str:
        p = subprocess.Popen(
            script.split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            text=True,
        )
        if pipe == "stdout":
            return p.stdout.read().strip()
        if pipe == "stderr":
            return p.stderr.read().strip()

    @staticmethod
    def install(params: argparse.Namespace):
        """
        1. 运行 certbot 申请证书
        3. 初始化 Project 环境对象
        4. 初始化 server config
        5. 初始化 client config
        6. 生成 client config 配置信息
        :param params:
        :return:
        """
        (domain, server_ip) = Scaffold._validate_domain(params.domain)
        logging.info(f"域名解析成功 - domain={domain}")

        # 初始化证书对象
        cert = Scaffold._handle_cert(domain, params)

        # 初始化 workstation
        project = Project()
        user = User.gen()
        if params.password:
            user.password = params.password

        # 设置脚本别名
        project.set_alias()
        project.log_cert(cert)

        # 初始化系统服务配置
        project.server_ip = server_ip
        service = Service.build_from_template(
            path=project.service_path, template=project.systemd_template
        )

        # 尝试释放 443 端口占用
        service.stop()
        server_port = project.server_port

        logging.info(f"正在下载 hysteria2-server")
        service.download_server(project.workstation_dir)

        logging.info("正在生成默认的服务端配置")
        server_config = ServerConfig.from_automation(
            user, cert.fullchain, cert.privkey, server_port
        )
        server_config.to_json(project.server_config_path)

        logging.info("正在部署系统服务")
        service.start()

        logging.info("正在检查服务状态")
        (response, text) = service.status()

        # 在控制台输出客户端配置
        if response is True:
            t = Template(project, mode="install")
            t.gen_clients(domain, user, server_config)
            t.parse(params)
            project.reset_shell()
        else:
            logging.info(f"服务启动失败 - status={text}")

    @staticmethod
    def remove(params: argparse.Namespace):
        (domain, _) = Scaffold._validate_domain(params.domain)
        logging.info(f"解绑服务 - bind={domain}")

        project = Project()

        # 移除脚本别名
        project.remove_alias()

        # 移除可能残留的证书文件
        CertBot(domain).remove()

        # 关停进程，注销系统服务，移除工作空间
        service = Service.build_from_template(project.service_path)
        service.remove(project.workstation_dir)

        project.reset_shell()

    @staticmethod
    def check(params: argparse.Namespace, mode: Literal["install", "check"] = "check"):
        project = Project()
        Template(project, mode).parse(params)

    @staticmethod
    def service_relay(cmd: str):
        project = Project()
        service = Service.build_from_template(path=project.service_path)

        if cmd == "status":
            os.system("clear")
            os.system(f"{Project.executable_path} version")
            os.system(f"systemctl status {Service.name} --lines=0")
            ct_active = Scaffold._recv_stream("systemctl is-active certbot.timer")
            logging.info(f"证书续订服务状态：{ct_active}")
            if project.cert_path_log.exists():
                cert_log = json.loads(project.cert_path_log.read_text(encoding="utf8"))
                for alt, fp in cert_log.items():
                    logging.info(f"{alt}: {fp}")
            logging.info(f"服務端配置：{project.server_config_path}")
            logging.info(f"客戶端配置[NekoRay]：{project.nekoray_config_path}")
            logging.info(f"客戶端配置[sing-box]：{project.singbox_config_path}")
            logging.info(f"系统服务配置：{project.service_path}")
        elif cmd == "log":
            os.system("clear")
            os.system(f"{Project.executable_path} version")
            os.system(f"journalctl -f -o cat -u {service.name}")
        elif cmd == "start":
            service.start()
        elif cmd == "stop":
            service.stop()
        elif cmd == "restart":
            service.restart()


def run():
    parser = argparse.ArgumentParser(description="Hysteria-v2 Scaffold (Python3.7+)")
    subparsers = parser.add_subparsers(dest="command")

    install_parser = subparsers.add_parser("install", help="Automatically install and run")
    install_parser.add_argument("-d", "--domain", type=str, help="传参指定域名，否则需要在运行脚本后以交互的形式输入")
    install_parser.add_argument("--cert", type=str, help="/path/to/fullchain.pem")
    install_parser.add_argument("--key", type=str, help="/path/to/privkey.pem")
    install_parser.add_argument("-U", "--upgrade", action="store_true", help="下载最新版预编译文件")
    install_parser.add_argument("-p", "--password", type=str, help="password")

    remove_parser = subparsers.add_parser("remove", help="Uninstall services and associated caches")
    remove_parser.add_argument("-d", "--domain", type=str, help="传参指定域名，否则需要在运行脚本后以交互的形式输入")

    check_parser = subparsers.add_parser("check", help="Print client configuration")

    subparsers.add_parser("status", help="Check hysteria2 service status")
    subparsers.add_parser("log", help="Check hysteria2 service syslog")
    subparsers.add_parser("start", help="Start hysteria2 service")
    subparsers.add_parser("stop", help="Stop hysteria2 service")
    subparsers.add_parser("restart", help="restart hysteria2 service")

    for c in [check_parser, install_parser]:
        c.add_argument("--server", action="store_true", help="show server config")
        c.add_argument("--nekoray", action="store_true", help="show NekoRay config")
        c.add_argument("--clash", action="store_true", help="show Clash.Meta config")
        # c.add_argument("--v2ray", action="store_true", help="show v2rayN config")
        c.add_argument("--singbox", action="store_true", help="show sing-box config")

    args = parser.parse_args()
    command = args.command

    with suppress(KeyboardInterrupt):
        if command == "install":
            if args.upgrade:
                attach_latest_download_url()
            Scaffold.install(params=args)
        elif command == "remove":
            Scaffold.remove(params=args)
        elif command == "check":
            Scaffold.check(params=args)
        elif command in ["status", "log", "start", "stop", "restart"]:
            Scaffold.service_relay(command)
        else:
            parser.print_help()


if __name__ == "__main__":
    run()
