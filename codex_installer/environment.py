# -*- coding: utf-8 -*-
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class ToolStatus:
    name: str
    ok: bool
    path: str | None = None
    version: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class EnvironmentStatus:
    node: ToolStatus
    npm: ToolStatus

    @property
    def ready(self):
        return self.node.ok and self.npm.ok


def resolve_command(command_name):
    path = shutil.which(command_name)
    if path:
        return path

    if sys.platform.startswith("win") and not command_name.endswith(".cmd"):
        path = shutil.which(f"{command_name}.cmd")
        if path:
            return path

    if sys.platform.startswith("win"):
        return resolve_windows_common_command(command_name)

    return None


def resolve_windows_common_command(command_name):
    executable_names = [command_name]
    if not command_name.endswith(".exe"):
        executable_names.append(f"{command_name}.exe")
    if not command_name.endswith(".cmd"):
        executable_names.append(f"{command_name}.cmd")

    node_dirs = []
    for env_name, parts in [
        ("ProgramFiles", ("nodejs",)),
        ("ProgramFiles(x86)", ("nodejs",)),
        ("LOCALAPPDATA", ("Programs", "nodejs")),
    ]:
        base_path = os.environ.get(env_name)
        if base_path:
            node_dirs.append(Path(base_path, *parts))

    for node_dir in node_dirs:
        for executable_name in executable_names:
            candidate = node_dir / executable_name
            if candidate.exists():
                return str(candidate)

    return None


def run_and_capture(command):
    try:
        completed = subprocess.run(
            command,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return False, None, "未找到命令"
    except subprocess.CalledProcessError as exc:
        output = (exc.stdout or exc.stderr or "").strip()
        message = output or f"命令执行失败，退出码：{exc.returncode}"
        return False, None, message

    return True, completed.stdout.strip(), None


def check_tool(command_name, display_name=None):
    executable = resolve_command(command_name)
    name = display_name or command_name

    if not executable:
        return ToolStatus(name=name, ok=False, error="未检测到")

    ok, version, error = run_and_capture([executable, "--version"])
    return ToolStatus(
        name=name,
        ok=ok,
        path=executable,
        version=version,
        error=error,
    )


def check_environment():
    return EnvironmentStatus(
        node=check_tool("node", "Node.js"),
        npm=check_tool("npm", "npm"),
    )
