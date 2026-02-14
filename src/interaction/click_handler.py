"""点击交互（从 src/core/pet_core.py 拆分）"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

import tkinter as tk

from src.constants import BEHAVIOR_MODE_QUIET

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class ClickHandler:
    """点击处理器（单击/双击/与拖动判定协作）"""

    def __init__(self, app: "DesktopPet") -> None:
        self.app = app
        self._click_animation_after_id = None

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

        # 安静模式下随机播放 idle3 或 idle4 动画
        if app.behavior_mode == BEHAVIOR_MODE_QUIET:
            # 音乐播放时禁止单击动画切换和气泡显示
            if app._music_playing:
                # 音乐播放模式下单击时显示歌名和音乐控制组件
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

            # 取消之前的定时器
            if self._click_animation_after_id:
                app.root.after_cancel(self._click_animation_after_id)
                self._click_animation_after_id = None

            idle_gifs = getattr(app, "idle_gifs", [])
            if len(idle_gifs) >= 4:
                # 随机选择 idle3 (index 2) 或 idle4 (index 3)
                idx = random.choice([2, 3])
                frames, delays = idle_gifs[idx]
                app.current_frames = frames
                app.current_delays = delays
                app.frame_index = 0
                if frames:
                    app.label.config(image=frames[0])

                # 2000ms 后切换回普通待机动画 (idle2)
                self._click_animation_after_id = app.root.after(
                    2000, self._restore_idle_animation
                )
            # 安静模式下也触发点击反应气泡
            app.speech_bubble.show_click_reaction()
            return

        # 音乐播放模式下显示歌名和音乐控制组件
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

    def _restore_idle_animation(self) -> None:
        """恢复普通待机动画"""
        self._click_animation_after_id = None
        app = self.app

        # 确保仍在安静模式
        if app.behavior_mode != BEHAVIOR_MODE_QUIET:
            return

        idle_gifs = getattr(app, "idle_gifs", [])
        if idle_gifs:
            # 切换回 idle2 (index 1)
            frames, delays = idle_gifs[1]
            app.current_frames = frames
            app.current_delays = delays
            app.frame_index = 0
            if frames:
                app.label.config(image=frames[0])
