"""
从节点分享链接生成 client-config.yaml
"""
import sys
from contextlib import suppress
from pathlib import Path

import urllib3.util
import yaml
import webbrowser

links_path = Path("links.txt")
if not links_path.exists():
    links_path.write_text("")
    print("--> 将分享链接贴到 ./links.txt 文件中")
    sys.exit()


def get_conf(server: str, port: str, auth: str, sni: str):
    return {
        "server": f"{server}:{port}",
        "auth": auth,
        "tls": {"sni": sni, "insecure": False},
        "fastOpen": True,
        "lazy": True,
        "http": {"listen": "0.0.0.0:2081"},
    }


def load_links():
    for link in filter(None, links_path.read_text().strip().split("\n")):
        parser = urllib3.util.parse_url(link.strip())
        if parser.scheme not in ["hy2", "hysteria2"]:
            continue
        print(f"Load {link}")
        sni = parser.request_uri.split("sni=")[1].split("=")[0]
        conf_ = get_conf(server=parser.host, port=parser.port, auth=parser.auth, sni=sni)

        filename = parser.fragment or sni

        yield filename, conf_


def output_confs(config_path: Path, conf_: dict):
    with open(config_path, "w") as file:
        yaml.safe_dump(conf_, file, sort_keys=False)


def main():
    fdr_conf = Path("configs")
    fdr_conf.mkdir(exist_ok=True, parents=True)

    for filename, conf_ in load_links():
        config_path = fdr_conf.joinpath(f"{filename}.yaml")
        output_confs(config_path, conf_)

    with suppress(Exception):
        webbrowser.open(f"file://{fdr_conf.resolve()}")


if __name__ == "__main__":
    main()
