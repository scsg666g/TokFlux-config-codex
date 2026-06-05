# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
import sys


PROVIDER_ID = "custom"
PROVIDER_NAME = "custom"
LEGACY_PROVIDER_IDS = ("tokenflux",)
API_KEY_ENV_NAME = "OPENAI_API_KEY"
API_BASE_URL_ENV_NAME = "OPENAI_BASE_URL"


def get_codex_home():
    configured_home = os.environ.get("CODEX_HOME")
    if configured_home:
        return Path(configured_home).expanduser()

    return Path.home() / ".codex"


def get_config_path():
    return get_codex_home() / "config.toml"


def get_auth_path():
    return get_codex_home() / "auth.json"


def read_saved_api_key():
    auth_path = get_auth_path()
    if auth_path.exists():
        try:
            data = json.loads(auth_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}

        api_key = data.get(API_KEY_ENV_NAME, "")
        if isinstance(api_key, str) and api_key.strip():
            return api_key.strip()

    return os.environ.get(API_KEY_ENV_NAME, "").strip()


def write_codex_settings(base_url, api_key, persist_environment=True):
    codex_home = get_codex_home()
    codex_home.mkdir(parents=True, exist_ok=True)

    config_path = get_config_path()
    auth_path = get_auth_path()

    write_config_toml(config_path, base_url)
    write_auth_json(auth_path, api_key)
    write_process_environment(base_url, api_key)

    if persist_environment:
        write_user_environment(base_url, api_key)

    return config_path, auth_path


def write_config_toml(config_path, base_url):
    existing = ""
    if config_path.exists():
        existing = config_path.read_text(encoding="utf-8")

    cleaned = remove_managed_config(existing).rstrip()
    managed_block = build_managed_config_block(base_url)

    next_text = managed_block
    if cleaned:
        next_text = cleaned + "\n\n" + managed_block

    config_path.write_text(next_text + "\n", encoding="utf-8")


def remove_managed_config(text):
    lines = text.splitlines()
    output = []
    current_table = ""
    skip_provider_table = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            current_table = stripped.strip("[]").strip()
            skipped_tables = {
                f"model_providers.{provider_id}"
                for provider_id in (PROVIDER_ID, *LEGACY_PROVIDER_IDS)
            }
            skip_provider_table = current_table in skipped_tables

        if skip_provider_table:
            continue

        if current_table == "" and stripped.startswith("model_"):
            key = stripped.split("=", 1)[0].strip()
            if key in {
                "model_provider",
                "model",
                "model_reasoning_effort",
            }:
                continue

        if current_table == "" and stripped.startswith(("disable_response_storage", "approvals_reviewer")):
            key = stripped.split("=", 1)[0].strip()
            if key in {"disable_response_storage", "approvals_reviewer"}:
                continue

        output.append(line)

    return "\n".join(output)


def build_managed_config_block(base_url):
    return "\n".join(
        [
            f'model_provider = "{PROVIDER_ID}"',
            'model = "gpt-5.5"',
            'model_reasoning_effort = "high"',
            "disable_response_storage = true",
            'approvals_reviewer = "user"',
            "",
            f'[model_providers.{PROVIDER_ID}]',
            f'name = "{PROVIDER_NAME}"',
            'wire_api = "responses"',
            "requires_openai_auth = true",
            f'base_url = {toml_string(base_url)}',
        ]
    )


def write_auth_json(auth_path, api_key):
    data = {}
    if auth_path.exists():
        try:
            data = json.loads(auth_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}

    data["auth_mode"] = "apikey"
    data[API_KEY_ENV_NAME] = api_key

    auth_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def toml_string(value):
    return json.dumps(value, ensure_ascii=False)


def write_process_environment(base_url, api_key):
    os.environ[API_KEY_ENV_NAME] = api_key
    os.environ[API_BASE_URL_ENV_NAME] = base_url


def write_user_environment(base_url, api_key):
    if not sys.platform.startswith("win"):
        return

    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as env_key:
        winreg.SetValueEx(env_key, API_KEY_ENV_NAME, 0, winreg.REG_SZ, api_key)
        winreg.SetValueEx(env_key, API_BASE_URL_ENV_NAME, 0, winreg.REG_SZ, base_url)

    broadcast_environment_change()


def broadcast_environment_change():
    if not sys.platform.startswith("win"):
        return

    import ctypes

    hwnd_broadcast = 0xFFFF
    wm_settingchange = 0x001A
    smto_abortifhung = 0x0002
    result = ctypes.c_ulong()

    ctypes.windll.user32.SendMessageTimeoutW(
        hwnd_broadcast,
        wm_settingchange,
        0,
        "Environment",
        smto_abortifhung,
        5000,
        ctypes.byref(result),
    )
