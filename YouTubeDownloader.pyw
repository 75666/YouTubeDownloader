#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import queue
import socket
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, DND_TEXT, TkinterDnD

try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None


DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
DEV_NODE = r"C:\Users\PS061\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
DEV_FFMPEG = r"C:\Users\PS061\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
DEV_ARIA2 = r"C:\Users\PS061\Documents\Codex\2026-07-31\ni-h\_tools\aria2\aria2-1.37.0-win-64bit-build1\aria2c.exe"
COMMON_PROXY_PORTS = [7890, 7897, 10809, 10808, 1080, 8888, 2080, 33210]


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def first_existing(*paths):
    for path in paths:
        if path and os.path.isfile(path):
            return path
    return paths[0] if paths else None


APP_DIR = app_dir()
NODE = first_existing(os.path.join(APP_DIR, "node.exe"), DEV_NODE)
FFMPEG = first_existing(os.path.join(APP_DIR, "ffmpeg.exe"), DEV_FFMPEG)
ARIA2 = first_existing(os.path.join(APP_DIR, "aria2c.exe"), DEV_ARIA2)


def normalize_url(text):
    import re
    text = (text or "").strip()
    if text.startswith("{"):
        text = text[1:]
    if text.endswith("}"):
        text = text[:-1]
    match = re.search(r"https?://[^\s<>\"'{}]+", text)
    return match.group(0) if match else text


def normalize_proxy(raw):
    value = (raw or "").strip()
    if not value:
        return ""
    if "://" not in value:
        if value.isdigit():
            return f"http://127.0.0.1:{value}"
        return f"http://{value}"
    return value


def detect_local_proxy():
    for port in COMMON_PROXY_PORTS:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return f"http://127.0.0.1:{port}"
        except OSError:
            continue
    return ""


class QueueLogger:
    def __init__(self, ui_queue):
        self.ui_queue = ui_queue

    def debug(self, msg):
        pass

    def info(self, msg):
        self.ui_queue.put(("log", str(msg)))

    def warning(self, msg):
        self.ui_queue.put(("log", f"警告: {msg}"))

    def error(self, msg):
        self.ui_queue.put(("log", f"错误: {msg}"))


