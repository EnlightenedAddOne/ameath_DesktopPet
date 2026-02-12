"""对话气泡模块 - 点击宠物时显示的对话（美化版）"""

from __future__ import annotations

import random
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from src.pet import DesktopPet

from src.constants import TRANSPARENT_COLOR


# 不同时间段的问候语
GREETINGS = {
    "morning": [
        "早上好呀！☀️",
        "新的一天开始啦~",
        "早安！要元气满满哦！",
        "早上好！记得吃早餐哦~",
        "又是美好的一天！",
    ],
    "noon": [
        "中午好！",
        "该吃午饭啦~",
        "午后时光，休息一下吧",
        "中午好！要不要小憩一下？",
    ],
    "afternoon": [
        "下午好！",
        "工作/学习辛苦啦~",
        "下午茶时间到了吗？",
        "加油！马上就下班/放学了！",
    ],
    "evening": [
        "晚上好！🌙",
        "今天过得怎么样？",
        "晚上是放松的时间~",
        "辛苦了一天，好好休息吧~",
    ],
    "night": [
        "夜深了，还不睡吗？😴",
        "熬夜对身体不好哦~",
        "晚安，做个好梦~",
        "该睡觉啦，明天见~",
    ],
}

# 随机互动台词
RANDOM_LINES = [
    "我在这里陪着你哦~ 💕",
    "有什么我可以帮你的吗？",
    "无聊的话可以找我玩呀~",
    "你今天看起来很不错呢！",
    "要劳逸结合哦~",
    "记得多喝水！💧",
    "长时间看屏幕对眼睛不好哦~",
    "适当活动一下身体吧~",
    "我在发呆... (￣▽￣)",
    "要不要休息一下？",
]

# 点击反应台词
CLICK_REACTIONS = [
    "哎呀，被发现了！😆",
    "别戳我啦~",
    "哈哈，好痒！",
    "嘿嘿，抓到我了！",
    "唔...怎么啦？",
    "我在呢！👋",
    "你找到我啦！",
]


