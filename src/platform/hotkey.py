"""全局快捷键模块"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Callable, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


# Windows API 常量
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

# 虚拟键码
VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B
VK_H = 0x48
VK_P = 0x50
VK_Q = 0x51
VK_S = 0x53
VK_T = 0x54
VK_A = 0x41


class GlobalHotkey:
    """全局快捷键管理器"""

    _instance: Optional["GlobalHotkey"] = None
    _hotkey_id = 1000

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.app: DesktopPet | None = None
        self._hotkeys: Dict[int, tuple] = {}  # id -> (modifiers, vk, callback)
        self._is_running = False
        self._original_wndproc = None
        self._hwnd = None

    def register_app(self, app: DesktopPet) -> bool:
        """注册应用程序

        Args:
            app: DesktopPet 实例

        Returns:
            是否成功
        """
        self.app = app

        # 获取窗口句柄
        try:
            self._hwnd = ctypes.windll.user32.GetParent(app.root.winfo_id())
            if not self._hwnd:
                print("获取窗口句柄失败")
                return False
        except Exception as e:
            print(f"获取窗口句柄失败: {e}")
            return False

        # 设置窗口消息处理
        try:
            self._setup_message_handler()
            self._register_default_hotkeys()
            self._is_running = True
            print("全局快捷键已注册")
            return True
        except Exception as e:
            print(f"注册全局快捷键失败: {e}")
            return False

    def _setup_message_handler(self) -> None:
        """设置窗口消息处理器"""
        # 保存原始窗口过程
        GWL_WNDPROC = -4
        WndProcType = ctypes.WINFUNCTYPE(
            wintypes.LPARAM,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        def wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_HOTKEY:
                hotkey_id = wparam
                if hotkey_id in self._hotkeys:
                    _, _, callback = self._hotkeys[hotkey_id]
                    try:
                        callback()
                    except Exception as e:
                        print(f"执行快捷键回调失败: {e}")
                return 0

            # 调用原始窗口过程
            if self._original_wndproc:
                return ctypes.windll.user32.CallWindowProcW(
                    self._original_wndproc, hwnd, msg, wparam, lparam
                )
            return 0

        self._wndproc = WndProcType(wndproc)
        self._original_wndproc = ctypes.windll.user32.SetWindowLongW(
            self._hwnd, GWL_WNDPROC, self._wndproc
        )

    def _register_default_hotkeys(self) -> None:
        """注册默认快捷键"""
        if not self.app:
            return

        # Ctrl+Shift+H - 显示/隐藏
        self.register(
            MOD_CONTROL | MOD_SHIFT,
            VK_H,
            self._toggle_visible,
        )

        # Ctrl+Shift+Q - 退出
        self.register(
            MOD_CONTROL | MOD_SHIFT,
            VK_Q,
            self._quit,
        )

        # Ctrl+Shift+S - 显示快捷菜单
        self.register(
            MOD_CONTROL | MOD_SHIFT,
            VK_S,
            self._show_quick_menu,
        )

        # Ctrl+Shift+A - AI对话
        self.register(
            MOD_CONTROL | MOD_SHIFT,
            VK_A,
            self._open_ai_chat,
        )

    def register(
        self,
        modifiers: int,
        vk: int,
        callback: Callable[[], None],
    ) -> bool:
        """注册快捷键

        Args:
            modifiers: 修饰键（MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN 的组合）
            vk: 虚拟键码
            callback: 回调函数

        Returns:
            是否成功
        """
        if not self._hwnd:
            return False

        hotkey_id = GlobalHotkey._hotkey_id
        GlobalHotkey._hotkey_id += 1

        try:
            result = ctypes.windll.user32.RegisterHotKey(
                self._hwnd,
                hotkey_id,
                modifiers,
                vk,
            )
            if result:
                self._hotkeys[hotkey_id] = (modifiers, vk, callback)
                return True
            else:
                print(f"注册快捷键失败: {modifiers}+{vk}")
                return False
        except Exception as e:
            print(f"注册快捷键失败: {e}")
            return False

    def unregister_all(self) -> None:
        """注销所有快捷键"""
        if not self._hwnd:
            return

        for hotkey_id in list(self._hotkeys.keys()):
            try:
                ctypes.windll.user32.UnregisterHotKey(self._hwnd, hotkey_id)
            except Exception:
                pass

        self._hotkeys.clear()
        self._is_running = False

        # 恢复原始窗口过程
        if self._original_wndproc and self._hwnd:
            try:
                GWL_WNDPROC = -4
                ctypes.windll.user32.SetWindowLongW(
                    self._hwnd, GWL_WNDPROC, self._original_wndproc
                )
            except Exception:
                pass

        print("全局快捷键已注销")

    def _toggle_visible(self) -> None:
        """切换显示/隐藏"""
        if self.app:
            if self.app.root.state() == "withdrawn":
                self.app.root.deiconify()
            else:
                self.app.root.withdraw()

    def _quit(self) -> None:
        """退出程序"""
        if self.app:
            self.app.request_quit()

    def _show_quick_menu(self) -> None:
        """显示快捷菜单"""
        if self.app:
            self.app.quick_menu.show()

    def _open_ai_chat(self) -> None:
        """打开AI对话"""
        if self.app:
            self.app.open_ai_chat_dialog()


# 全局实例
hotkey_manager = GlobalHotkey()
