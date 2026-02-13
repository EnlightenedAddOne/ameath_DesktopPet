"""快捷菜单模块 - 双击宠物时显示的快捷操作面板"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet

from src.constants import (
    BEHAVIOR_MODE_ACTIVE,
    BEHAVIOR_MODE_CLINGY,
    BEHAVIOR_MODE_QUIET,
)


class QuickMenu:
    """快捷菜单类"""

    def __init__(self, app: DesktopPet):
        self.app = app
        self.window: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._container: tk.Frame | None = None
        self._menu_width = 0
        self._menu_height = 0
        self._music_text = tk.StringVar(master=self.app.root, value="🎵 播放音乐")
        self._buttons: list[tk.Button] = []
        self._behavior_buttons: dict[str, tk.Button] = {}
        self._active_behavior_button: tk.Button | None = None
        self._panel_bg = "#FFFFFF"
        self._panel_border = "#F7A7B6"
        self._panel_inner_border = "#7BEAF7"
        self._hover_bg = "#EAFBFE"
        self._active_bg = "#F7A7B6"
        self._text_color = "#2E2A28"
        self._active_fg = "#2E2A28"
        self._title_color = "#F7A7B6"
        self._section_color = "#7BEAF7"

        self.app.root.after_idle(self._preload)

    def show(self) -> None:
        """显示快捷菜单"""
        if not self.window or self._menu_width == 0 or self._menu_height == 0:
            self._create_window()

        if self.app.is_music_playing():
            self._music_text.set("⏹️ 停止音乐")
        else:
            self._music_text.set("🎵 播放音乐")

        self._refresh_behavior_buttons()

        # 计算位置（宠物旁边）
        x = int(self.app.x + self.app.w + 10)
        y = int(self.app.y)

        # 确保不超出屏幕
        screen_w = self.app.root.winfo_screenwidth()
        screen_h = self.app.root.winfo_screenheight()

        # 如果在屏幕右侧，显示在宠物左侧
        if x + 150 > screen_w:
            x = int(self.app.x - 160)

        width = self._menu_width
        height = self._menu_height

        # 确保在屏幕内
        x_pos = max(10, min(x, screen_w - width - 10))
        y_pos = max(10, min(y, screen_h - height - 10))

        self.window.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        self.window.deiconify()
        self.window.lift()

        # 点击外部自动关闭
        self._setup_auto_close()

        if self.window:
            self.window.focus_force()

    def hide(self) -> None:
        """隐藏快捷菜单"""
        if self.window:
            self.window.withdraw()

    def _draw_rounded_rect(
        self,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        radius: int,
        **kwargs,
    ) -> None:
        """绘制圆角矩形"""
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
        canvas.create_polygon(points, smooth=True, **kwargs)

    def _preload(self) -> None:
        """预加载菜单，减少首次弹出卡顿"""
        if not self.window:
            self._create_window()
            self.hide()

    def _create_window(self) -> None:
        """创建菜单窗口与控件"""
        self.window = tk.Toplevel(self.app.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.withdraw()

        transparent_color = "#FDFBF6"

        self.window.config(bg=transparent_color)
        self.window.attributes("-transparentcolor", transparent_color)
        self.window.attributes("-alpha", 0.92)

        self._canvas = tk.Canvas(
            self.window,
            bg=transparent_color,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._container = tk.Frame(self._canvas, bg=self._panel_bg)

        # 创建标题
        title = tk.Label(
            self._container,
            text="快捷操作",
            font=("Microsoft YaHei UI", 10, "bold"),
            bg=self._panel_bg,
            fg=self._title_color,
            pady=5,
        )
        title.pack(fill=tk.X)

        # 分隔线
        separator = tk.Frame(self._container, height=1, bg=self._panel_inner_border)
        separator.pack(fill=tk.X, padx=8)

        # 创建按钮
        self._buttons = []
        self._behavior_buttons = {}

        self._create_section_label("行为模式")
        self._create_behavior_group()

        self._create_section_label("缩放")
        self._create_scale_group()

        self._create_section_label("快捷操作")
        self._create_action_grid()

        padding = 10
        self._canvas.update_idletasks()
        content_width = self._container.winfo_reqwidth()
        content_height = self._container.winfo_reqheight()
        canvas_width = content_width + padding * 2
        canvas_height = content_height + padding * 2

        self._canvas.config(width=canvas_width, height=canvas_height)
        self._canvas.create_window(
            padding,
            padding,
            window=self._container,
            anchor="nw",
        )
        # 外描边
        self._draw_rounded_rect(
            self._canvas,
            1,
            1,
            canvas_width - 2,
            canvas_height - 2,
            radius=14,
            fill=self._panel_bg,
            outline=self._panel_border,
            width=1,
        )
        # 内描边（轻科技感）
        self._draw_rounded_rect(
            self._canvas,
            3,
            3,
            canvas_width - 4,
            canvas_height - 4,
            radius=12,
            fill="",
            outline=self._panel_inner_border,
            width=1,
        )
        self._canvas.tag_lower("all")

        self._menu_width = canvas_width
        self._menu_height = canvas_height

    def _create_button(
        self, text: str | tk.StringVar, command: Callable[[], None]
    ) -> tk.Button:
        """创建菜单按钮"""
        if not self._container:
            return tk.Button()

        if isinstance(text, tk.StringVar):
            btn = tk.Button(
                self._container,
                textvariable=text,
                font=("Microsoft YaHei UI", 9),
                relief=tk.FLAT,
                borderwidth=0,
                highlightthickness=0,
                cursor="hand2",
                command=command,
                padx=8,
                pady=2,
            )
        else:
            btn = tk.Button(
                self._container,
                text=text,
                font=("Microsoft YaHei UI", 9),
                relief=tk.FLAT,
                borderwidth=0,
                highlightthickness=0,
                cursor="hand2",
                command=command,
                padx=8,
                pady=2,
            )

        btn.pack(fill=tk.X, padx=8, pady=1)
        self._buttons.append(btn)
        self._bind_button_hover(btn)
        self._apply_button_bg(btn)
        return btn

    def _create_button_widget(
        self, parent: tk.Misc, text: str | tk.StringVar, command: Callable[[], None]
    ) -> tk.Button:
        """创建按钮控件"""
        if isinstance(text, tk.StringVar):
            btn = tk.Button(
                parent,
                textvariable=text,
                font=("Microsoft YaHei UI", 9),
                relief=tk.FLAT,
                borderwidth=0,
                highlightthickness=0,
                cursor="hand2",
                command=command,
                padx=8,
                pady=2,
            )
        else:
            btn = tk.Button(
                parent,
                text=text,
                font=("Microsoft YaHei UI", 9),
                relief=tk.FLAT,
                borderwidth=0,
                highlightthickness=0,
                cursor="hand2",
                command=command,
                padx=8,
                pady=2,
            )

        self._buttons.append(btn)
        self._bind_button_hover(btn)
        self._apply_button_bg(btn)
        return btn

    def _create_section_label(self, text: str) -> None:
        """创建分组标题"""
        if not self._container:
            return

        label = tk.Label(
            self._container,
            text=text,
            font=("Microsoft YaHei UI", 8, "bold"),
            bg=self._panel_bg,
            fg=self._section_color,
            pady=3,
        )
        label.pack(fill=tk.X, padx=8, pady=(6, 2))

    def _create_scale_group(self) -> None:
        """创建缩放按钮组"""
        if not self._container:
            return

        group = tk.Frame(self._container, bg=self._panel_bg)
        group.pack(fill=tk.X, padx=8, pady=1)

        btn_up = self._create_button_widget(group, "🔍 放大", self._scale_up)
        btn_down = self._create_button_widget(group, "🔎 缩小", self._scale_down)

        btn_up.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))
        btn_down.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

    def _create_behavior_group(self) -> None:
        """创建行为模式按钮组"""
        if not self._container:
            return

        group = tk.Frame(self._container, bg=self._panel_bg)
        group.pack(fill=tk.X, padx=8, pady=1)

        btn_quiet = self._create_button_widget(group, "😴 安静", self._set_quiet_mode)
        btn_active = self._create_button_widget(group, "⚡ 活泼", self._set_active_mode)
        btn_clingy = self._create_button_widget(group, "🧲 粘人", self._set_clingy_mode)

        btn_quiet.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=1)
        btn_active.grid(row=0, column=1, sticky="ew", padx=(4, 4), pady=1)
        btn_clingy.grid(row=0, column=2, sticky="ew", padx=(4, 0), pady=1)

        group.columnconfigure(0, weight=1)
        group.columnconfigure(1, weight=1)
        group.columnconfigure(2, weight=1)

        self._behavior_buttons[BEHAVIOR_MODE_QUIET] = btn_quiet
        self._behavior_buttons[BEHAVIOR_MODE_ACTIVE] = btn_active
        self._behavior_buttons[BEHAVIOR_MODE_CLINGY] = btn_clingy

    def _create_action_grid(self) -> None:
        """创建快捷操作按钮网格"""
        if not self._container:
            return

        group = tk.Frame(self._container, bg=self._panel_bg)
        group.pack(fill=tk.X, padx=8, pady=1)

        items: list[tuple[str | tk.StringVar, Callable[[], None]]] = [
            ("👻 穿透", self._toggle_click_through),
            ("🍅 开始/停", self._toggle_pomodoro),
            ("🍅 重置", self._reset_pomodoro),
            (self._music_text, self._toggle_music),
            ("👁️ 隐藏", self._hide_pet),
            ("❌ 退出", self._quit),
        ]

        columns = 2
        last_btn: tk.Button | None = None
        for index, (text, command) in enumerate(items):
            row = index // columns
            column = index % columns
            btn = self._create_button_widget(group, text, command)
            btn.grid(row=row, column=column, sticky="ew", padx=4, pady=1)
            last_btn = btn

        if len(items) % columns == 1 and last_btn is not None:
            last_btn.grid(columnspan=2)

        group.columnconfigure(0, weight=1)
        group.columnconfigure(1, weight=1)

    def _bind_button_hover(self, btn: tk.Button) -> None:
        """绑定按钮悬停效果"""
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self._hover_bg))
        btn.bind("<Leave>", lambda e, b=btn: self._apply_button_bg(b))

    def _apply_button_bg(self, btn: tk.Button) -> None:
        """应用按钮背景颜色"""
        if btn == self._active_behavior_button:
            btn.configure(
                bg=self._active_bg,
                activebackground=self._hover_bg,
                fg=self._active_fg,
                activeforeground=self._active_fg,
            )
        else:
            btn.configure(
                bg=self._panel_bg,
                activebackground=self._hover_bg,
                fg=self._text_color,
                activeforeground=self._text_color,
            )

    def _refresh_behavior_buttons(self) -> None:
        """刷新行为模式按钮状态"""
        if not self._behavior_buttons:
            return

        current_mode = self.app.behavior_mode
        self._active_behavior_button = None
        for mode, btn in self._behavior_buttons.items():
            if mode == current_mode:
                self._active_behavior_button = btn

        for btn in self._behavior_buttons.values():
            self._apply_button_bg(btn)

    def _setup_auto_close(self) -> None:
        """设置点击外部自动关闭"""
        if not self.window:
            return

        def check_focus():
            if self.window and not self.window.focus_displayof():
                self.hide()
            else:
                self.window.after(100, check_focus)

        self.window.after(100, check_focus)

    def _toggle_click_through(self) -> None:
        """切换鼠标穿透"""
        self.app.toggle_click_through()
        self.hide()

    def _set_quiet_mode(self) -> None:
        """设置安静模式"""
        self.app.set_behavior_mode(BEHAVIOR_MODE_QUIET)
        self.hide()

    def _set_active_mode(self) -> None:
        """设置活泼模式"""
        self.app.set_behavior_mode(BEHAVIOR_MODE_ACTIVE)
        self.hide()

    def _set_clingy_mode(self) -> None:
        """设置粘人模式"""
        self.app.set_behavior_mode(BEHAVIOR_MODE_CLINGY)
        self.hide()

    def _scale_up(self) -> None:
        """放大"""
        if self.app.scale_index < len(self.app.scale_options) - 1:
            self.app.set_scale(self.app.scale_index + 1)
        self.hide()

    def _scale_down(self) -> None:
        """缩小"""
        if self.app.scale_index > 0:
            self.app.set_scale(self.app.scale_index - 1)
        self.hide()

    def _hide_pet(self) -> None:
        """隐藏宠物"""
        self.app.root.withdraw()
        self.hide()

    def _toggle_music(self) -> None:
        """切换音乐播放"""
        if self.app.toggle_music_playback():
            self._music_text.set("⏹️ 停止音乐")
        else:
            self._music_text.set("🎵 播放音乐")
        self.hide()

    def _toggle_pomodoro(self) -> None:
        """开始/停止番茄钟"""
        self.app.toggle_pomodoro()
        self.hide()

    def _reset_pomodoro(self) -> None:
        """重置番茄钟"""
        self.app.reset_pomodoro()
        self.hide()

    def _quit(self) -> None:
        """退出程序"""
        self.app.request_quit()
        self.hide()
