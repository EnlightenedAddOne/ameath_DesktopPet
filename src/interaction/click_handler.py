"""点击交互（从 src/core/pet_core.py 拆分）"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import tkinter as tk

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class ClickHandler:
    """点击处理器（单击/双击/与拖动判定协作）"""

    def __init__(self, app: "DesktopPet") -> None:
        self.app = app

    def on_mouse_down(self, event: tk.Event) -> None:
        """鼠标按下事件 - 处理单击/双击/拖动"""
        app = self.app
        if app.click_through:
            return

        app._pending_drag = True
        app._mouse_down_x = event.x
        app._mouse_down_y = event.y
        app._drag_started = False

        current_time = int(time.time() * 1000)
        time_since_last_click = current_time - app._last_click_time

        if time_since_last_click < 300:
            app._click_count = 2
            self._handle_double_click(event)
        else:
            app._click_count = 1
            app._last_click_time = current_time
            app.root.after(300, lambda: self._handle_single_click(event))

    def on_mouse_up(self, event: tk.Event) -> None:
        """鼠标释放事件"""
        app = self.app
        if app.dragging:
            app.drag.stop_drag(event)
        app._pending_drag = False

    def _handle_single_click(self, event: tk.Event) -> None:
        """处理单击"""
        app = self.app
        if app._click_count != 1:
            return
        if app._drag_started:
            return

        if app._music_playing:
            if app.music_panel.is_visible():
                app.music_panel.hide()
                app.speech_bubble.hide()
            else:
                app.music_panel.show()
                title = app.get_current_music_title()
                if title:
                    app.speech_bubble.show(
                        f"🎵 {title}", duration=None, allow_during_music=True
                    )
            return

        app.speech_bubble.show_click_reaction()

    def _handle_double_click(self, event: tk.Event) -> None:
        """处理双击"""
        app = self.app
        app._click_count = 0
        app._pending_drag = False
        app.quick_menu.show()
