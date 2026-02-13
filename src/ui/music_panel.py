"""音乐控制面板（胶囊风格）"""

from __future__ import annotations

import tkinter as tk
from typing import Optional

from src.constants import TRANSPARENT_COLOR


class MusicPanel:
    """音乐控制面板

    - 透明窗口
    - Canvas 绘制胶囊底板、胶囊按钮、进度条
    """

    def __init__(self, app) -> None:
        self.app = app
        self.window: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None

        self._progress_after_id: Optional[str] = None
        self._dragging = False

        # 尺寸
        self._w = 248
        self._h = 76
        self._pad = 8

        # 主题（粉/浅蓝/白，偏网易云/KG）
        self._bg = "#FFFFFF"
        self._border = "#DDE6F5"
        self._shadow = "#EAF1FF"
        self._text = "#2E2A28"
        self._muted = "#6E6A68"
        self._accent = "#F7A7B6"  # 粉
        self._accent2 = "#7BEAF7"  # 浅蓝
        self._hover = "#F3F8FF"
        self._pressed = "#E7F0FF"

        # 布局
        self._track_y = 16
        self._track_h = 10
        self._buttons_y = 38
        self._btn_w = 58
        self._btn_h = 26
        self._btn_gap = 10

        # Canvas item ids
        self._pill_id = None
        self._track_bg_id = None
        self._track_fill_id = None
        self._knob_id = None
        self._time_id = None

        self._btn_prev = {}
        self._btn_play = {}
        self._btn_next = {}

    def show(self) -> None:
        """显示面板"""
        if not self.window or not self.window.winfo_exists():
            self._create_window()
        self.update_position()
        if self.window:
            self.window.deiconify()
            self.window.lift()
        self._redraw_all()
        self._schedule_progress()

    def hide(self) -> None:
        """隐藏面板"""
        if self._progress_after_id:
            self.app.root.after_cancel(self._progress_after_id)
            self._progress_after_id = None
        if self.window and self.window.winfo_exists():
            self.window.withdraw()

    def is_visible(self) -> bool:
        if not self.window or not self.window.winfo_exists():
            return False
        return str(self.window.state()) != "withdrawn"

    def update_position(self) -> None:
        """更新面板位置：桌宠正下方居中"""
        if not self.window or not self.window.winfo_exists():
            return

        x = int(self.app.x + self.app.w // 2 - self._w // 2)
        y = int(self.app.y + self.app.h - 2)

        screen_w = self.app.root.winfo_screenwidth()
        screen_h = self.app.root.winfo_screenheight()

        x_pos = max(10, min(x, screen_w - self._w - 10))
        y_pos = max(10, min(y, screen_h - self._h - 10))
        self.window.geometry(f"{self._w}x{self._h}+{x_pos}+{y_pos}")

    def _create_window(self) -> None:
        self.window = tk.Toplevel(self.app.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.config(bg=TRANSPARENT_COLOR)
        self.window.attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.window.attributes("-alpha", 1.0)

        self.canvas = tk.Canvas(
            self.window,
            width=self._w,
            height=self._h,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 进度条交互
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _redraw_all(self) -> None:
        if not self.canvas:
            return
        self.canvas.delete("all")

        # 阴影层
        self._draw_rounded_rect(
            self.canvas,
            self._pad + 1,
            self._pad + 2,
            self._w - self._pad + 1,
            self._h - self._pad + 2,
            radius=16,
            fill=self._shadow,
            outline="",
            width=0,
        )

        # 胶囊底板
        self._pill_id = self._draw_rounded_rect(
            self.canvas,
            self._pad,
            self._pad,
            self._w - self._pad,
            self._h - self._pad,
            radius=16,
            fill=self._bg,
            outline=self._border,
            width=1,
        )

        self._draw_progress()
        self._draw_buttons()

    def _draw_progress(self) -> None:
        if not self.canvas:
            return

        x1 = self._pad + 14
        x2 = self._w - self._pad - 14
        y1 = self._pad + self._track_y
        y2 = y1 + self._track_h
        r = self._track_h // 2

        # track bg
        self._track_bg_id = self._draw_rounded_rect(
            self.canvas,
            x1,
            y1,
            x2,
            y2,
            radius=r,
            fill="#EEF3FF",
            outline="#E0E9FA",
            width=1,
        )

        pos = self.app.get_music_position() if self.app.is_music_playing() else 0.0
        total = self.app.get_music_length() if self.app.is_music_playing() else 0.0
        progress = 0.0 if total <= 0 else max(0.0, min(1.0, pos / total))
        fill_x2 = int(x1 + (x2 - x1) * progress)

        if fill_x2 > x1 + r:
            self._track_fill_id = self._draw_rounded_rect(
                self.canvas,
                x1,
                y1,
                fill_x2,
                y2,
                radius=r,
                fill=self._accent,
                outline="",
                width=0,
            )

        # knob
        knob_r = 7
        knob_x = int(x1 + (x2 - x1) * progress)
        knob_y = (y1 + y2) // 2
        self._knob_id = self.canvas.create_oval(
            knob_x - knob_r,
            knob_y - knob_r,
            knob_x + knob_r,
            knob_y + knob_r,
            fill="#FFFFFF",
            outline=self._accent2,
            width=2,
        )

        # time text (small)
        if total > 0:
            text = f"{self._fmt(pos)} / {self._fmt(total)}"
        else:
            text = "--:-- / --:--"
        self._time_id = self.canvas.create_text(
            self._w - self._pad - 18,
            self._pad + 10,
            text=text,
            fill=self._muted,
            font=("Microsoft YaHei UI", 8),
            anchor="ne",
        )

    def _draw_buttons(self) -> None:
        if not self.canvas:
            return

        row_w = self._btn_w * 3 + self._btn_gap * 2
        start_x = int(self._w // 2 - row_w // 2)
        y1 = self._pad + self._buttons_y
        cy = y1 + self._btn_h // 2

        prev_cx = start_x + self._btn_w // 2
        play_cx = start_x + self._btn_w + self._btn_gap + self._btn_w // 2
        next_cx = start_x + (self._btn_w + self._btn_gap) * 2 + self._btn_w // 2

        self._btn_prev = self._draw_icon_button(
            cx=prev_cx,
            cy=cy,
            text="⏮",
            command=self._prev,
            kind="prev",
            icon_color=self._muted,
        )

        play_text = "▶" if self.app.is_music_paused() else "⏸"
        self._btn_play = self._draw_icon_button(
            cx=play_cx,
            cy=cy,
            text=play_text,
            command=self._toggle_play,
            kind="play",
            icon_color=self._text,
            hover_fill="#EAFBFF",
            pressed_fill="#DDF6FF",
            radius=15,
        )

        self._btn_next = self._draw_icon_button(
            cx=next_cx,
            cy=cy,
            text="⏭",
            command=self._next,
            kind="next",
            icon_color=self._muted,
        )

    def _draw_icon_button(
        self,
        cx: int,
        cy: int,
        text: str,
        command,
        kind: str,
        icon_color: str | None = None,
        hover_fill: str | None = None,
        pressed_fill: str | None = None,
        radius: int = 14,
    ) -> dict:
        """绘制无底色按钮：仅图标 + 悬浮/按下柔光"""
        if not self.canvas:
            return {}

        icon_color = icon_color or self._text
        hover_fill = hover_fill or self._hover
        pressed_fill = pressed_fill or self._pressed

        tag = f"btn_{kind}"

        # hover/press highlight (hidden by default)
        hi_id = self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill=hover_fill,
            outline="",
            width=0,
            state="hidden",
        )

        # hit area (invisible on white pill)
        hit_id = self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill=self._bg,
            outline=self._bg,
            width=0,
        )

        txt_id = self.canvas.create_text(
            cx,
            cy,
            text=text,
            fill=icon_color,
            font=("Microsoft YaHei UI", 11, "bold"),
        )

        self.canvas.addtag_withtag(tag, hi_id)
        self.canvas.addtag_withtag(tag, hit_id)
        self.canvas.addtag_withtag(tag, txt_id)

        self.canvas.tag_bind(
            tag,
            "<Enter>",
            lambda e, b={"hi": hi_id, "hover": hover_fill}: self._btn_hover(b, True),
        )
        self.canvas.tag_bind(
            tag,
            "<Leave>",
            lambda e, b={"hi": hi_id, "hover": hover_fill}: self._btn_hover(b, False),
        )
        self.canvas.tag_bind(
            tag,
            "<ButtonPress-1>",
            lambda e, b={"hi": hi_id, "pressed": pressed_fill}: self._btn_press(b),
        )
        self.canvas.tag_bind(
            tag,
            "<ButtonRelease-1>",
            lambda e,
            b={"hi": hi_id, "hover": hover_fill},
            cb=command: self._btn_release(b, cb),
        )

        return {"tag": tag, "hi": hi_id, "hit": hit_id, "text": txt_id}

    def _btn_hover(self, btn: dict, on: bool) -> None:
        if not self.canvas:
            return
        if self._dragging:
            return
        hi_id = btn.get("hi")
        if not hi_id:
            return
        if on:
            self.canvas.itemconfigure(
                hi_id, fill=btn.get("hover", self._hover), state="normal"
            )
        else:
            self.canvas.itemconfigure(hi_id, state="hidden")

    def _btn_press(self, btn: dict) -> None:
        if not self.canvas:
            return
        hi_id = btn.get("hi")
        if not hi_id:
            return
        self.canvas.itemconfigure(
            hi_id, fill=btn.get("pressed", self._pressed), state="normal"
        )

    def _btn_release(self, btn: dict, cb) -> None:
        if not self.canvas:
            return
        hi_id = btn.get("hi")
        if hi_id:
            # keep a soft hover after release, then redraw will reset anyway
            self.canvas.itemconfigure(
                hi_id, fill=btn.get("hover", self._hover), state="normal"
            )
        cb()
        self._redraw_all()

    def _on_press(self, event) -> None:
        if not self.canvas or not self.app.is_music_playing():
            return
        if not self._is_in_track(event.x, event.y):
            return
        self._dragging = True
        self._seek_by_x(event.x)

    def _on_drag(self, event) -> None:
        if not self._dragging:
            return
        self._seek_by_x(event.x)

    def _on_release(self, event) -> None:
        self._dragging = False

    def _is_in_track(self, x: int, y: int) -> bool:
        x1 = self._pad + 14
        x2 = self._w - self._pad - 14
        y1 = self._pad + self._track_y
        y2 = y1 + self._track_h
        return x1 <= x <= x2 and (y1 - 8) <= y <= (y2 + 8)

    def _seek_by_x(self, x: int) -> None:
        x1 = self._pad + 14
        x2 = self._w - self._pad - 14
        total = self.app.get_music_length()
        if total <= 0:
            return
        ratio = (x - x1) / max(1, (x2 - x1))
        ratio = max(0.0, min(1.0, ratio))
        self.app.seek_music(total * ratio)
        self._redraw_all()

    def _schedule_progress(self) -> None:
        if not self.window or not self.window.winfo_exists():
            return
        if self.is_visible() and self.app.is_music_playing() and not self._dragging:
            self._redraw_all()
        self._progress_after_id = self.app.root.after(300, self._schedule_progress)

    def _prev(self) -> None:
        self.app.prev_music()

    def _next(self) -> None:
        self.app.next_music()

    def _toggle_play(self) -> None:
        self.app.toggle_music_pause()

    def _fmt(self, seconds: float) -> str:
        seconds = max(0, int(seconds))
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def _draw_rounded_rect(
        self,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        radius: int,
        fill: str,
        outline: str,
        width: int,
    ) -> int:
        # Use a smoothed polygon; returns polygon id.
        radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
        if radius == 0:
            return canvas.create_rectangle(
                x1, y1, x2, y2, fill=fill, outline=outline, width=width
            )

        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return canvas.create_polygon(
            points,
            smooth=True,
            splinesteps=36,
            fill=fill,
            outline=outline,
            width=width,
        )
