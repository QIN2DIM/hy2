"""
1. 在与 clash_to_sharelink.py 同级别的目录下（当前目录），创建一个名为 cfw_config.yaml 的临时文件
2. 将可用的 ClashMeta YAML 运行配置复制进来
3. 运行脚本
4. 所有 ClashMeta YAML 中的 hy2 节点信息都被转换成 sharelink 存储至当前目录的 links.txt
"""
# -*- coding: utf-8 -*-
# Time       : 2024/3/24 23:28
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
from dataclasses import dataclass
from pathlib import Path

import yaml

cfw_path = Path("cfw_config.yaml").resolve()
links_path = Path("links.txt")

links = []


@dataclass
class Sharelink:
    # hy2://[auth@]hostname[:port]/?[key=value]&[key=value]...
    auth: str
    server: str
    sni: str
    name: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = self.sni

    def __str__(self) -> str:
        """https://hysteria.network/zh/docs/developers/URI-Scheme/"""
        return f"hy2://{self.auth}@{self.server}?sni={self.sni}#{self.name}"


def run(yaml_path: Path):
    fn = yaml_path.name

    if not yaml_path.is_file():
        yaml_path.write_text("", encoding="utf8")
        print(f"自动创建缺失的配置文件，请填写配置后重新运行脚本 - {yaml_path=}")
        raise FileNotFoundError(
            f"Please copy ClashMeta YAML Configuration to the {fn}"
        )

    data = yaml.safe_load(yaml_path.read_text(encoding="utf8"))
    if not isinstance(data, dict):
        raise ValueError(f"{fn} 文件为空")

    if not (proxies := data.get("proxies")):
        print(f"请检查 {fn} 的配置内容，脚本未能识别 proxies 字段，无法进入到 sharelink 导出任务")
        return

    for proxy in proxies:
        if proxy["type"] != "hysteria2":
            continue
        sharelink = Sharelink(
            auth=proxy["password"],
            server=f'{proxy["server"]}:{proxy["port"]}',
            sni=proxy["sni"],
            name=proxy["name"],
        )
        links.append(str(sharelink))
        print(sharelink)

    if links:
        links_path.write_text("\n".join(links))
        print("\noutput --> ", links_path.resolve())


if __name__ == "__main__":
    run(yaml_path=cfw_path)
