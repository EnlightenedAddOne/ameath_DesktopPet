"""系统托盘模块"""

from __future__ import annotations

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
