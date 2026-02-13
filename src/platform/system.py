"""系统功能模块 - Windows API 和 DPI 处理"""

import ctypes
from typing import Optional

from src.constants import (
    GWL_EXSTYLE,
    HWND_TOPMOST,
    SWP_NOACTIVATE,
    SWP_NOMOVE,
    SWP_NOSIZE,
    SWP_SHOWWINDOW,
    WS_EX_LAYERED,
    WS_EX_TRANSPARENT,
)


def enable_dpi_awareness() -> None:
    """启用 Windows DPI 感知（解决高DPI屏幕模糊问题）"""
    try:
        # Windows 8.1+
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError, ctypes.WinError):
        try:
            # Windows Vista+
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError, ctypes.WinError):
            pass


def set_window_topmost(hwnd: int) -> bool:
    """设置窗口置顶

    Args:
        hwnd: 窗口句柄

    Returns:
        是否成功
    """
    try:
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
        return True
    except (OSError, ctypes.WinError) as e:
        print(f"设置窗口置顶失败: {e}")
        return False


def set_click_through(hwnd: int, enable: bool) -> bool:
    """设置鼠标穿透

    Args:
        hwnd: 窗口句柄
        enable: 是否启用

    Returns:
        是否成功
    """
    try:
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enable:
            new_style = style | WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            new_style = style & ~WS_EX_TRANSPARENT

        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        return True
    except (OSError, ctypes.WinError) as e:
        print(f"设置鼠标穿透失败: {e}")
        return False


def get_window_handle(widget) -> Optional[int]:
    """获取 tkinter 窗口的 Windows 句柄

    Args:
        widget: tkinter 部件

    Returns:
        窗口句柄或 None
    """
    try:
        return ctypes.windll.user32.GetParent(widget.winfo_id())
    except (OSError, ctypes.WinError):
        return None
