"""番茄钟进度条显示模块"""

from __future__ import annotations

import tkinter as tk

from src.constants import TRANSPARENT_COLOR


class PomodoroIndicator:
    """番茄钟进度条"""

    def __init__(self, app) -> None:
        self.app = app
        self.window: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None
        self._offset_x = 0
        self._offset_y = 0
        self._width = 150
        self._height = 18
        self._style = {
            "bg": "#FFFFFF",
            "border": "#7BEAF7",
            "track": "#F7A7B6",
            "text": "#2E2A28",
        }

    def show(self) -> None:
        """显示进度条"""
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            return

        self.window = tk.Toplevel(self.app.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.config(bg=TRANSPARENT_COLOR)
        self.window.attributes("-transparentcolor", TRANSPARENT_COLOR)

        self.canvas = tk.Canvas(
            self.window,
            width=self._width,
            height=self._height,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self._redraw(phase="专注", remaining=0, total=1)
        self.update_position()

    def hide(self) -> None:
        """隐藏进度条"""
        if self.window:
            self.window.destroy()
            self.window = None
            self.canvas = None

    def update_progress(self, phase: str, remaining: int, total: int) -> None:
        """更新进度条

        Args:
            phase: 阶段名称
            remaining: 剩余秒数
            total: 阶段总秒数
        """
        if not self.window or not self.window.winfo_exists():
            self.show()
        self._redraw(phase, remaining, total)

    def update_position(self) -> None:
        """更新进度条位置"""
        if not self.window or not self.window.winfo_exists():
            return

        x = int(self.app.x + self.app.w // 2)
        y = int(self.app.y - 22)

        self._offset_x = x - int(self.app.x)
        self._offset_y = y - int(self.app.y)

        screen_w = self.app.root.winfo_screenwidth()
        screen_h = self.app.root.winfo_screenheight()
        width = self._width
        height = self._height

        x_pos = max(10, min(x - width // 2, screen_w - width - 10))
        y_pos = max(10, min(y - height, screen_h - height - 10))
        self.window.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

    def _redraw(self, phase: str, remaining: int, total: int) -> None:
        if not self.canvas:
            return

        self.canvas.delete("all")
        radius = 9
        progress = 0.0 if total <= 0 else max(0.0, min(1.0, 1 - remaining / total))
        fill_width = int((self._width - 4) * progress)

        self._draw_rounded_rect(
            1,
            1,
            self._width - 2,
            self._height - 2,
            radius=radius,
            fill=self._style["bg"],
            outline=self._style["border"],
            width=1,
        )

        if fill_width > 0:
            self._draw_rounded_rect(
                2,
                2,
                2 + fill_width,
                self._height - 2,
                radius=radius - 2,
                fill=self._style["track"],
                outline="",
                width=0,
            )

        minutes = max(0, remaining) // 60
        seconds = max(0, remaining) % 60
        text = f"{phase} {minutes:02d}:{seconds:02d}"
        self.canvas.create_text(
            self._width // 2,
            self._height // 2,
            text=text,
            fill=self._style["text"],
            font=("Microsoft YaHei UI", 8, "bold"),
        )

    def _draw_rounded_rect(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        radius: int,
        fill: str,
        outline: str,
        width: int,
    ) -> None:
        if not self.canvas:
            return

        radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
        if radius == 0:
            self.canvas.create_rectangle(
                x1, y1, x2, y2, fill=fill, outline=outline, width=width
            )
            return

        self.canvas.create_arc(
            x1,
            y1,
            x1 + radius * 2,
            y1 + radius * 2,
            start=90,
            extent=90,
            fill=fill,
            outline=outline,
            width=width,
        )
        self.canvas.create_arc(
            x2 - radius * 2,
            y1,
            x2,
            y1 + radius * 2,
            start=0,
            extent=90,
            fill=fill,
            outline=outline,
            width=width,
        )
        self.canvas.create_arc(
            x2 - radius * 2,
            y2 - radius * 2,
            x2,
            y2,
            start=270,
            extent=90,
            fill=fill,
            outline=outline,
            width=width,
        )
        self.canvas.create_arc(
            x1,
            y2 - radius * 2,
            x1 + radius * 2,
            y2,
            start=180,
            extent=90,
            fill=fill,
            outline=outline,
            width=width,
        )
        self.canvas.create_rectangle(
            x1 + radius,
            y1,
            x2 - radius,
            y2,
            fill=fill,
            outline=outline,
            width=width,
        )
        self.canvas.create_rectangle(
            x1,
            y1 + radius,
            x2,
            y2 - radius,
            fill=fill,
            outline=outline,
            width=width,
        )
