# -*- coding: utf-8 -*-
# Time       : 2023/10/17 15:13
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import base64
import json
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse

import yaml

# 从 NekoRay(v3.23) 批量导出 hysteria2 节点的 NekoLink 分享链接
# nekoray://custom#eyJf ....
neko_links_put = """

"""


def parse_neko_links(neko_links: str):
    neko_links = [
        urlparse(i).fragment for i in neko_links.split("\n") if i.startswith("nekoray://")
    ]
    proxies = []
    for link in neko_links:
        metadata = json.loads(base64.b64decode(link.strip()).decode("utf8"))
        cs = json.loads(metadata["cs"])
        server, port = cs["server"].split(":")
        proxy_node = {
            "name": cs["tls"]["sni"],
            "type": "hysteria2",
            "server": server,
            "port": int(port),
            "password": cs["auth"],
            "sni": cs["tls"]["sni"],
            "skip-cert-verify": cs["tls"]["insecure"],
        }
        proxies.append(proxy_node)

    return proxies


def flat_proxy_group(proxies: List[Dict[str, Any]]) -> List[dict]:
    group = {"name": "PROXY", "type": "select", "proxies": []}
    for proxy_node in proxies:
        group["proxies"].append(proxy_node["name"])

    return [group]


def to_yaml(proxies, groups):
    template_path = Path("templates/clash_config.yaml")
    config = yaml.safe_load(template_path.read_text(encoding="utf8"))
    config.update({"proxies": proxies, "proxy-groups": groups})

    output_path = "clash_verge_config.yaml"
    with open(output_path, "w", encoding="utf8") as file:
        yaml.safe_dump(config, file, sort_keys=False)

    return output_path


def run():
    if not neko_links_put.strip():
        return

    proxies = parse_neko_links(neko_links_put)
    groups = flat_proxy_group(proxies)
    output_path = to_yaml(proxies, groups)

    print(f">> output --> {output_path}")


if __name__ == "__main__":
    run()
