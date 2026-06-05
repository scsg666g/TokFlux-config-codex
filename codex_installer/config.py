# -*- coding: utf-8 -*-
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

APP_TITLE = "TokFlux配置助手"
WINDOW_SIZE = "1000x700"
WINDOW_MIN_SIZE = (480, 320)
LOGO_PATH = PROJECT_ROOT / "logo.png"

PACKAGE_NAME = "@openai/codex"
REGISTRY_URL = "https://registry.npmmirror.com"

INSTALL_COMMAND_ARGS = [
    "install",
    "-g",
    PACKAGE_NAME,
    f"--registry={REGISTRY_URL}",
]

NODE_DOWNLOAD_URL = "https://nodejs.org/"
NODE_WINGET_PACKAGE_ID = "OpenJS.NodeJS.LTS"
API_BASE_URL = "http://tokenflux.cloud/v1"
API_TEST_TIMEOUT = 15
API_TEST_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/125.0 Safari/537.36"
)
