"""版本检查模块"""

import re
import tkinter as tk
import urllib.request
import webbrowser
from typing import Optional

from src.constants import GITEE_RELEASES_URL
from src.utils import resource_path, version_greater_than


def check_new_version() -> Optional[str]:
    """检查 Gitee 是否有新版本

    Returns:
        新版本号或 None
    """
    try:
        req = urllib.request.Request(
            GITEE_RELEASES_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")

        # 提取版本标签
        pattern = r'href="/lzy-buaa-jdi/ameath/releases/tag/(v[^"]+)"'
        matches = re.findall(pattern, html)
        if matches:
            return matches[0]
    except Exception as e:
        print(f"检查版本失败: {e}")

    return None


def show_update_dialog(
    parent: tk.Tk, current_version: str, latest_version: str
) -> None:
    """显示版本更新通知弹窗

    Args:
        parent: 父窗口
        current_version: 当前版本
        latest_version: 最新版本
    """
    dialog = tk.Toplevel(parent)
    dialog.title("发现新版本")
    width, height = 520, 300
    dialog.geometry(f"{width}x{height}")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.transient(parent)

    try:
        from PIL import Image as PILImage
        from PIL import ImageTk

        icon_image = PILImage.open(resource_path("assets/gifs/ameath.gif"))
        icon_image = icon_image.resize((64, 64), PILImage.Resampling.LANCZOS)
        app_icon = ImageTk.PhotoImage(icon_image)
        dialog.iconphoto(True, app_icon)
    except Exception as e:
        print(f"设置更新窗口图标失败: {e}")

    # 居中显示
    dialog.update_idletasks()
    screen_w = dialog.winfo_screenwidth()
    screen_h = dialog.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    dialog.geometry(f"+{x}+{y}")

    # 内容
    tk.Label(
        dialog,
        text="发现新版本！",
        font=("Microsoft YaHei UI", 16, "bold"),
    ).pack(pady=(25, 15))

    tk.Label(
        dialog,
        text=f"当前版本: {current_version}",
        font=("Microsoft YaHei UI", 12),
    ).pack()

    tk.Label(
        dialog,
        text=f"最新版本: {latest_version}",
        font=("Microsoft YaHei UI", 12),
    ).pack(pady=(5, 20))

    # 按钮
    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=(0, 25))

    def on_download():
        webbrowser.open(GITEE_RELEASES_URL)
        dialog.destroy()

    tk.Button(
        btn_frame,
        text="前往发布",
        command=on_download,
        width=12,
        font=("Microsoft YaHei UI", 11),
        bg="#1890FF",
        fg="white",
    ).pack(side=tk.LEFT, padx=15)

    tk.Button(
        btn_frame,
        text="取消",
        command=dialog.destroy,
        width=12,
        font=("Microsoft YaHei UI", 11),
    ).pack(side=tk.LEFT, padx=15)

    dialog.focus_force()


def check_version_and_notify(root: tk.Tk, current_version: str) -> None:
    """检查版本并通知（后台线程调用）

    Args:
        root: 根窗口
        current_version: 当前版本号
    """
    latest = check_new_version()
    if latest and version_greater_than(latest, current_version):
        # 在主线程显示弹窗
        root.after(0, lambda: show_update_dialog(root, current_version, latest))
