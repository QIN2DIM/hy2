"""全局常量配置"""

from pathlib import Path

BASE_DIR = Path("/home/anytls")
DOCKER_COMPOSE_PATH = BASE_DIR / "docker-compose.yaml"
CONFIG_PATH = BASE_DIR / "config.yaml"

LISTEN_PORT = 8443
SERVICE_IMAGE = "metacubex/mihomo:latest"

MIHOMO_ANYTLS_DOCS = "https://wiki.metacubex.one/config/proxies/anytls/#anytls"
