"""窗口管理（从 src/core/pet_core.py 拆分）"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import tkinter as tk

from src.constants import TRANSPARENT_COLOR, TRANSPARENCY_OPTIONS
from src.platform.system import get_window_handle, set_click_through, set_window_topmost

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class WindowManager:
    """窗口管理器

    说明：窗口对象与关键字段仍保存在 app 上（root/label/hwnd/...），此管理器负责
    初始化与对 Windows API 的调用。
    """

    def __init__(self, app: "DesktopPet") -> None:
        self.app = app

    def init_window(self) -> None:
        """初始化窗口与主标签"""
        root = self.app.root
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.config(bg=TRANSPARENT_COLOR)
        root.attributes("-transparentcolor", TRANSPARENT_COLOR)

        label = tk.Label(root, bg=TRANSPARENT_COLOR, bd=0)
        label.pack()
        self.app.label = label

    def init_handle_and_click_through(self) -> None:
        """初始化句柄并应用鼠标穿透"""
        self.app.root.update_idletasks()
        hwnd = get_window_handle(self.app.root)
        self.app.hwnd = hwnd
        if hwnd:
            set_click_through(hwnd, bool(self.app.click_through))

    def set_transparency(self, index: int) -> None:
        """设置窗口透明度（不负责持久化）"""
        if not (0 <= index < len(TRANSPARENCY_OPTIONS)):
            return
        alpha = TRANSPARENCY_OPTIONS[index]
        self.app.root.attributes("-alpha", alpha)

    def set_click_through(self, enable: bool) -> None:
        """设置鼠标穿透"""
        hwnd: Optional[int] = getattr(self.app, "hwnd", None)
        if hwnd:
            set_click_through(hwnd, enable)

    def ensure_topmost(self) -> None:
        """确保窗口置顶"""
        hwnd: Optional[int] = getattr(self.app, "hwnd", None)
        if hwnd:
            set_window_topmost(hwnd)
