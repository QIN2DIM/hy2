"""
Clash.Meta YAML 配置转换为 Surge .conf 配置

1. 在与 clash_to_surge.py 同级别的目录下（当前目录），创建一个名为 cfw_config.yaml 的临时文件
2. 将可用的 ClashMeta YAML 运行配置复制进来
3. 运行脚本
4. 所有 ClashMeta YAML 中的节点信息都被转换成 Surge .conf 格式存储至当前目录的 surge_config.conf

支持协议：hysteria2, anytls
参考文档：https://manual.nssurge.com/policy/proxy.html
"""

# -*- coding: utf-8 -*-
# Time       : 2026/1/5
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description: Convert Clash.Meta YAML to Surge .conf

from pathlib import Path
from typing import Any

import yaml


def convert_hysteria2(proxy: dict[str, Any]) -> str | None:
    """
    Convert Clash hysteria2 proxy to Surge format.

    Surge format:
    Proxy-Hysteria = hysteria2, server, port, password=pwd, download-bandwidth=100

    Optional params: sni, skip-cert-verify, download-bandwidth, port-hopping, port-hopping-interval
    """
    name = proxy.get("name")
    server = proxy.get("server")
    port = proxy.get("port")
    password = proxy.get("password")

    if not all([name, server, port, password]):
        return None

    parts = [f"{name} = hysteria2", str(server), str(port), f"password={password}"]

    # SNI
    sni = proxy.get("sni")
    if sni:
        parts.append(f"sni={sni}")

    # Skip certificate verification
    skip_cert_verify = proxy.get("skip-cert-verify", False)
    if skip_cert_verify:
        parts.append("skip-cert-verify=true")

    # Download bandwidth (Mbps)
    down = proxy.get("down")
    if down:
        # Clash uses "down" field, convert to Mbps if needed
        # Clash format might be "100 Mbps" or just a number
        if isinstance(down, str):
            down = down.lower().replace("mbps", "").replace(" ", "")
        parts.append(f"download-bandwidth={down}")

    # ECH (Encrypted Client Hello)
    ech = proxy.get("ech")
    if ech:
        parts.append("ech=true")

    return ", ".join(parts)


def convert_anytls(proxy: dict[str, Any]) -> str | None:
    """
    Convert Clash anytls proxy to Surge format.

    Surge format:
    Proxy-AnyTLS = anytls, server, port, password=pwd

    Optional params: sni, skip-cert-verify, reuse
    """
    name = proxy.get("name")
    server = proxy.get("server")
    port = proxy.get("port")
    password = proxy.get("password")

    if not all([name, server, port, password]):
        return None

    parts = [f"{name} = anytls", str(server), str(port), f"password={password}"]

    # SNI
    sni = proxy.get("sni")
    if sni:
        parts.append(f"sni={sni}")

    # Skip certificate verification
    skip_cert_verify = proxy.get("skip-cert-verify", False)
    if skip_cert_verify:
        parts.append("skip-cert-verify=true")

    # Connection reuse (enabled by default in AnyTLS v2)
    reuse = proxy.get("reuse")
    if reuse is False:
        parts.append("reuse=false")

    return ", ".join(parts)


CONVERTERS = {"hysteria2": convert_hysteria2, "anytls": convert_anytls}


# Surge 支持的规则类型
# 参考: https://manual.nssurge.com/rule.html
# 参考: https://manual.nssurge.com/rule/domain-based.html
SURGE_SUPPORTED_RULE_TYPES = {
    # Domain-based rules
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "DOMAIN-SET",
    # IP-based rules
    "IP-CIDR",
    "IP-CIDR6",
    "GEOIP",
    "IP-ASN",
    # HTTP rules
    "USER-AGENT",
    "URL-REGEX",
    # Process rules
    "PROCESS-NAME",
    # Misc rules
    "DEST-PORT",
    "IN-PORT",
    "SRC-IP",
    "PROTOCOL",
    # Ruleset
    "RULE-SET",
}

# Clash → Surge 规则类型映射
# MATCH → FINAL
# GEOSITE → 需要手动转换为 RULE-SET (Surge 不支持 GEOSITE)


