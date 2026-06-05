# -*- coding: utf-8 -*-
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from .config import (
    API_BASE_URL,
    APP_TITLE,
    LOGO_PATH,
    NODE_DOWNLOAD_URL,
    WINDOW_MIN_SIZE,
    WINDOW_SIZE,
)
from .api_client import test_openai_connection
from .codex_config import write_codex_settings
from .environment import check_environment
from .environment_installer import build_node_install_command, stream_node_install_output
from .installer import build_install_command, stream_install_output


class CodexInstallerApp:
    def __init__(self, root):
        self.root = root
        self.output_queue = queue.Queue()
        self.worker = None

        self.root.title(APP_TITLE)
        self.set_window_icon()
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(*WINDOW_MIN_SIZE)
        self.root.resizable(True, True)

        self.status_var = tk.StringVar(value="请先进行环境测试")
        self.node_var = tk.StringVar(value="Node.js：未检查")
        self.npm_var = tk.StringVar(value="npm：未检查")
        self.url_var = tk.StringVar(value=API_BASE_URL)
        self.key_var = tk.StringVar()

        self.build_ui()
        self.root.after(100, self.drain_output_queue)

    def set_window_icon(self):
        if not LOGO_PATH.exists():
            return

        try:
            self.logo_image = tk.PhotoImage(file=str(LOGO_PATH))
            self.root.iconphoto(True, self.logo_image)
        except tk.TclError:
            self.logo_image = None

    def build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(main)
        top.pack(fill=tk.X)
        top.columnconfigure(0, minsize=360)
        top.columnconfigure(1, weight=1)

        left_panel = ttk.Frame(top)
        left_panel.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 18))

        input_panel = ttk.Frame(top)
        input_panel.grid(row=0, column=1, sticky=tk.NE, pady=(18, 0))

        title = ttk.Label(left_panel, text=APP_TITLE, font=("Microsoft YaHei UI", 14, "bold"))
        title.pack(anchor=tk.W)

        subtitle = ttk.Label(
            left_panel,
            text="检测 Node.js 和 npm 后，安装 @openai/codex。",
            foreground="#555555",
        )
        subtitle.pack(anchor=tk.W, pady=(4, 12))

        status_box = ttk.LabelFrame(left_panel, text="环境状态", padding=10)
        status_box.pack(anchor=tk.W, fill=tk.X)

        ttk.Label(status_box, textvariable=self.node_var).pack(anchor=tk.W)
        ttk.Label(status_box, textvariable=self.npm_var).pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(status_box, textvariable=self.status_var, foreground="#0f766e").pack(
            anchor=tk.W, pady=(8, 0)
        )

        ttk.Label(input_panel, text="API请求地址:").grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        self.url_entry = ttk.Entry(
            input_panel,
            textvariable=self.url_var,
            width=42,
            state="readonly",
        )
        self.url_entry.grid(row=0, column=1, sticky=tk.EW, pady=(0, 8))

        ttk.Label(input_panel, text="key:").grid(row=1, column=0, sticky=tk.W)
        self.key_entry = ttk.Entry(input_panel, textvariable=self.key_var, width=42, show="*")
        self.key_entry.grid(row=1, column=1, sticky=tk.EW)
        input_panel.columnconfigure(1, weight=1)

        button_row = ttk.Frame(main)
        button_row.pack(fill=tk.X, pady=12)

        self.check_button = ttk.Button(button_row, text="环境测试", command=self.check_environment)
        self.check_button.pack(side=tk.LEFT)

        self.install_button = ttk.Button(
            button_row,
            text="安装 Codex",
            command=self.install_codex,
            state=tk.DISABLED,
        )
        self.install_button.pack(side=tk.LEFT, padx=(8, 0))

        self.clear_button = ttk.Button(button_row, text="清空日志", command=self.clear_log)
        self.clear_button.pack(side=tk.RIGHT)

        self.log = scrolledtext.ScrolledText(
            main,
            height=9,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 9),
        )
        self.log.pack(fill=tk.BOTH, expand=True)

    def set_busy(self, is_busy):
        state = tk.DISABLED if is_busy else tk.NORMAL
        self.check_button.config(state=state)
        self.clear_button.config(state=state)
        if is_busy:
            self.install_button.config(state=tk.DISABLED)

    def append_log(self, text):
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def clear_log(self):
        self.log.config(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.config(state=tk.DISABLED)

    def drain_output_queue(self):
        try:
            while True:
                kind, payload = self.output_queue.get_nowait()
                if kind == "log":
                    self.append_log(payload)
                elif kind == "status":
                    self.status_var.set(payload)
                elif kind == "node":
                    self.node_var.set(payload)
                elif kind == "npm":
                    self.npm_var.set(payload)
                elif kind == "install_ready":
                    self.install_button.config(state=tk.NORMAL if payload else tk.DISABLED)
                elif kind == "busy":
                    self.set_busy(payload)
                elif kind == "message":
                    title, message, level = payload
                    if level == "error":
                        messagebox.showerror(title, message)
                    else:
                        messagebox.showinfo(title, message)
        except queue.Empty:
            pass

        self.root.after(100, self.drain_output_queue)

    def run_worker(self, target):
        if self.worker and self.worker.is_alive():
            return

        self.worker = threading.Thread(target=target, daemon=True)
        self.worker.start()

    def check_environment(self):
        self.clear_log()
        self.output_queue.put(("busy", True))
        self.output_queue.put(("status", "正在测试 API 连接..."))
        self.output_queue.put(("install_ready", False))
        base_url = self.url_var.get().strip()
        api_key = self.key_var.get().strip()

        def worker():
            self.output_queue.put(("log", "正在测试 API 连接...\n"))
            api_result = test_openai_connection(base_url, api_key)

            self.output_queue.put(("log", api_result.message + "\n"))
            if api_result.detail:
                self.output_queue.put(("log", f"{api_result.detail}\n"))

            if not api_result.ok:
                self.output_queue.put(("status", "API 连接失败"))
                self.output_queue.put(("busy", False))
                return

            self.output_queue.put(("status", "API 连接成功，正在检查环境..."))
            self.output_queue.put(("log", "\n"))
            self.output_queue.put(("log", "正在检查 Node.js 和 npm...\n\n"))
            env = check_environment()

            self.report_tool("node", env.node)
            self.report_tool("npm", env.npm)

            if env.ready:
                self.output_queue.put(("status", "环境正常，可以安装 Codex ---------"))
                self.output_queue.put(("log", "环境正常，可以安装 Codex ---------\n"))
                self.output_queue.put(("install_ready", True))
            else:
                self.install_missing_environment()

            self.output_queue.put(("busy", False))

        self.run_worker(worker)

    def report_tool(self, queue_key, tool):
        if tool.ok:
            self.output_queue.put((queue_key, f"{tool.name}：{tool.version}"))
            self.output_queue.put(("log", f"[OK] {tool.name}: {tool.version}\n路径: {tool.path}\n\n"))
            return

        self.output_queue.put((queue_key, f"{tool.name}：未检测到"))
        self.output_queue.put(("log", f"[缺失] 没有检测到 {tool.name}\n\n"))

    def install_missing_environment(self):
        command = build_node_install_command()
        if not command:
            self.output_queue.put(("status", "无法自动安装 Node.js"))
            self.output_queue.put(
                (
                    "log",
                    "检测到环境缺失，但找不到 winget，无法自动安装 Node.js。\n"
                    f"请手动安装 Node.js：{NODE_DOWNLOAD_URL}\n",
                )
            )
            return

        self.output_queue.put(("status", "检测到环境缺失，正在安装 Node.js..."))
        self.output_queue.put(("log", "检测到环境缺失，正在安装 Node.js LTS...\n"))
        self.output_queue.put(("log", " ".join(command) + "\n\n"))

        try:
            return_code = stream_node_install_output(
                lambda line: self.output_queue.put(("log", line))
            )
        except FileNotFoundError as exc:
            self.output_queue.put(("status", "环境安装失败"))
            self.output_queue.put(("log", f"{exc}\n"))
            return

        if return_code != 0:
            self.output_queue.put(("status", "环境安装失败"))
            self.output_queue.put(("log", f"\nNode.js 安装失败，winget 退出码：{return_code}\n"))
            return

        self.output_queue.put(("log", "\nNode.js 安装完成，正在重新检查环境...\n\n"))
        env = check_environment()
        self.report_tool("node", env.node)
        self.report_tool("npm", env.npm)

        if env.ready:
            self.output_queue.put(("status", "环境正常，可以安装 Codex ---------"))
            self.output_queue.put(("log", "环境正常，可以安装 Codex ---------\n"))
            self.output_queue.put(("install_ready", True))
        else:
            self.output_queue.put(("status", "环境安装完成，但当前程序还未识别到 Node.js/npm"))
            self.output_queue.put(
                (
                    "log",
                    "Node.js 可能已经安装完成，但当前程序还没有刷新到新的 PATH。\n"
                    "请重新打开本程序后再次点击环境测试。\n",
                )
            )

    def install_codex(self):
        base_url = self.url_var.get().strip()
        api_key = self.key_var.get().strip()
        if not api_key:
            messagebox.showerror("缺少 key", "请先填写 key。")
            return

        if not messagebox.askyesno("确认安装", "现在开始全局安装 @openai/codex 吗？"):
            return

        self.output_queue.put(("busy", True))
        self.output_queue.put(("status", "正在安装 Codex..."))

        def worker():
            command = build_install_command()
            if not command:
                self.fail_install("找不到 npm，请先安装 Node.js。")
                return

            self.output_queue.put(("log", "\n准备执行安装命令：\n"))
            self.output_queue.put(("log", " ".join(command) + "\n\n"))

            try:
                return_code = stream_install_output(
                    lambda line: self.output_queue.put(("log", line))
                )
            except FileNotFoundError as exc:
                self.fail_install(str(exc))
                return

            self.output_queue.put(("busy", False))

            if return_code == 0:
                try:
                    config_path, auth_path = write_codex_settings(base_url, api_key)
                except OSError as exc:
                    self.output_queue.put(("status", "Codex 已安装，但配置写入失败"))
                    self.output_queue.put(("log", f"\nCodex 已安装，但配置写入失败：{exc}\n"))
                    self.output_queue.put(
                        ("message", ("配置失败", f"Codex 已安装，但配置写入失败：{exc}", "error"))
                    )
                    return

                self.output_queue.put(("status", "安装完成"))
                self.output_queue.put(("log", "\nCodex 安装完成，配置已写入。\n"))
                self.output_queue.put(("log", f"配置文件：{config_path}\n"))
                self.output_queue.put(("log", f"认证文件：{auth_path}\n"))
                self.output_queue.put(("log", "用户环境变量已更新：OPENAI_API_KEY / OPENAI_BASE_URL\n"))
                self.output_queue.put(("log", "可以在终端运行：codex --version\n"))
                self.output_queue.put(("message", ("安装完成", "Codex 已安装完成。", "info")))
            else:
                self.output_queue.put(("status", "安装失败"))
                self.output_queue.put(("install_ready", True))
                self.output_queue.put(("log", f"\n安装失败，npm 退出码：{return_code}\n"))
                self.output_queue.put(
                    ("message", ("安装失败", f"npm 安装失败，退出码：{return_code}", "error"))
                )

        self.run_worker(worker)

    def fail_install(self, message):
        self.output_queue.put(("busy", False))
        self.output_queue.put(("install_ready", False))
        self.output_queue.put(("status", "安装失败"))
        self.output_queue.put(("message", ("安装失败", message, "error")))


def main():
    root = tk.Tk()
    CodexInstallerApp(root)
    root.mainloop()
