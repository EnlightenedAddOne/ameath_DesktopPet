"""翻译模块"""

from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Callable, Optional

import requests
from PIL import Image, ImageTk

from src.config import load_config, update_config
from src.constants import (
    AI_DEFAULT_BASE_URLS,
    AI_PROVIDER_DEEPSEEK,
    AI_PROVIDER_KIMI,
    AI_PROVIDER_QWEN,
    DEFAULT_TRANSLATE_LANG,
    TRANSLATE_LANGUAGES,
)
from src.utils import resource_path

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class TranslateEngine:
    """翻译引擎 - 使用AI API进行翻译"""

    def __init__(self):
        self._config = None

    def _load_config(self) -> dict:
        """加载配置"""
        if self._config is None:
            self._config = load_config()
        return self._config

    def reload_config(self) -> None:
        """重新加载配置"""
        self._config = None

    def translate(
        self,
        text: str,
        target_lang: str,
        on_complete: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """翻译文本

        Args:
            text: 要翻译的文本
            target_lang: 目标语言代码
            on_complete: 翻译完成回调
            on_error: 翻译失败回调
        """
        config = self._load_config()

        if not config.get("ai_enabled", False):
            on_error("请先在AI配置中启用AI功能")
            return

        if not config.get("ai_api_key", ""):
            on_error("请先配置AI API密钥")
            return

        # 获取目标语言名称
        lang_name = TRANSLATE_LANGUAGES.get(target_lang, "中文")

        # 构建翻译prompt
        prompt = f"请将以下文本翻译成{lang_name}，只返回翻译结果，不要有任何解释或额外内容：\n\n{text}"

        # 使用线程执行翻译
        thread = threading.Thread(
            target=self._do_translate,
            args=(config, prompt, on_complete, on_error),
            daemon=True,
        )
        thread.start()

    def _do_translate(
        self,
        config: dict,
        prompt: str,
        on_complete: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """执行翻译请求"""
        try:
            provider = config.get("ai_provider", AI_PROVIDER_DEEPSEEK)
            api_key = config.get("ai_api_key", "")
            model = config.get("ai_model", "")
            base_url = config.get("ai_base_url", "")

            if not base_url:
                base_url = AI_DEFAULT_BASE_URLS.get(provider, "")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            # Kimi和千问需要特殊处理
            if provider == AI_PROVIDER_KIMI:
                headers["Authorization"] = f"Bearer {api_key}"
            elif provider == AI_PROVIDER_QWEN:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
            }

            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                on_complete(content.strip())
            elif response.status_code == 401:
                on_error("API密钥无效，请检查配置")
            else:
                error_text = response.text[:200]
                on_error(f"翻译失败: {response.status_code}\n{error_text}")

        except requests.Timeout:
            on_error("翻译请求超时，请重试")
        except Exception as e:
            on_error(f"翻译出错: {str(e)}")


class TranslateWindow:
    """翻译窗口"""

    def __init__(self, app: DesktopPet):
        self.app = app
        self.window: tk.Toplevel | None = None
        self.engine = TranslateEngine()
        self._original_text = ""
        self._translated_text = ""
        self._is_topmost = False
        self._pin_btn: tk.Button | None = None
        self._close_btn: tk.Button | None = None
        self._drag_offset: tuple[int, int] | None = None
        self._title_icon: ImageTk.PhotoImage | None = None
        self._pin_icon_normal: ImageTk.PhotoImage | None = None
        self._pin_icon_active: ImageTk.PhotoImage | None = None

    def show(self, text: str = "") -> None:
        """显示翻译窗口"""
        if self.window and self.window.winfo_exists():
            # 保持置顶状态
            try:
                self.window.attributes("-topmost", bool(self._is_topmost))
            except Exception:
                pass

            # 触发显示时，尽量把窗口带到前台
            try:
                self.window.deiconify()
            except Exception:
                pass
            try:
                self.window.lift()
            except Exception:
                pass
            try:
                self.window.focus_force()
            except Exception:
                pass

            # 未固定时，短暂 topmost 提升一次，避免被其它窗口压住
            if not self._is_topmost:
                try:
                    self.window.attributes("-topmost", True)
                    self.window.lift()

                    def _unset_topmost() -> None:
                        if self.window and self.window.winfo_exists():
                            try:
                                self.window.attributes("-topmost", False)
                            except Exception:
                                pass

                    self.window.after(150, _unset_topmost)
                except Exception:
                    pass
            if text:
                self._original_text = text
                self._source_text_widget.delete("1.0", tk.END)
                self._source_text_widget.insert("1.0", text)
                self._translated_text = ""
                self._result_text_widget.delete("1.0", tk.END)
            return

        self._original_text = text
        self._translated_text = ""
        self._create_window()

    def _create_window(self) -> None:
        """创建翻译窗口"""
        config = load_config()

        self.window = tk.Toplevel(self.app.root)
        self.window.title("Aemeath 翻译助手")
        self.window.geometry("450x560")
        self.window.resizable(False, False)
        # 自定义标题栏下，transient/父子关系容易导致被“父窗口置顶/隐藏”影响，这里保持独立窗口

        # 使用自定义标题栏（可在右上角紧贴放置按钮）
        self.window.overrideredirect(True)

        # overrideredirect 窗口不会显示系统标题栏图标，这里不再设置 iconbitmap

        # 统一关闭行为
        self.window.bind("<Escape>", lambda _e: self.window.destroy())

        # 默认不置顶；由固定按钮控制
        self._is_topmost = False
        try:
            self.window.attributes("-topmost", False)
        except Exception:
            pass

        # 居中显示
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 450) // 2
        y = (self.window.winfo_screenheight() - 560) // 2
        self.window.geometry(f"+{x}+{y}")

        # 确保显示在屏幕上
        try:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
        except Exception:
            pass

        # 颜色配置（与现有窗口保持一致：粉色 / 浅蓝 / 白色）
        bg_color = "#FFF5F8"
        primary_color = "#FF69B4"
        accent_color = "#6EC6FF"
        card_color = "#FFFFFF"
        border_color = "#FFD1E8"
        text_color = "#5C3B4A"
        muted_text_color = "#8A6B79"

        self.window.configure(bg=bg_color)

        # 顶部装饰条（自定义标题栏）
        title_frame = tk.Frame(self.window, bg=primary_color, height=50)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        # 标题区（图标 + 文本）
        title_left = tk.Frame(title_frame, bg=primary_color)
        title_left.pack(side=tk.LEFT, padx=16, pady=10)

        # 加载标题栏图标（使用机器翻译图标）
        try:
            # 使用机器翻译图标
            icon_path_png = resource_path("assets/icon/translate_icon.png")
            icon_img = Image.open(icon_path_png).convert("RGBA")
        except Exception:
            # 回退到ICO文件
            try:
                icon_img = Image.open(resource_path("assets/gifs/ameath.ico")).convert(
                    "RGBA"
                )
            except Exception:
                icon_img = None

        if icon_img:
            icon_img = icon_img.resize((28, 28), Image.Resampling.LANCZOS)
            self._title_icon = ImageTk.PhotoImage(icon_img)
            tk.Label(title_left, image=self._title_icon, bg=primary_color).pack(
                side=tk.LEFT, padx=(0, 8)
            )

        title_label = tk.Label(
            title_left,
            text="Aemeath 翻译助手",
            bg=primary_color,
            fg="white",
            font=("Microsoft YaHei", 13, "bold"),
        )
        title_label.pack(side=tk.LEFT)

        def _toggle_topmost() -> None:
            self._is_topmost = not self._is_topmost
            if self.window and self.window.winfo_exists():
                try:
                    self.window.attributes("-topmost", bool(self._is_topmost))
                except Exception:
                    pass
                try:
                    self.window.lift()
                except Exception:
                    pass
            self._refresh_pin_button(
                primary_color=primary_color, accent_color=accent_color
            )

        # 关闭按钮（最右）
        self._close_btn = tk.Button(
            title_frame,
            text="\u2715",
            bg=primary_color,
            fg="white",
            font=("Microsoft YaHei", 10, "bold"),
            borderwidth=0,
            padx=10,
            pady=4,
            cursor="hand2",
            activebackground="#FF85C1",
            activeforeground="white",
            command=self.window.destroy,
        )
        self._close_btn.pack(side=tk.RIGHT, padx=(0, 10), pady=12)

        # 置顶按钮：紧挨关闭按钮左侧，先加载图标
        try:
            pin_normal = Image.open(resource_path("assets/icon/取消固定.png")).convert(
                "RGBA"
            )
            pin_active = Image.open(resource_path("assets/icon/已固定.png")).convert(
                "RGBA"
            )
            # 调整图标大小
            pin_size = (16, 16)
            pin_normal = pin_normal.resize(pin_size, Image.Resampling.LANCZOS)
            pin_active = pin_active.resize(pin_size, Image.Resampling.LANCZOS)
            self._pin_icon_normal = ImageTk.PhotoImage(pin_normal)
            self._pin_icon_active = ImageTk.PhotoImage(pin_active)
        except Exception:
            self._pin_icon_normal = None
            self._pin_icon_active = None

        self._pin_btn = tk.Button(
            title_frame,
            image=self._pin_icon_normal if self._pin_icon_normal else None,
            text="\U0001f4cc" if not self._pin_icon_normal else "",
            bg=primary_color,
            fg="white",
            font=("Microsoft YaHei", 9, "bold"),
            borderwidth=0,
            padx=10,
            pady=4,
            cursor="hand2",
            activeforeground="white",
            command=_toggle_topmost,
        )
        self._pin_btn.pack(side=tk.RIGHT, padx=(0, 6), pady=12)
        self._refresh_pin_button(primary_color=primary_color, accent_color=accent_color)

        # 支持拖动窗口：拖动标题栏空白处
        def _start_drag(event) -> None:
            if not self.window:
                return
            self._drag_offset = (
                event.x_root - self.window.winfo_x(),
                event.y_root - self.window.winfo_y(),
            )

        def _on_drag(event) -> None:
            if not self.window or not self._drag_offset:
                return
            x = event.x_root - self._drag_offset[0]
            y = event.y_root - self._drag_offset[1]
            self.window.geometry(f"+{x}+{y}")

        def _end_drag(_event) -> None:
            self._drag_offset = None

        for w in (title_frame, title_left, title_label):
            w.bind("<ButtonPress-1>", _start_drag)
            w.bind("<B1-Motion>", _on_drag)
            w.bind("<ButtonRelease-1>", _end_drag)

        # 主内容区 - 增加圆角效果
        # 使用两层边框模拟圆角效果（外层粉色边框，内层白色内容）
        outer_frame = tk.Frame(self.window, bg=primary_color, padx=2, pady=2)
        outer_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        inner_window = tk.Frame(outer_frame, bg=bg_color)
        inner_window.pack(fill=tk.BOTH, expand=True)

        content_frame = tk.Frame(inner_window, bg=bg_color, padx=16, pady=14)
        content_frame.pack(fill=tk.BOTH, expand=True)

        card_frame = tk.Frame(
            content_frame,
            bg=card_color,
            highlightthickness=1,
            highlightbackground=border_color,
            highlightcolor=border_color,
        )
        card_frame.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(card_frame, bg=card_color, padx=14, pady=12)
        inner.pack(fill=tk.BOTH, expand=True)

        # 原文
        tk.Label(
            inner,
            text="原文：",
            bg=card_color,
            fg=text_color,
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w",
        ).pack(fill=tk.X)

        self._source_text_widget = tk.Text(
            inner,
            height=4,
            font=("Microsoft YaHei", 10),
            wrap=tk.WORD,
            bg="#FFFFFF",
            fg=text_color,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=border_color,
            highlightcolor=accent_color,
            padx=8,
            pady=6,
        )
        self._source_text_widget.pack(fill=tk.X, pady=(5, 10))
        self._source_text_widget.insert("1.0", self._original_text)

        # 目标语言选择
        lang_frame = tk.Frame(inner, bg=card_color)
        lang_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            lang_frame,
            text="目标语言：",
            bg=card_color,
            fg=text_color,
            font=("Microsoft YaHei", 10),
        ).pack(side=tk.LEFT)

        # 语言名称映射（显示用）
        self._lang_names = list(TRANSLATE_LANGUAGES.values())
        # 反向映射（名称 -> 代码）
        self._lang_code_map = {v: k for k, v in TRANSLATE_LANGUAGES.items()}

        # 获取当前配置的语言代码，转为显示名称
        current_lang_code = config.get("translate_target_lang", DEFAULT_TRANSLATE_LANG)
        current_lang_name = TRANSLATE_LANGUAGES.get(current_lang_code, "简体中文")

        self._target_lang_var = tk.StringVar(value=current_lang_name)
        lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self._target_lang_var,
            values=self._lang_names,
            state="readonly",
            font=("Microsoft YaHei", 9),
            width=12,
        )
        lang_combo.pack(side=tk.LEFT, padx=(10, 0))

        # 翻译按钮（缩小尺寸）
        translate_btn = tk.Button(
            inner,
            text="翻译",
            bg=primary_color,
            fg="white",
            font=("Microsoft YaHei", 10, "bold"),
            borderwidth=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._do_translate,
            activebackground="#FF85C1",
            activeforeground="white",
        )
        translate_btn.pack(fill=tk.X, pady=(0, 15))

        # 译文
        tk.Label(
            inner,
            text="译文：",
            bg=card_color,
            fg=text_color,
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w",
        ).pack(fill=tk.X)

        self._result_text_widget = tk.Text(
            inner,
            height=13,
            font=("Microsoft YaHei", 10),
            wrap=tk.WORD,
            bg="#FFFFFF",
            fg=text_color,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=border_color,
            highlightcolor=accent_color,
            padx=8,
            pady=6,
        )
        self._result_text_widget.pack(fill=tk.X, pady=(5, 10))

        # 底部按钮
        btn_frame = tk.Frame(inner, bg=card_color)
        btn_frame.pack(fill=tk.X)

        copy_btn = tk.Button(
            btn_frame,
            text="复制译文",
            bg=accent_color,
            fg="white",
            font=("Microsoft YaHei", 9, "bold"),
            borderwidth=0,
            padx=15,
            pady=6,
            cursor="hand2",
            command=self._copy_result,
            activebackground="#8BD7FF",
            activeforeground="white",
        )
        copy_btn.pack(side=tk.LEFT, padx=(0, 10))

        rerun_btn = tk.Button(
            btn_frame,
            text="重新翻译",
            bg="#F3F4F6",
            fg=text_color,
            font=("Microsoft YaHei", 9, "bold"),
            borderwidth=0,
            padx=15,
            pady=6,
            cursor="hand2",
            command=self._do_translate,
            activebackground="#E5E7EB",
            activeforeground=text_color,
        )
        rerun_btn.pack(side=tk.LEFT)

        # 翻译状态
        self._status_label = tk.Label(
            inner,
            text="",
            bg=card_color,
            fg=muted_text_color,
            font=("Microsoft YaHei", 9),
        )
        self._status_label.pack(pady=(10, 0))

    def _refresh_pin_button(self, primary_color: str, accent_color: str) -> None:
        """刷新置顶按钮显示状态"""
        if not self._pin_btn:
            return

        # 始终保持粉色主题，不使用蓝色
        if self._is_topmost:
            # 已固定状态 - 使用激活图标（保持粉色）
            if self._pin_icon_active:
                self._pin_btn.configure(
                    image=self._pin_icon_active,
                    bg=primary_color,
                    activebackground="#FF85C1",
                )
            else:
                self._pin_btn.configure(
                    text="\U0001f4cc", bg=primary_color, activebackground="#FF85C1"
                )
        else:
            # 未固定状态 - 使用普通图标（保持粉色）
            if self._pin_icon_normal:
                self._pin_btn.configure(
                    image=self._pin_icon_normal,
                    bg=primary_color,
                    activebackground="#FF85C1",
                )
            else:
                self._pin_btn.configure(
                    text="\U0001f4cc", bg=primary_color, activebackground="#FF85C1"
                )

    def _do_translate(self) -> None:
        """执行翻译"""
        source_text = self._source_text_widget.get("1.0", tk.END).strip()
        if not source_text:
            self._status_label.configure(text="请输入要翻译的文本")
            return

        # 将语言名称转换为语言代码
        lang_name = self._target_lang_var.get()
        target_lang = self._lang_code_map.get(lang_name, "zh")

        if not target_lang:
            target_lang = DEFAULT_TRANSLATE_LANG

        # 保存目标语言设置（保存代码）
        update_config(translate_target_lang=target_lang)

        # 显示翻译中状态
        self._status_label.configure(text="翻译中...")
        self._result_text_widget.delete("1.0", tk.END)

        def on_complete(result: str) -> None:
            self._translated_text = result
            self._result_text_widget.delete("1.0", tk.END)
            self._result_text_widget.insert("1.0", result)
            self._status_label.configure(text="翻译完成")

        def on_error(error: str) -> None:
            self._status_label.configure(text=error)
            messagebox.showerror("翻译错误", error)

        self.engine.translate(source_text, target_lang, on_complete, on_error)

    def _copy_result(self) -> None:
        """复制译文到剪贴板"""
        if not self._translated_text:
            self._status_label.configure(text="暂无译文可复制")
            return

        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(self._translated_text)
            self._status_label.configure(text="已复制到剪贴板")
        except Exception as e:
            self._status_label.configure(text=f"复制失败: {e}")

    def hide(self) -> None:
        """隐藏窗口"""
        if self.window:
            self.window.withdraw()