def convert_rule(rule: str, valid_policies: set[str]) -> tuple[str | None, str | None]:
    """
    Convert a single Clash rule to Surge format.

    Returns:
        tuple: (converted_rule, warning_message)
        - converted_rule: The Surge format rule, or None if cannot convert
        - warning_message: Optional warning about the conversion
    """
    rule = rule.strip()
    if not rule or rule.startswith("#"):
        return None, None

    parts = rule.split(",")
    if len(parts) < 2:
        return None, f"无效规则格式: {rule}"

    rule_type = parts[0].strip().upper()

    # Handle MATCH/FINAL rule (only 2 parts: MATCH,POLICY)
    if rule_type == "MATCH":
        policy = parts[1].strip()
        return f"FINAL,{policy}", None

    if len(parts) < 3:
        return None, f"规则缺少策略: {rule}"

    matcher = parts[1].strip()
    policy = parts[2].strip()
    extra_params = [p.strip() for p in parts[3:]] if len(parts) > 3 else []

    # Handle GEOSITE (Clash-specific, Surge doesn't support)
    # Convert to comment with suggestion to use RULE-SET
    if rule_type == "GEOSITE":
        return None, f"GEOSITE 不被 Surge 支持，请使用 RULE-SET 替代: GEOSITE,{matcher},{policy}"

    # Handle AND/OR/NOT logical rules (Surge uses different syntax)
    if rule_type in ("AND", "OR", "NOT"):
        return None, f"逻辑规则需要手动转换: {rule}"

    # Check if rule type is directly supported by Surge
    if rule_type in SURGE_SUPPORTED_RULE_TYPES:
        # Build the Surge rule
        surge_rule_parts = [rule_type, matcher, policy]

        # Handle extra parameters (like no-resolve)
        for param in extra_params:
            param_lower = param.lower()
            if param_lower == "no-resolve":
                surge_rule_parts.append("no-resolve")
            # Add other param handling as needed

        return ",".join(surge_rule_parts), None

    # Unknown rule type
    return None, f"不支持的规则类型: {rule_type}"


def convert_rules(
    rules: list[str], valid_policies: set[str]
) -> tuple[list[str], list[str], list[str]]:
    """
    Convert Clash rules to Surge format.

    Args:
        rules: List of Clash rule strings
        valid_policies: Set of valid policy names (proxies + groups)

    Returns:
        tuple: (converted_rules, skipped_geosite_comments, warnings)
    """
    converted = []
    geosite_comments = []
    warnings = []

    for rule in rules:
        result, warning = convert_rule(rule, valid_policies)

        if warning:
            if "GEOSITE" in warning:
                # Extract the original rule for comment
                geosite_comments.append(f"# {warning}")
            else:
                warnings.append(warning)

        if result:
            converted.append(result)

    # Ensure FINAL rule exists and is at the end
    has_final = any(r.startswith("FINAL,") for r in converted)
    if not has_final:
        converted.append("FINAL,DIRECT")
    else:
        # Move FINAL to the end if it exists
        final_rules = [r for r in converted if r.startswith("FINAL,")]
        other_rules = [r for r in converted if not r.startswith("FINAL,")]
        converted = other_rules + final_rules[-1:]  # Keep only the last FINAL

    return converted, geosite_comments, warnings


def convert_proxy_groups(groups: list[dict], valid_proxy_names: set[str]) -> list[str]:
    """
    Convert Clash proxy-groups to Surge Proxy Group format.

    Surge format:
    GroupName = select, Proxy1, Proxy2, ...
    """
    lines = []

    # First pass: collect all group names
    all_group_names = {g.get("name") for g in groups if g.get("name")}

    # Valid references include: proxies, other groups, and built-in policies
    valid_refs = valid_proxy_names | all_group_names | {"DIRECT", "REJECT"}

    for group in groups:
        name = group.get("name")
        group_type = group.get("type", "select")
        proxies = group.get("proxies", [])

        if not name or not proxies:
            continue

        # Filter proxies to only include valid ones
        filtered_proxies = [p for p in proxies if p in valid_refs]

        if not filtered_proxies:
            continue

        # Map Clash group types to Surge group types
        surge_type_map = {
            "select": "select",
            "url-test": "url-test",
            "fallback": "fallback",
            "load-balance": "load-balance",
        }

        surge_type = surge_type_map.get(group_type, "select")

        parts = [f"{name} = {surge_type}"] + filtered_proxies

        # Add test URL and parameters for auto groups
        if surge_type in ("url-test", "fallback"):
            url = group.get("url", "http://www.gstatic.com/generate_204")
            interval = group.get("interval", 300)
            parts.append(f"url={url}")
            parts.append(f"interval={interval}")

            # Add tolerance for url-test
            if surge_type == "url-test":
                tolerance = group.get("tolerance", 100)
                parts.append(f"tolerance={tolerance}")

        # Load balance parameters
        if surge_type == "load-balance":
            strategy = group.get("strategy", "round-robin")
            # Surge uses 'persistent' parameter for sticky sessions
            if strategy == "consistent-hashing":
                parts.append("persistent=true")

        lines.append(", ".join(parts))

    return lines


