# -*- coding: utf-8 -*-
# Time       : 2023/10/17 15:13
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import base64
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import yaml

# 从 NekoRay(v3.23) 批量导出 hysteria2 节点的 NekoLink 分享链接
# nekoray://custom#eyJf ....
neko_links_put = """
"""


@dataclass
class ProxyNode:
    name: str = field(default=str)
    type: str = "hysteria2"
    server: str = field(default=str)
    port: int = field(default=int)
    password: str = field(default=str)
    sni: str = field(default=str)
    skip_cert_verify: bool = field(default=bool)

    @classmethod
    def from_neko(cls, link: str):
        code_part = urlparse(link.strip()).fragment
        metadata = json.loads(base64.b64decode(code_part).decode("utf8"))
        cs = json.loads(metadata["cs"])
        return cls(
            name=metadata["name"],
            server=metadata["addr"],
            port=metadata["port"],
            password=cs["auth"],
            sni=cs["tls"]["sni"],
            skip_cert_verify=cs["tls"]["insecure"],
        )

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
    neko_links = [i for i in neko_links.split("\n") if i.startswith("nekoray://")]
    return [ProxyNode.from_neko(link) for link in neko_links]


def run():
    template_path = Path("templates/clash_config.yaml")
    output_path = Path("clash_verge_config.yaml")

    if not neko_links_put.strip():
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
