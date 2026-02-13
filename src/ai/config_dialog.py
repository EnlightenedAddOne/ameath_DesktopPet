"""AI配置对话框模块"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet

from src.config import load_config, update_config
from src.constants import (
    AI_DEFAULT_MODELS,
    AI_PROVIDER_CLAUDE,
    AI_PROVIDER_DEEPSEEK,
    AI_PROVIDER_OPENAI,
)


class AIConfigDialog:
    """AI配置对话框"""

    def __init__(self, app: DesktopPet):
        self.app = app
        self.dialog: tk.Toplevel | None = None
        self.config_vars: dict = {}

    def show(self) -> None:
        """显示配置对话框"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            return

        self._create_dialog()

    def _create_dialog(self) -> None:
        """创建对话框"""
        self.dialog = tk.Toplevel(self.app.root)
        self.dialog.title("AI助手配置")
        self.dialog.geometry("480x600")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.app.root)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 480) // 2
        y = (self.dialog.winfo_screenheight() - 600) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # 加载当前配置
        config = load_config()

        # 创建界面
        self._create_widgets(config)

    def _create_widgets(self, config: dict) -> None:
        """创建界面组件"""
        # 主容器
        main_container = ttk.Frame(self.dialog)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 上方可滚动区域
        scroll_container = ttk.Frame(main_container)
        scroll_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(15, 5))

        # Canvas和滚动条
        canvas = tk.Canvas(scroll_container, highlightthickness=0, height=450)
        scrollbar = ttk.Scrollbar(
            scroll_container, orient="vertical", command=canvas.yview
        )
        content_frame = ttk.Frame(canvas, padding="5")

        content_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=content_frame, anchor="nw", width=420)
        canvas.configure(yscrollcommand=scrollbar.set)

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        content_frame.bind("<MouseWheel>", _on_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 启用AI
        self.config_vars["enabled"] = tk.BooleanVar(
            value=config.get("ai_enabled", False)
        )
        ttk.Checkbutton(
            content_frame,
            text="启用AI对话功能",
            variable=self.config_vars["enabled"],
        ).pack(anchor=tk.W, pady=(0, 10))

        # 分隔线
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        # API提供商
        ttk.Label(content_frame, text="AI服务商:").pack(anchor=tk.W, pady=(5, 3))
        self.config_vars["provider"] = tk.StringVar(
            value=config.get("ai_provider", AI_PROVIDER_DEEPSEEK)
        )
        provider_combo = ttk.Combobox(
            content_frame,
            textvariable=self.config_vars["provider"],
            values=[AI_PROVIDER_DEEPSEEK, AI_PROVIDER_OPENAI, AI_PROVIDER_CLAUDE],
            state="readonly",
        )
        provider_combo.pack(fill=tk.X, pady=(0, 8))
        provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        # API密钥
        ttk.Label(content_frame, text="API密钥:").pack(anchor=tk.W, pady=(5, 3))
        api_key_frame = ttk.Frame(content_frame)
        api_key_frame.pack(fill=tk.X, pady=(0, 8))

        self.config_vars["api_key"] = tk.StringVar(value=config.get("ai_api_key", ""))
        api_key_entry = ttk.Entry(
            api_key_frame,
            textvariable=self.config_vars["api_key"],
            show="*",
        )
        api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 显示/隐藏密码
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            api_key_frame,
            text="显示",
            variable=self.show_key_var,
            command=lambda: api_key_entry.config(
                show="" if self.show_key_var.get() else "*"
            ),
        ).pack(side=tk.RIGHT, padx=(5, 0))

        # 模型选择
        ttk.Label(content_frame, text="模型:").pack(anchor=tk.W, pady=(5, 3))
        self.config_vars["model"] = tk.StringVar(
            value=config.get("ai_model", "deepseek-chat")
        )
        self.model_combo = ttk.Combobox(
            content_frame,
            textvariable=self.config_vars["model"],
            values=list(AI_DEFAULT_MODELS.values()),
        )
        self.model_combo.pack(fill=tk.X, pady=(0, 8))

        # Base URL（可选）
        ttk.Label(content_frame, text="Base URL (可选，留空使用默认):").pack(
            anchor=tk.W, pady=(5, 3)
        )
        self.config_vars["base_url"] = tk.StringVar(value=config.get("ai_base_url", ""))
        ttk.Entry(content_frame, textvariable=self.config_vars["base_url"]).pack(
            fill=tk.X, pady=(0, 8)
        )

        # 性格选择
        ttk.Label(content_frame, text="选择性格:").pack(anchor=tk.W, pady=(5, 3))
        self.config_vars["personality"] = tk.StringVar(
            value=config.get("ai_personality", "emys")
        )
        personality_combo = ttk.Combobox(
            content_frame,
            textvariable=self.config_vars["personality"],
            values=["emys", "default", "helpful", "cute", "tsundere"],
            state="readonly",
        )
        personality_combo.pack(fill=tk.X, pady=(0, 5))

        # 性格说明
        personality_desc = {
            "emys": "爱弥斯（飞行雪绒）- 鸣潮角色，粉色头发电子幽灵少女",
            "default": "活泼友善，带可爱语气",
            "helpful": "专业准确，实用建议",
            "cute": "超级可爱，喜欢颜文字",
            "tsundere": "傲娇属性，外冷内热",
        }
        self.desc_label = ttk.Label(
            content_frame,
            text=personality_desc.get(self.config_vars["personality"].get(), ""),
            foreground="gray",
            font=("Microsoft YaHei", 9),
            wraplength=400,
        )
        self.desc_label.pack(anchor=tk.W, pady=(0, 10))
        personality_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self.desc_label.config(
                text=personality_desc.get(self.config_vars["personality"].get(), "")
            ),
        )

        # 下方固定按钮区域
        button_frame = ttk.Frame(main_container, padding="10")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # 分隔线
        ttk.Separator(main_container, orient=tk.HORIZONTAL).pack(
            fill=tk.X, side=tk.BOTTOM
        )

        ttk.Button(
            button_frame,
            text="保存配置",
            command=self._save_config,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            button_frame,
            text="测试连接",
            command=self._test_connection,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            button_frame,
            text="取消",
            command=self.dialog.destroy,
        ).pack(side=tk.RIGHT)

    def _on_provider_change(self, event=None) -> None:
        """服务商改变时更新默认模型"""
        provider = self.config_vars["provider"].get()
        default_model = AI_DEFAULT_MODELS.get(provider, "deepseek-chat")
        self.config_vars["model"].set(default_model)
        self.model_combo.set(default_model)

    def _save_config(self) -> None:
        """保存配置"""
        try:
            update_config(
                ai_enabled=self.config_vars["enabled"].get(),
                ai_provider=self.config_vars["provider"].get(),
                ai_api_key=self.config_vars["api_key"].get().strip(),
                ai_model=self.config_vars["model"].get().strip(),
                ai_base_url=self.config_vars["base_url"].get().strip(),
                ai_personality=self.config_vars["personality"].get(),
            )

            # 重新加载AI引擎配置
            if hasattr(self.app, "ai_chat") and self.app.ai_chat:
                self.app.ai_chat.reload_config()

            messagebox.showinfo("成功", "配置已保存！", parent=self.dialog)
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}", parent=self.dialog)

    def _test_connection(self) -> None:
        """测试API连接"""
        import threading

        api_key = self.config_vars["api_key"].get().strip()
        provider = self.config_vars["provider"].get()
        model = self.config_vars["model"].get().strip()
        base_url = self.config_vars["base_url"].get().strip()

        if not api_key:
            messagebox.showwarning("提示", "请先输入API密钥", parent=self.dialog)
            return

        # 设置默认base_url
        if not base_url:
            if provider == AI_PROVIDER_OPENAI:
                base_url = "https://api.openai.com/v1"
            elif provider == AI_PROVIDER_CLAUDE:
                base_url = "https://api.anthropic.com/v1"
            elif provider == AI_PROVIDER_DEEPSEEK:
                base_url = "https://api.deepseek.com/v1"

        def _test():
            try:
                import requests

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                }

                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "你好"}],
                    "max_tokens": 10,
                }

                response = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=15,
                )

                if response.status_code == 200:
                    self.dialog.after(
                        0,
                        lambda: messagebox.showinfo(
                            "成功",
                            "连接测试成功！AI功能可以正常使用~",
                            parent=self.dialog,
                        ),
                    )
                elif response.status_code == 401:
                    self.dialog.after(
                        0,
                        lambda: messagebox.showerror(
                            "错误",
                            "API密钥无效，请检查密钥是否正确",
                            parent=self.dialog,
                        ),
                    )
                else:
                    error_text = response.text[:200]
                    self.dialog.after(
                        0,
                        lambda: messagebox.showerror(
                            "错误",
                            f"连接失败 (状态码: {response.status_code}):\n{error_text}",
                            parent=self.dialog,
                        ),
                    )

            except Exception as e:
                self.dialog.after(
                    0,
                    lambda: messagebox.showerror(
                        "错误", f"测试连接时出错: {str(e)}", parent=self.dialog
                    ),
                )

        # 显示测试中的提示
        test_window = tk.Toplevel(self.dialog)
        test_window.title("测试中")
        test_window.geometry("200x80")
        test_window.transient(self.dialog)
        test_window.grab_set()
        test_window.resizable(False, False)
        ttk.Label(test_window, text="正在测试连接...").pack(expand=True)

        def run_test_and_close():
            _test()
            test_window.destroy()

        threading.Thread(target=run_test_and_close, daemon=True).start()
