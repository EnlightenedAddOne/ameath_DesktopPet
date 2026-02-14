"""系统托盘模块"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pystray
from PIL import Image

from src.constants import (
    BEHAVIOR_MODE_ACTIVE,
    BEHAVIOR_MODE_CLINGY,
    BEHAVIOR_MODE_QUIET,
    SCALE_OPTIONS,
    TRANSPARENCY_OPTIONS,
)
from src.utils import resource_path

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class TrayController:
    """系统托盘控制器"""

    def __init__(self, app: DesktopPet):
        self.app = app
        self.icon: pystray.Icon | None = None

    def _create_icon_image(self) -> Image.Image:
        """创建托盘图标"""
        try:
            icon_gif = Image.open(resource_path("assets/gifs/ameath.gif"))
            icon_gif.seek(0)
            icon_image = icon_gif.convert("RGBA")
            return icon_image.resize((64, 64), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"加载托盘图标失败，使用默认图标: {e}")
            return Image.new("RGB", (64, 64), color="pink")

    def _toggle_startup(self, icon: pystray.Icon):
        """切换开机自启"""
        self.app.auto_startup = not self.app.auto_startup
        self.app.set_auto_startup_flag(self.app.auto_startup)
        self.app.update_config(auto_startup=self.app.auto_startup)
        icon.menu = self.build_menu()

    def _toggle_visible(self, icon: pystray.Icon):
        """切换隐藏/显示"""
        if self.app.root.state() == "withdrawn":
            self.app.root.deiconify()
        else:
            self.app.root.withdraw()
        icon.menu = self.build_menu()

    def _toggle_click_through(self, icon: pystray.Icon):
        """切换鼠标穿透"""
        self.app.toggle_click_through()
        icon.menu = self.build_menu()

    def _set_behavior_mode(self, icon: pystray.Icon, mode: str):
        """设置行为模式"""
        self.app.set_behavior_mode(mode)
        icon.menu = self.build_menu()

    def _toggle_pomodoro(self, icon: pystray.Icon):
        """开始/停止番茄钟"""
        self.app.toggle_pomodoro()
        icon.menu = self.build_menu()

    def _reset_pomodoro(self, icon: pystray.Icon):
        """重置番茄钟"""
        self.app.reset_pomodoro()
        icon.menu = self.build_menu()

    def _quit(self, icon: pystray.Icon):
        """退出程序"""
        self.app.request_quit()

    def _on_set_scale(self, icon: pystray.Icon, index: int):
        """设置缩放"""
        self.app.set_scale(index)
        icon.menu = self.build_menu()

    def _on_set_transparency(self, icon: pystray.Icon, index: int):
        """设置透明度"""
        self.app.set_transparency(index)
        icon.menu = self.build_menu()

    def _create_scale_menu(self) -> pystray.Menu:
        """创建设置缩放子菜单"""
        items = []
        for i, scale in enumerate(SCALE_OPTIONS):

            def make_handler(idx):
                def handler(icon, item):
                    self._on_set_scale(icon, idx)

                return handler

            def make_checker(idx):
                def checker(item):
                    return self.app.scale_index == idx

                return checker

            items.append(
                pystray.MenuItem(
                    f"{scale}x",
                    make_handler(i),
                    checked=make_checker(i),
                    radio=True,
                )
            )
        return pystray.Menu(*items)

    def _create_transparency_menu(self) -> pystray.Menu:
        """创建透明度子菜单"""
        items = []
        for i, alpha in enumerate(TRANSPARENCY_OPTIONS):

            def make_handler(idx):
                def handler(icon, item):
                    self._on_set_transparency(icon, idx)

                return handler

            def make_checker(idx):
                def checker(item):
                    return self.app.transparency_index == idx

                return checker

            items.append(
                pystray.MenuItem(
                    f"{int(alpha * 100)}%",
                    make_handler(i),
                    checked=make_checker(i),
                    radio=True,
                )
            )
        return pystray.Menu(*items)

    def _create_behavior_mode_menu(self) -> pystray.Menu:
        """创建行为模式子菜单"""
        return pystray.Menu(
            pystray.MenuItem(
                "安静模式",
                lambda icon, item: self._set_behavior_mode(icon, BEHAVIOR_MODE_QUIET),
                checked=lambda item: self.app.behavior_mode == BEHAVIOR_MODE_QUIET,
                radio=True,
            ),
            pystray.MenuItem(
                "活泼模式",
                lambda icon, item: self._set_behavior_mode(icon, BEHAVIOR_MODE_ACTIVE),
                checked=lambda item: self.app.behavior_mode == BEHAVIOR_MODE_ACTIVE,
                radio=True,
            ),
            pystray.MenuItem(
                "粘人模式",
                lambda icon, item: self._set_behavior_mode(icon, BEHAVIOR_MODE_CLINGY),
                checked=lambda item: self.app.behavior_mode == BEHAVIOR_MODE_CLINGY,
                radio=True,
            ),
        )

    def _create_pomodoro_menu(self) -> pystray.Menu:
        """创建番茄钟子菜单"""
        return pystray.Menu(
            pystray.MenuItem(
                "开始" if not self.app._pomodoro_enabled else "停止",
                self._toggle_pomodoro,
            ),
            pystray.MenuItem(
                "重置",
                self._reset_pomodoro,
                enabled=lambda item: self.app._pomodoro_enabled,
            ),
        )

    def _create_ai_menu(self) -> pystray.Menu:
        """创建AI助手子菜单"""
        # 快捷提问
        quick_questions = [
            ("讲个笑话", "讲个笑话"),
            ("今天星期几", "今天星期几？"),
            ("给我建议", "给我点建议"),
            ("我累了", "我累了"),
        ]

        quick_items = []
        for label, question in quick_questions:

            def make_handler(q):
                def handler(icon, item):
                    self.app.quick_ai_chat(q)

                return handler

            quick_items.append(pystray.MenuItem(label, make_handler(question)))

        return pystray.Menu(
            pystray.MenuItem(
                "开始对话",
                lambda icon, item: self.app.open_ai_chat_dialog(),
            ),
            pystray.MenuItem(
                "快捷提问",
                pystray.Menu(*quick_items),
            ),
            pystray.MenuItem(
                "随机话题",
                lambda icon, item: self.app.quick_ai_chat(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "配置AI",
                lambda icon, item: self.app.show_ai_config_dialog(),
            ),
            pystray.MenuItem(
                "清空对话历史",
                lambda icon, item: self.app.clear_ai_history(),
            ),
        )

    def _create_translate_menu(self) -> pystray.Menu:
        """创建翻译助手子菜单"""
        from src.config import load_config, update_config

        config = load_config()
        translate_enabled = config.get("translate_enabled", False)

        return pystray.Menu(
            pystray.MenuItem(
                "开启/关闭翻译",
                self._toggle_translate,
                checked=lambda item: translate_enabled,
            ),
            pystray.MenuItem(
                "手动翻译",
                lambda icon, item: self.app.translate_window.show(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "使用说明",
                lambda icon, item: self._show_translate_help(),
            ),
        )

    def _toggle_translate(self, icon: pystray.Icon) -> None:
        """切换翻译功能"""
        from src.config import load_config, update_config

        config = load_config()
        current = config.get("translate_enabled", False)
        update_config(translate_enabled=not current)
        icon.menu = self.build_menu()

    def _show_translate_help(self) -> None:
        """显示翻译使用说明"""
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "翻译助手使用说明",
            "1. 选中需要翻译的文字\n"
            "2. 按住 Ctrl 键超过1秒\n"
            "3. 即可弹出翻译窗口\n\n"
            "注意：需要先在AI配置中启用AI功能",
        )
        root.destroy()

    def _create_quick_launch_menu(self) -> pystray.Menu:
        """创建快速启动子菜单"""
        from src.config import load_config, update_config

        config = load_config()
        quick_enabled = config.get("quick_launch_enabled", False)
        exe_path = config.get("quick_launch_exe_path", "")

        # 显示路径（截取文件名）
        if exe_path:
            display_path = os.path.basename(exe_path)
        else:
            display_path = "未设置"

        return pystray.Menu(
            pystray.MenuItem(
                "开启/关闭",
                self._toggle_quick_launch,
                checked=lambda item: quick_enabled,
            ),
            pystray.MenuItem(
                f"程序: {display_path}",
                self._set_quick_launch_path,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "使用说明",
                self._show_quick_launch_help,
            ),
        )

    def _toggle_quick_launch(self, icon: pystray.Icon) -> None:
        """切换快速启动功能"""
        from src.config import load_config, update_config

        config = load_config()
        current = config.get("quick_launch_enabled", False)
        update_config(quick_launch_enabled=not current)
        icon.menu = self.build_menu()

    def _set_quick_launch_path(self, icon: pystray.Icon, item) -> None:
        """设置快速启动的程序路径"""
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        file_path = filedialog.askopenfilename(
            title="选择要启动的程序",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
        )

        root.destroy()

        if file_path:
            from src.config import update_config

            update_config(quick_launch_exe_path=file_path)
            icon.menu = self.build_menu()

    def _show_quick_launch_help(self) -> None:
        """显示快速启动使用说明"""
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "快速启动使用说明",
            "快速启动程序：\n"
            "1. 先在托盘菜单中设置要启动的程序\n"
            "2. 关闭鼠标穿透功能\n"
            "3. 在宠物上快速点击5次（2秒内）\n"
            "4. 即可启动设定的程序\n\n"
            "提示：点击太快可能导致触发失败",
        )
        root.destroy()

    def build_menu(self) -> pystray.Menu:
        """构建托盘菜单"""
        return pystray.Menu(
            pystray.MenuItem(
                "隐藏" if self.app.root.state() == "normal" else "显示",
                self._toggle_visible,
            ),
            pystray.MenuItem(
                "鼠标穿透",
                self._toggle_click_through,
                checked=lambda item: self.app.click_through,
            ),
            pystray.MenuItem(
                "开机自启",
                self._toggle_startup,
                checked=lambda item: self.app.auto_startup,
            ),
            pystray.MenuItem("快速启动", self._create_quick_launch_menu()),
            pystray.MenuItem("AI助手", self._create_ai_menu()),
            pystray.MenuItem("翻译助手", self._create_translate_menu()),
            pystray.MenuItem("行为模式", self._create_behavior_mode_menu()),
            pystray.MenuItem("番茄钟", self._create_pomodoro_menu()),
            pystray.MenuItem("缩放", self._create_scale_menu()),
            pystray.MenuItem("透明度", self._create_transparency_menu()),
            pystray.MenuItem("退出", self._quit),
        )

    def run(self) -> None:
        """启动托盘图标"""
        icon_image = self._create_icon_image()
        self.icon = pystray.Icon("desktop_pet", icon_image, "远航星", self.build_menu())
        self.icon.run_detached()

    def stop(self) -> None:
        """停止托盘图标"""
        if self.icon:
            self.icon.stop()
