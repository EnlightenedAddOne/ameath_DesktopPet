"""拖动处理（从 src/core/pet_core.py 拆分）"""

from __future__ import annotations

from typing import TYPE_CHECKING

import tkinter as tk

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class DragHandler:
    """拖动处理器"""

    def __init__(self, app: "DesktopPet") -> None:
        self.app = app

    def start_drag(self, event: tk.Event) -> None:
        """开始拖动"""
        app = self.app
        if app.click_through:
            return

        app.dragging = True
        app.drag_start_x = app._mouse_down_x
        app.drag_start_y = app._mouse_down_y
        app._pre_drag_frames = app.current_frames
        app._pre_drag_delays = app.current_delays
        app._click_count = 0
        app._drag_started = True

        if app.drag_frames:
            app.current_frames = app.drag_frames
            app.current_delays = [1000] * len(app.drag_frames)
            app.frame_index = 0
            app.label.config(image=app.current_frames[0])

    def do_drag(self, event: tk.Event) -> None:
        """拖动中"""
        app = self.app
        if not app.dragging and app._pending_drag:
            dx = event.x - app._mouse_down_x
            dy = event.y - app._mouse_down_y
            if abs(dx) > 5 or abs(dy) > 5:
                self.start_drag(event)

        if app.dragging:
            app.x = event.x_root - app.drag_start_x
            app.y = event.y_root - app.drag_start_y
            app.root.geometry(f"+{int(app.x)}+{int(app.y)}")
            if hasattr(app, "speech_bubble") and app.speech_bubble:
                app.speech_bubble.update_position()
            if hasattr(app, "pomodoro_indicator") and app.pomodoro_indicator:
                app.pomodoro_indicator.update_position()
            if hasattr(app, "music_panel") and app.music_panel:
                app.music_panel.update_position()
            if (
                hasattr(app, "ai_chat_panel")
                and app.ai_chat_panel
                and app.ai_chat_panel.is_visible()
            ):
                app.ai_chat_panel._update_position()

    def stop_drag(self, event: tk.Event) -> None:
        """停止拖动"""
        app = self.app
        app.dragging = False
        if app._pre_drag_frames is not None:
            app.current_frames = app._pre_drag_frames
            app.current_delays = app._pre_drag_delays
            app.frame_index = 0
