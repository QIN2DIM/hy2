"""
1. 在与 clash_to_share_link.py 同级别的目录下（当前目录），创建一个名为 cfw_config.yaml 的临时文件
2. 将可用的 ClashMeta YAML 运行配置复制进来
3. 运行脚本
4. 所有 ClashMeta YAML 中的节点信息都被转换成 share_link 存储至当前目录的 links.txt
"""

# -*- coding: utf-8 -*-
# Time       : 2024/3/24 23:28
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
from pathlib import Path

import yaml

type2tpl = {
    "hysteria2": "hy2://{password}@{server}:{port}?sni={sni}#{name}",
    "anytls": "anytls://{password}@{server}:{port}?sni={sni}#{name}",
}


def main(
    cfw_path: Path = Path(__file__).parent / "cfw_config.yaml",
    links_path: Path = Path(__file__).parent / "links.txt",
):
    filename = cfw_path.name

    if not cfw_path.is_file():
        cfw_path.write_text("", encoding="utf8")
        print(f"已自动创建缺失的配置文件，请填写 {filename} 后重新运行脚本")
        return

    data = yaml.safe_load(cfw_path.read_text(encoding="utf8"))
    if not isinstance(data, dict):
        print(f"❌ {filename} 文件为空")
        return

    if not data.get("proxies") or not data.get("proxy-groups"):
        print(
            f"❌ 导出 share_link 失败，未能识别 proxies 或 proxy-groups，"
            f"请检查 {filename} 的配置内容。"
        )
        return

    links = []
    for proxy in data.get("proxies", []):
        if proxy["type"] not in type2tpl:
            continue
        share_link = type2tpl[proxy["type"]].format(
            password=proxy["password"],
            server=proxy["server"],
            port=proxy["port"],
            sni=proxy["sni"],
            name=proxy["name"],
        )
        links.append(share_link)

    if links:
        links = sorted(links)
        fulltext = "\n".join(links)
        links_path.write_text(fulltext, encoding="utf8")

        print(fulltext)
        print("\noutput --> ", links_path.resolve())


if __name__ == "__main__":
    main()