class SpeechBubble:
    """对话气泡类 - 美化版"""

    def __init__(self, app: DesktopPet):
        self.app = app
        self.window: tk.Toplevel | None = None
        self.after_id: str | None = None
        self.label: tk.Label | None = None
        self._offset_x = 0  # 相对于宠物的偏移
        self._offset_y = 0
        self._style = {
            "bubble": "#FFD1E8",
            "bubble_edge": "#FFB6DB",
            "highlight": "#FFE8F4",
            "text": "#5C3B4A",
            "muted": "#8E6A7B",
        }

    def show(
        self,
        text: str | None = None,
        duration: int | None = 3000,
        x: int | None = None,
        y: int | None = None,
        allow_during_music: bool = False,
    ) -> None:
        """显示对话气泡

        Args:
            text: 显示的文字，None则随机选择
            duration: 显示时长（毫秒）
            x: X坐标，None则自动计算
            y: Y坐标，None则自动计算
        """
        if getattr(self.app, "_music_playing", False) and not allow_during_music:
            return

        # 如果已有气泡，先关闭
        self.hide()

        # 获取文字
        if text is None:
            text = self._get_random_text()

        # 计算位置（相对于宠物）
        if x is None:
            x = int(self.app.x + self.app.w // 2)
        if y is None:
            y = int(self.app.y - 15)

        # 保存偏移量（用于跟随移动）
        self._offset_x = x - int(self.app.x)
        self._offset_y = y - int(self.app.y)

        # 创建气泡窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.config(bg=TRANSPARENT_COLOR)
        self.window.attributes("-transparentcolor", TRANSPARENT_COLOR)

        font = tkfont.Font(family="Microsoft YaHei UI", size=11, weight="bold")
        wrapped_lines = self._wrap_text(text, font, 200)
        text_width = (
            max(font.measure(line) for line in wrapped_lines) if wrapped_lines else 0
        )
        line_height = font.metrics("linespace")
        text_height = line_height * max(1, len(wrapped_lines))

        pad_x = 10
        pad_y = 8
        triangle_size = 12
        radius = 16
        width = text_width + pad_x * 2
        height = text_height + pad_y * 2

        canvas = tk.Canvas(
            self.window,
            width=width,
            height=height + triangle_size,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
        )
        canvas.pack()

        self._draw_rounded_rect(
            canvas,
            0,
            0,
            width,
            height,
            radius=radius,
            fill=self._style["bubble"],
            outline=self._style["bubble_edge"],
            width=2,
        )
        # 顶部柔光高亮
        self._draw_rounded_rect(
            canvas,
            6,
            4,
            width - 6,
            12,
            radius=8,
            fill=self._style["highlight"],
            outline="",
            width=0,
        )

        canvas.create_text(
            width // 2,
            height // 2,
            text="\n".join(wrapped_lines),
            font=font,
            fill=self._style["text"],
            justify=tk.CENTER,
        )

        # 绘制向下的三角形
        triangle_x = width // 2
        triangle_y = height
        canvas.create_polygon(
            triangle_x - triangle_size,
            triangle_y,
            triangle_x + triangle_size,
            triangle_y,
            triangle_x,
            triangle_y + triangle_size,
            fill=self._style["bubble"],
            outline=self._style["bubble_edge"],
        )

        # 调整窗口大小和位置
        self.window.update_idletasks()
        height = height + triangle_size

        # 确保不超出屏幕
        screen_w = self.app.root.winfo_screenwidth()
        screen_h = self.app.root.winfo_screenheight()
        x_pos = max(10, min(x - width // 2, screen_w - width - 10))
        y_pos = max(10, y - height)

        self.window.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

        # 自动关闭
        if duration is None or duration <= 0:
            return
        self.after_id = self.app.root.after(duration, self.hide)

    def update_position(self) -> None:
        """更新气泡位置（跟随宠物移动）"""
        if self.window and self.window.winfo_exists():
            # 根据当前宠物位置重新计算
            x = int(self.app.x + self._offset_x)
            y = int(self.app.y + self._offset_y)

            # 确保不超出屏幕
            screen_w = self.app.root.winfo_screenwidth()
            width = self.window.winfo_width()
            x_pos = max(10, min(x - width // 2, screen_w - width - 10))
            y_pos = max(10, y - self.window.winfo_height())

            self.window.geometry(f"+{x_pos}+{y_pos}")

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
    ) -> None:
        """绘制圆角矩形"""
        radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
        if radius == 0:
            canvas.create_rectangle(
                x1, y1, x2, y2, fill=fill, outline=outline, width=width
            )
            return

        canvas.create_arc(
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
        canvas.create_arc(
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
        canvas.create_arc(
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
        canvas.create_arc(
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
        canvas.create_rectangle(
            x1 + radius,
            y1,
            x2 - radius,
            y2,
            fill=fill,
            outline=outline,
            width=width,
        )
        canvas.create_rectangle(
            x1,
            y1 + radius,
            x2,
            y2 - radius,
            fill=fill,
            outline=outline,
            width=width,
        )

    def hide(self) -> None:
        """隐藏对话气泡"""
        if self.after_id:
            self.app.root.after_cancel(self.after_id)
            self.after_id = None

        if self.window:
            self.window.destroy()
            self.window = None
            self.label = None

    def is_visible(self) -> bool:
        """判断气泡是否可见"""
        if not self.window or not self.window.winfo_exists():
            return False
        return str(self.window.state()) != "withdrawn"

    def _wrap_text(self, text: str, font: tkfont.Font, max_width: int) -> List[str]:
        """按宽度换行文本"""
        lines: List[str] = []
        for raw_line in text.split("\n"):
            if not raw_line:
                lines.append("")
                continue
            current = ""
            for ch in raw_line:
                if font.measure(current + ch) > max_width and current:
                    lines.append(current)
                    current = ch
                else:
                    current += ch
            lines.append(current)
        return lines

    def _get_random_text(self) -> str:
        """获取随机问候语"""
        hour = datetime.now().hour

        # 根据时间选择问候语
        if 5 <= hour < 11:
            time_key = "morning"
        elif 11 <= hour < 14:
            time_key = "noon"
        elif 14 <= hour < 18:
            time_key = "afternoon"
        elif 18 <= hour < 22:
            time_key = "evening"
        else:
            time_key = "night"

        # 70%概率使用时间相关问候，30%概率使用随机台词
        if random.random() < 0.7:
            return random.choice(GREETINGS[time_key])
        else:
            return random.choice(RANDOM_LINES)

    def show_click_reaction(self) -> None:
        """显示点击反应"""
        text = random.choice(CLICK_REACTIONS)
        self.show(text, duration=2000)

    def show_greeting(self) -> None:
        """显示问候语"""
        self.show(duration=4000)
