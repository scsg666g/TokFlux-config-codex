# -*- coding: utf-8 -*-
import subprocess

from .config import CLAUDE_INSTALL_COMMAND_ARGS, INSTALL_COMMAND_ARGS
from .environment import resolve_command


def build_npm_command(args):
    npm_executable = resolve_command("npm")
    if not npm_executable:
        return None

    return [npm_executable, *args]


def build_install_command():
    return build_npm_command(INSTALL_COMMAND_ARGS)


def build_claude_install_command():
    return build_npm_command(CLAUDE_INSTALL_COMMAND_ARGS)


def stream_npm_output(command, on_line):
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


def stream_install_output(on_line):
    return stream_npm_output(build_install_command(), on_line)


def stream_claude_install_output(on_line):
    return stream_npm_output(build_claude_install_command(), on_line)
