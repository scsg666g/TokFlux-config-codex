# -*- coding: utf-8 -*-
import subprocess

from .config import NODE_WINGET_PACKAGE_ID
from .environment import resolve_command


def build_node_install_command():
    winget_executable = resolve_command("winget")
    if not winget_executable:
        return None

    return [
        winget_executable,
        "install",
        "--exact",
        "--id",
        NODE_WINGET_PACKAGE_ID,
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--silent",
    ]


def stream_node_install_output(on_line):
    command = build_node_install_command()
    if not command:
        raise FileNotFoundError("找不到 winget，无法自动安装 Node.js。")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    for line in process.stdout or []:
        on_line(line)

    return process.wait()
