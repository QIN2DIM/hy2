"""全局常量配置"""

from pathlib import Path

BASE_DIR = Path("/home/hysteria2")
DOCKER_COMPOSE_PATH = BASE_DIR / "docker-compose.yaml"
CONFIG_PATH = BASE_DIR / "config.yaml"

LISTEN_PORT = 4433
SERVICE_IMAGE = "metacubex/mihomo:latest"

MIHOMO_PROXIES_DOCS = "https://wiki.metacubex.one/config/proxies/hysteria2/#hysteria2"

MASQUERADE_WEBSITE = "https://cocodataset.org/"

TOOL_NAME = "Hysteria2"
COMPOSE_SERVICE_NAME = "hysteria2-inbound"
COMPOSE_CONTAINER_PREFIX = f"{COMPOSE_SERVICE_NAME}-"

MIHOMO_LISTEN_TYPE = "hysteria2"
MIHOMO_LISTENER_NAME_PREFIX = f"{MIHOMO_LISTEN_TYPE}-in-"

DEFAULT_CLIENT_CONFIG = {
    "name": "{{DOMAIN}}",
    "type": MIHOMO_LISTEN_TYPE,
    "server": "{{PUBLIC_IP}}",
    "port": "{{PORT}}",
    "password": "{{PASSWORD}}",
    "sni": "{{SNI}}",
    "skip_cert_verify": False,
}
