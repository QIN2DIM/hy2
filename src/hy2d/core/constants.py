"""全局常量配置"""

from pathlib import Path

BASE_DIR = Path("/home/hysteria2")
DOCKER_COMPOSE_PATH = BASE_DIR / "docker-compose.yaml"
CONFIG_PATH = BASE_DIR / "config.yaml"

LISTEN_PORT = 4433
SERVICE_IMAGE = "metacubex/mihomo:latest"

MIHOMO_PROXIES_DOCS = "https://wiki.metacubex.one/config/proxies/hysteria2/#hysteria2"
