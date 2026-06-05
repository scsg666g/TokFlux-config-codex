# -*- coding: utf-8 -*-
import subprocess

from .config import INSTALL_COMMAND_ARGS
from .environment import resolve_command


def build_install_command():
    npm_executable = resolve_command("npm")
    if not npm_executable:
        return None

    return [npm_executable, *INSTALL_COMMAND_ARGS]


def stream_install_output(on_line):
    command = build_install_command()
    if not command:
        raise FileNotFoundError("找不到 npm，请先安装 Node.js。")

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
