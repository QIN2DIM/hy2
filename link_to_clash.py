# -*- coding: utf-8 -*-
# Time       : 2023/10/17 15:13
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import base64
import json
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import yaml

links_path = Path("links.txt")
if not links_path.exists():
    links_path.write_text("")
    print("--> 从 NekoRay 导出分享链接（NekoLink）到 ./links.txt 文件中")
    sys.exit()

# 从 NekoRay(v3.23) 批量导出 hysteria2 节点的 NekoLink 分享链接
# nekoray://custom#eyJf ....
# nekoray://hysteria2#eyjf ...
neko_links_put = links_path.read_text(encoding="utf8")


@dataclass
class ProxyNode:
    name: str = field(default=str)
    type: str = "hysteria2"
    server: str = field(default=str)
    port: int = field(default=int)
    password: str = field(default=str)
    sni: str = field(default=str)
    skip_cert_verify: bool = field(default=bool)

    down: str = "200 mbps"
    up: str = "30 mbps"

    def __post_init__(self):
        sl = f"hy2://{self.password}@{self.server}:{self.port}?sni={self.sni}#{self.name}"
        print(sl)

    @classmethod
    def from_neko(cls, link: str):
        parse_result = urlparse(link.strip())

        match parse_result.scheme:
            case "hy2" | "hysteria2":
                password, serv = parse_result.netloc.split("@")
                serv_addr, serv_port = serv.split(":")
                query = parse_result.query.split("&")
                query_unquote = {"sni": ""}
                for i in query:
                    if i.startswith("sni"):
                        query_unquote["sni"] = i.replace("sni=", "")
                    elif i.startswith("insecure"):
                        query_unquote["insecure"] = bool(i.replace("insecure=", ""))
                return cls(
                    name=urllib.parse.unquote(parse_result.fragment),
                    server=serv_addr,
                    port=int(serv_port),
                    password=password,
                    sni=query_unquote["sni"],
                    skip_cert_verify=query_unquote.get("insecure", False),
                )
            case "nekoray":
                code_part = parse_result.fragment
                metadata = json.loads(base64.b64decode(code_part).decode("utf8"))
                # 从自定义配置添加的节点
                if "cs" in metadata:
                    cs = json.loads(metadata["cs"])
                    return cls(
                        name=metadata["name"],
                        server=metadata["addr"],
                        port=metadata["port"],
                        password=cs["auth"],
                        sni=cs["tls"]["sni"],
                        skip_cert_verify=cs["tls"]["insecure"],
                    )
                # Hysteria2 NekoLink
                return cls(
                    name=metadata["name"],
                    server=metadata["addr"],
                    port=metadata["port"],
                    password=metadata["password"],
                    sni=metadata["sni"],
                    skip_cert_verify=metadata["allowInsecure"],
                )
            case _:
                pass

    def to_dict(self):
        c = self.__dict__.copy()
        del c["skip_cert_verify"]
        c["skip-cert-verify"] = self.skip_cert_verify
        return c


@dataclass
class ProxyGroup:
    name: str = "PROXY"
    type: str = "select"
    proxies: List[str] = field(default_factory=list)

    @classmethod
    def from_proxies(cls, proxies: List[ProxyNode], name: str = "PROXY", type_: str = "select"):
        return cls(name=name, type=type_, proxies=[proxy_node.name for proxy_node in proxies])


def parse_neko_links(neko_links: str) -> List[ProxyNode]:
    neko_links = [
        i for i in neko_links.split("\n") if i.startswith("nekoray://") or i.startswith("hy2://")
    ]
    return [ProxyNode.from_neko(link) for link in neko_links]


def run():
    template_path = Path("templates/clash_config.yaml")
    output_path = Path("clash_verge_config.yaml")

    if not neko_links_put.strip():
        print("--> 从 NekoRay 导出分享链接（NekoLink）到 ./links.txt 文件中")
        return

    proxies = parse_neko_links(neko_links_put)
    group = ProxyGroup.from_proxies(proxies)

    proxies = [p.to_dict() for p in proxies]
    groups = [group.__dict__]

    config = yaml.safe_load(template_path.read_text(encoding="utf8"))
    config.update({"proxies": proxies, "proxy-groups": groups})
    output_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf8")

    print(config)
    print(f">> output --> {output_path}")


if __name__ == "__main__":
    run()
