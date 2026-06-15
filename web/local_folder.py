"""本机文件夹选择（Windows / macOS / Linux，需本地运行 Streamlit）。"""

from __future__ import annotations


def pick_local_folder(*, title: str = "选择知识库文件夹") -> str | None:
    """弹出系统文件夹对话框，返回绝对路径；取消或失败时返回 None。"""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    try:
        path = filedialog.askdirectory(title=title, mustexist=True)
    finally:
        root.destroy()
    return path or None