class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.ui_queue = queue.Queue()
        self.worker = None

        self.root.title("YouTube 下载器")
        self.root.geometry("600x440")
        self.root.minsize(560, 420)

        self._build_ui()
        self.root.after(100, self._poll_queue)

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=12, pady=(12, 6))
        tk.Label(top, text="YouTube 下载器", font=("Microsoft YaHei UI", 15, "bold")).pack(side=tk.LEFT)
        tk.Label(top, text="绿色版，解压后直接使用", fg="#666666").pack(side=tk.RIGHT)

        drop = tk.Frame(self.root, bg="#eaf1fb", bd=2, relief=tk.GROOVE, height=72)
        drop.pack(fill=tk.X, padx=12, pady=(0, 8))
        drop.pack_propagate(False)
        tk.Label(
            drop,
            text="把 YouTube 链接拖到这里，会自动开始下载",
            bg="#eaf1fb",
            fg="#1f3a5f",
            font=("Microsoft YaHei UI", 11),
        ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        drop.drop_target_register(DND_TEXT, DND_FILES)
        drop.dnd_bind("<<Drop>>", self._on_drop)

        row_url = tk.Frame(self.root)
        row_url.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(row_url, text="链接").pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        entry = tk.Entry(row_url, textvariable=self.url_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        entry.bind("<Return>", lambda _event: self._start_download())

        row_out = tk.Frame(self.root)
        row_out.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(row_out, text="保存到").pack(side=tk.LEFT)
        self.out_var = tk.StringVar(value=DESKTOP)
        tk.Entry(row_out, textvariable=self.out_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(row_out, text="选择", width=8, command=self._choose_output).pack(side=tk.LEFT)

        opt_row = tk.Frame(self.root)
        opt_row.pack(fill=tk.X, padx=12, pady=4)
        self.cookie_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opt_row,
            text="使用 Firefox 登录（会员视频）",
            variable=self.cookie_var,
        ).pack(side=tk.LEFT)
        self.proxy_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_row, text="代理", variable=self.proxy_var).pack(side=tk.LEFT, padx=(12, 2))
        self.proxy_entry = tk.Entry(opt_row, width=30)
        self.proxy_entry.insert(0, "")
        self.proxy_entry.pack(side=tk.LEFT)
        tk.Label(opt_row, text="留空自动检测", fg="#888888").pack(side=tk.LEFT, padx=(6, 0))

        btn_row = tk.Frame(self.root)
        btn_row.pack(fill=tk.X, padx=12, pady=6)
        self.start_btn = ttk.Button(btn_row, text="开始下载", command=self._start_download)
        self.start_btn.pack(side=tk.LEFT)
        ttk.Button(btn_row, text="打开下载文件夹", command=self._open_output).pack(side=tk.LEFT, padx=8)

        self.progress = ttk.Progressbar(self.root, maximum=100)
        self.progress.pack(fill=tk.X, padx=12, pady=(6, 2))

        self.status_var = tk.StringVar(value="等待链接")
        tk.Label(self.root, textvariable=self.status_var, anchor=tk.W).pack(fill=tk.X, padx=14)

        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 10))
        self.log_text = tk.Text(
            log_frame,
            height=7,
            state="disabled",
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 9),
        )
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _choose_output(self):
        path = filedialog.askdirectory(initialdir=self.out_var.get() or DESKTOP, title="选择保存文件夹")
        if path:
            self.out_var.set(path)

    def _open_output(self):
        path = self.out_var.get().strip() or DESKTOP
        if os.path.isdir(path):
            os.startfile(path)

    def _on_drop(self, event):
        url = normalize_url(event.data)
        if not url:
            return
        self.url_var.set(url)
        self._log(f"收到链接：{url}")
        self.root.after(250, self._start_download)

    def _log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _start_download(self):
        if self.worker is not None and self.worker.is_alive():
            return
        if YoutubeDL is None:
            messagebox.showerror("缺少组件", "yt-dlp 未正确打包，请重新下载绿色版。")
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("缺少链接", "请拖入或粘贴 YouTube 链接。")
            return
        output_dir = self.out_var.get().strip() or DESKTOP
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as exc:
                messagebox.showerror("无法创建目录", str(exc))
                return

        self.progress["value"] = 0
        self.status_var.set("正在启动下载...")
        self.start_btn.configure(state="disabled")
        self._log(f"开始下载：{url}")
        proxy = ""
        if self.proxy_var.get():
            proxy = normalize_proxy(self.proxy_entry.get())
            if not proxy:
                proxy = detect_local_proxy()
                if proxy:
                    self._log(f"自动检测到代理：{proxy}")
                else:
                    self._log("未检测到本地代理，将尝试直连")
        self.worker = threading.Thread(
            target=self._run_download,
            args=(
                url,
                output_dir,
                self.cookie_var.get(),
                proxy,
            ),
            daemon=True,
        )
        self.worker.start()

    def _run_download(self, url, output_dir, use_cookies, proxy):
        try:
            opts = {
                "noplaylist": True,
                "format": "bestvideo*+bestaudio/best",
                "outtmpl": os.path.join(output_dir, "%(title)s [%(id)s].%(ext)s"),
                "merge_output_format": "mkv",
                "ffmpeg_location": FFMPEG,
                "retries": 30,
                "fragment_retries": 30,
                "socket_timeout": 30,
                "continuedl": True,
                "concurrent_fragment_downloads": 4,
                "windowsfilenames": True,
                "quiet": True,
                "no_warnings": False,
                "noprogress": True,
                "progress_hooks": [self._progress_hook],
                "logger": QueueLogger(self.ui_queue),
                "remote_components": ["ejs:github"],
            }
            if NODE:
                opts["js_runtimes"] = {"node": {"path": NODE}}
            if use_cookies:
                opts["cookiesfrombrowser"] = ("firefox", None, None, None)
            if proxy:
                opts["proxy"] = proxy
                if ARIA2:
                    opts["external_downloader"] = ARIA2
                    opts["external_downloader_args"] = {
                        "aria2c": [
                            "-x",
                            "8",
                            "-s",
                            "8",
                            "-k",
                            "4M",
                            "--file-allocation=none",
                            "--allow-overwrite=false",
                            "--auto-file-renaming=false",
                            "--summary-interval=60",
                            "--console-log-level=warn",
                            f"--all-proxy={proxy}",
                        ]
                    }
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.ui_queue.put(("done", True, "下载完成"))
        except Exception as exc:
            self.ui_queue.put(("done", False, f"下载失败：{exc}"))

    def _progress_hook(self, data):
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            percent = (downloaded / total * 100) if total else 0
            speed = data.get("_speed_str", "") or ""
            eta = data.get("_eta_str", "") or ""
            text = f"下载 {percent:.1f}% {speed} {eta}".strip()
            self.ui_queue.put(("progress", min(100.0, percent), text))
        elif data.get("status") == "finished":
            self.ui_queue.put(("progress", 100, "下载完成，正在合并..."))

    def _poll_queue(self):
        try:
            while True:
                item = self.ui_queue.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, percent, text = item
                    self.progress["value"] = percent
                    self.status_var.set(text)
                elif kind == "log":
                    self._log(item[1])
                elif kind == "done":
                    _, ok, text = item
                    self.start_btn.configure(state="normal")
                    self.status_var.set(text)
                    self._log(text)
                    if ok:
                        messagebox.showinfo("完成", "下载完成，文件已保存。")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)


def main():
    root = TkinterDnD.Tk()
    YouTubeDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