def generate_surge_conf(
    proxies: list[str],
    proxy_groups: list[str],
    rules: list[str],
    geosite_comments: list[str] | None = None,
    general_settings: dict[str, Any] | None = None,
) -> str:
    """Generate complete Surge .conf content."""
    sections = []

    # [General] section
    general = general_settings or {}
    general_lines = [
        "[General]",
        f"loglevel = {general.get('loglevel', 'notify')}",
        f"dns-server = {general.get('dns-server', 'system')}",
        "skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 100.64.0.0/10, localhost, *.local",
    ]
    sections.append("\n".join(general_lines))

    # [Proxy] section
    proxy_section = ["[Proxy]", "DIRECT = direct", "REJECT = reject"] + proxies
    sections.append("\n".join(proxy_section))

    # [Proxy Group] section
    if proxy_groups:
        group_section = ["[Proxy Group]"] + proxy_groups
        sections.append("\n".join(group_section))

    # [Rule] section
    rule_section = ["[Rule]"]

    # Add GEOSITE comments at the top of rules section if any
    if geosite_comments:
        rule_section.append("")
        rule_section.append("# ====== 以下 GEOSITE 规则需要手动转换为 RULE-SET ======")
        rule_section.extend(geosite_comments)
        rule_section.append("# ====== GEOSITE 规则结束 ======")
        rule_section.append("")

    rule_section.extend(rules)
    sections.append("\n".join(rule_section))

    return "\n\n".join(sections) + "\n"


def main(
    cfw_path: Path = Path(__file__).parent / "cfw_config.yaml",
    surge_path: Path = Path(__file__).parent / "surge_config.conf",
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

    if not data.get("proxies"):
        print(f"❌ 导出 Surge 配置失败，未能识别 proxies，请检查 {filename} 的配置内容。")
        return

    # Convert proxies
    surge_proxies = []
    valid_proxy_names = set()
    skipped_types = set()

    for proxy in data.get("proxies", []):
        proxy_type = proxy.get("type", "")
        converter = CONVERTERS.get(proxy_type)

        if converter:
            result = converter(proxy)
            if result:
                surge_proxies.append(result)
                valid_proxy_names.add(proxy["name"])
        else:
            skipped_types.add(proxy_type)

    if skipped_types:
        print(f"⚠️  跳过不支持的协议类型: {', '.join(sorted(skipped_types))}")

    if not surge_proxies:
        print("❌ 没有找到可转换的 hysteria2 或 anytls 节点")
        return

    # Convert proxy groups
    surge_groups = []
    valid_group_names = set()
    if data.get("proxy-groups"):
        surge_groups = convert_proxy_groups(data["proxy-groups"], valid_proxy_names)
        # Extract group names for rule validation
        for group in data.get("proxy-groups", []):
            if group.get("name"):
                valid_group_names.add(group["name"])

    # Build valid policies set (proxies + groups + built-in)
    valid_policies = valid_proxy_names | valid_group_names | {"DIRECT", "REJECT"}

    # Convert rules
    surge_rules = []
    geosite_comments = []
    rule_warnings = []

    if data.get("rules"):
        surge_rules, geosite_comments, rule_warnings = convert_rules(data["rules"], valid_policies)

        if rule_warnings:
            print("\n⚠️  规则转换警告:")
            for warning in rule_warnings[:10]:  # Show first 10 warnings
                print(f"   - {warning}")
            if len(rule_warnings) > 10:
                print(f"   ... 还有 {len(rule_warnings) - 10} 条警告")
    else:
        # Default rules if none provided
        surge_rules = ["GEOIP,CN,DIRECT", "FINAL,DIRECT"]

    # Generate Surge config
    surge_conf = generate_surge_conf(
        surge_proxies, surge_groups, surge_rules, geosite_comments if geosite_comments else None
    )

    surge_path.write_text(surge_conf, encoding="utf8")

    print(f"✅ 成功转换 {len(surge_proxies)} 个节点")
    if surge_groups:
        print(f"✅ 成功转换 {len(surge_groups)} 个代理组")
    if surge_rules:
        converted_rule_count = len([r for r in surge_rules if not r.startswith("#")])
        print(f"✅ 成功转换 {converted_rule_count} 条规则")
    if geosite_comments:
        print(f"⚠️  {len(geosite_comments)} 条 GEOSITE 规则需要手动转换为 RULE-SET")
    print(f"\n📄 输出文件 --> {surge_path.resolve()}")


if __name__ == "__main__":
    main()
