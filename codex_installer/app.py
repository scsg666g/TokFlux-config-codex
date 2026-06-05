# -*- coding: utf-8 -*-
import math
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from PIL import Image, ImageOps, ImageTk

from .config import (
    API_BASE_URL,
    APP_TITLE,
    LOGO_PATH,
    NODE_DOWNLOAD_URL,
    WINDOW_MIN_SIZE,
    WINDOW_SIZE,
)
from .api_client import test_openai_connection
from .codex_config import read_saved_api_key, write_codex_settings
from .environment import check_environment
from .environment_installer import build_node_install_command, stream_node_install_output
from .installer import build_install_command, stream_install_output


class CodexInstallerApp:
    def __init__(self, root):
        self.root = root
        self.output_queue = queue.Queue()
        self.worker = None

        self.root.withdraw()
        self.root.title(APP_TITLE)
        self.set_window_icon()
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(*WINDOW_MIN_SIZE)
        self.root.resizable(True, True)

        self.status_var = tk.StringVar(value="请先进行环境测试")
        self.node_var = tk.StringVar(value="Node.js：未检查")
        self.npm_var = tk.StringVar(value="npm：未检查")
        self.url_var = tk.StringVar(value=API_BASE_URL)
        self.key_var = tk.StringVar(value=read_saved_api_key())
        self.key_display_var = tk.StringVar(value=self.mask_api_key(self.key_var.get()))

        self.build_ui()
        self.build_context_menu()
        self.show_startup_splash()
        self.root.after(100, self.drain_output_queue)

    def set_window_icon(self):
        if not LOGO_PATH.exists():
            return

        try:
            self.logo_image = tk.PhotoImage(file=str(LOGO_PATH))
            self.root.iconphoto(True, self.logo_image)
        except tk.TclError:
            self.logo_image = None

    def show_startup_splash(self):
        if not LOGO_PATH.exists():
            self.root.deiconify()
            return

        try:
            image = Image.open(LOGO_PATH).convert("RGBA")
        except OSError:
            self.root.deiconify()
            return

        image.thumbnail((112, 112), Image.LANCZOS)
        self.splash_original_image = image
        self.splash_window = tk.Toplevel(self.root)
        self.splash_window.overrideredirect(True)
        transparent_color = "#00ff01"
        self.splash_window.configure(bg=transparent_color)
        self.splash_window.attributes("-topmost", True)
        try:
            self.splash_window.attributes("-transparentcolor", transparent_color)
        except tk.TclError:
            pass

        splash_size = 190
        self.splash_canvas = tk.Canvas(
            self.splash_window,
            width=splash_size,
            height=splash_size,
            bg=transparent_color,
            highlightthickness=0,
            borderwidth=0,
        )
        self.splash_canvas.pack()
        text_x = splash_size // 2
        text_y = 146
        text_font = ("Microsoft YaHei UI", 11, "bold")
        for offset_x, offset_y in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            self.splash_canvas.create_text(
                text_x + offset_x,
                text_y + offset_y,
                text=APP_TITLE,
                fill="#000000",
                font=text_font,
            )
        self.splash_canvas.create_text(
            text_x,
            text_y,
            text=APP_TITLE,
            fill="#ffffff",
            font=text_font,
        )

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - splash_size) // 2
        y = (screen_height - splash_size) // 2
        self.splash_window.geometry(f"{splash_size}x{splash_size}+{x}+{y}")

        self.animate_startup_logo(frame=0, total_frames=52)

    def animate_startup_logo(self, frame, total_frames):
        if not getattr(self, "splash_window", None) or not self.splash_window.winfo_exists():
            return

        if frame >= total_frames:
            self.finish_startup_splash()
            return

        progress = frame / 13
        turn = math.cos(progress * math.pi)
        width_scale = max(0.18, abs(turn))
        base_width, base_height = self.splash_original_image.size
        frame_width = max(2, int(base_width * width_scale))

        image = self.splash_original_image
        if turn < 0:
            image = ImageOps.mirror(image)

        turned = image.resize((frame_width, base_height), Image.LANCZOS)
        self.splash_photo = ImageTk.PhotoImage(turned)

        self.splash_canvas.delete("logo")
        self.splash_canvas.create_image(95, 82, image=self.splash_photo, tags="logo")
        self.splash_window.after(35, self.animate_startup_logo, frame + 1, total_frames)

    def finish_startup_splash(self):
        if getattr(self, "splash_window", None) and self.splash_window.winfo_exists():
            self.splash_window.destroy()

        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def mask_api_key(self, api_key):
        if not api_key:
            return ""

        return "*" * 28

    def build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(main)
        top.pack(fill=tk.X)
        top.columnconfigure(0, minsize=360)
        top.columnconfigure(1, weight=1)

        left_panel = ttk.Frame(top)
        left_panel.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 18))

        input_panel = ttk.Frame(top, padding=(0, 20, 0, 0))
        input_panel.grid(row=0, column=1, sticky=tk.NE)

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

        form_label_font = ("Microsoft YaHei UI", 10)
        form_entry_font = ("Microsoft YaHei UI", 10)

        ttk.Label(input_panel, text="API 请求地址：", font=form_label_font).grid(
            row=0,
            column=0,
            sticky=tk.E,
            padx=(0, 8),
            pady=(0, 12),
        )
        self.url_entry = ttk.Entry(
            input_panel,
            textvariable=self.url_var,
            width=42,
            state="readonly",
            font=form_entry_font,
        )
        self.url_entry.grid(
            row=0,
            column=1,
            columnspan=2,
            sticky=tk.EW,
            pady=(0, 12),
            ipady=2,
        )

        ttk.Label(input_panel, text="API Key：", font=form_label_font).grid(
            row=1,
            column=0,
            sticky=tk.E,
            padx=(0, 8),
        )
        self.key_entry = ttk.Entry(
            input_panel,
            textvariable=self.key_display_var,
            width=42,
            state="readonly",
            font=form_entry_font,
        )
        self.key_entry.grid(row=1, column=1, sticky=tk.EW, ipady=2)
        self.save_config_button = ttk.Button(
            input_panel,
            text="修改 API Key",
            command=self.show_api_key_dialog,
        )
        self.save_config_button.grid(row=1, column=2, sticky=tk.E, padx=(8, 0))
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

    def build_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=False)
        self.context_menu.add_command(label="刷新", command=self.refresh_app)
        self.root.bind_all("<Button-3>", self.show_context_menu, add="+")

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def refresh_app(self):
        if self.worker and self.worker.is_alive():
            self.status_var.set("任务进行中，请稍后刷新")
            return

        self.key_var.set(read_saved_api_key())
        self.key_display_var.set(self.mask_api_key(self.key_var.get()))
        self.check_environment()

    def set_busy(self, is_busy):
        state = tk.DISABLED if is_busy else tk.NORMAL
        self.check_button.config(state=state)
        self.clear_button.config(state=state)
        self.save_config_button.config(state=state)
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

    def show_api_key_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("修改 API Key")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        content = ttk.Frame(dialog, padding=16)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            content,
            text="请输入新的 API Key：",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor=tk.W)

        new_key_var = tk.StringVar(value=self.key_var.get())
        key_entry = ttk.Entry(
            content,
            textvariable=new_key_var,
            width=46,
            show="*",
            font=("Microsoft YaHei UI", 10),
        )
        key_entry.pack(fill=tk.X, pady=(8, 14), ipady=2)

        button_row = ttk.Frame(content)
        button_row.pack(fill=tk.X)

        def on_save():
            api_key = new_key_var.get().strip()
            if self.save_codex_config(api_key):
                dialog.destroy()

        ttk.Button(button_row, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_row, text="保存", command=on_save).pack(side=tk.RIGHT, padx=(0, 8))

        dialog.bind("<Return>", lambda _event: on_save())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        key_entry.focus_set()

        self.root.update_idletasks()
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def save_codex_config(self, api_key):
        base_url = self.url_var.get().strip()
        if not api_key:
            messagebox.showerror("缺少 key", "请先填写新的 API Key。")
            return False

        try:
            config_path, auth_path = write_codex_settings(base_url, api_key)
        except OSError as exc:
            messagebox.showerror("保存失败", f"配置写入失败：{exc}")
            self.status_var.set("配置写入失败")
            self.append_log(f"\n配置写入失败：{exc}\n")
            return False

        self.key_var.set(api_key)
        self.key_display_var.set(self.mask_api_key(api_key))
        self.status_var.set("配置已更新")
        self.append_log("\nCodex 配置已更新。\n")
        self.append_log(f"配置文件：{config_path}\n")
        self.append_log(f"认证文件：{auth_path}\n")
        self.append_log("用户环境变量已更新：OPENAI_API_KEY / OPENAI_BASE_URL\n")
        self.append_log("如果旧终端仍使用旧 key，请重新打开终端。\n")
        messagebox.showinfo("保存完成", "新的 API Key 已保存。")
        return True

    def fail_install(self, message):
        self.output_queue.put(("busy", False))
        self.output_queue.put(("install_ready", False))
        self.output_queue.put(("status", "安装失败"))
        self.output_queue.put(("message", ("安装失败", message, "error")))


def main():
    root = tk.Tk()
    CodexInstallerApp(root)
    root.mainloop()
