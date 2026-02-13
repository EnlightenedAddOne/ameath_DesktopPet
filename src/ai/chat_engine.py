"""AI对话引擎模块 - 支持多种LLM服务"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet

import requests

from src.config import load_config
from src.constants import (
    AI_DEFAULT_BASE_URLS,
    AI_PROVIDER_DOUBAO,
    AI_PROVIDER_GLM,
    AI_PROVIDER_KIMI,
    AI_PROVIDER_OPENAI,
    AI_PROVIDER_QWEN,
    AI_PROVIDER_DEEPSEEK,
)
from src.ai.emys_character import (
    get_emys_personality,
    EMYS_QUICK_REPLIES,
)


@dataclass
class ChatMessage:
    """聊天消息"""

    role: str  # "user" 或 "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


class ChatHistory:
    """对话历史管理"""

    def __init__(self, max_messages: int = 20):
        self.messages: List[ChatMessage] = []
        self.max_messages = max_messages

    def add_message(self, role: str, content: str) -> None:
        """添加消息"""
        self.messages.append(ChatMessage(role=role, content=content))
        # 保持历史记录长度
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def get_formatted_history(self) -> List[Dict[str, str]]:
        """获取格式化的历史记录用于API调用"""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

    def clear(self) -> None:
        """清空历史"""
        self.messages.clear()

    def get_last_context(self, context_size: int = 5) -> List[Dict[str, str]]:
        """获取最近的对话上下文"""
        recent = (
            self.messages[-context_size:]
            if len(self.messages) > context_size
            else self.messages
        )
        return [{"role": msg.role, "content": msg.content} for msg in recent]


class AIChatEngine:
    """AI对话引擎"""

    # 预设角色设定
    PERSONALITIES = {
        "aemeath": "爱弥斯（Aemeath）- 桌面宠物",  # 桌面宠物人设
        "default": "阿米 - 默认可爱助手",
        "helpful": "专业助手模式",
        "cute": "超萌模式",
        "tsundere": "傲娇模式",
    }

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        if self.current_personality == "aemeath":
            return get_emys_personality()
        elif self.current_personality == "helpful":
            return "你是一个有帮助的桌面助手，名叫小爱。你专业、准确，会给出实用的建议。回答简洁明了。"
        elif self.current_personality == "cute":
            return "你是一个超级可爱的桌面宠物，名叫小爱。你说话带着萌系语气，喜欢用颜文字和emoji。回答简短可爱。"
        elif self.current_personality == "tsundere":
            return "你是一个傲娇的桌面宠物，名叫小爱。你表面冷淡但内心关心用户，说话带点傲娇语气。"
        else:
            return "你是一个可爱的桌面宠物助手，名叫小爱。你性格活泼、友善，喜欢和用户聊天。回答要简短（50字以内），带点可爱语气。"

    def __init__(self, app: DesktopPet):
        self.app = app
        self.history = ChatHistory(max_messages=20)
        self.is_processing = False
        self.current_personality = "aemeath"  # 默认使用爱弥斯人设
        self._load_config()

    def _load_config(self) -> None:
        """加载AI配置"""
        config = load_config()
        self.api_key = config.get("ai_api_key", "")
        self.provider = config.get("ai_provider", AI_PROVIDER_DEEPSEEK)
        self.model = config.get("ai_model", "deepseek-chat")
        self.base_url = config.get("ai_base_url", "")
        self.enabled = config.get("ai_enabled", False)
        self.personality = config.get("ai_personality", "aemeath")
        self.current_personality = (
            self.personality if self.personality in self.PERSONALITIES else "aemeath"
        )

        # 设置默认base_url
        if not self.base_url:
            self.base_url = AI_DEFAULT_BASE_URLS.get(self.provider, "")

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.enabled and self.api_key and self.base_url)

    def send_message(
        self,
        message: str,
        on_response: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """发送消息并获取回复

        Args:
            message: 用户消息
            on_response: 成功回调，接收回复内容
            on_error: 错误回调，接收错误信息
        """
        if self.is_processing:
            on_error("正在处理上一条消息，请稍等~")
            return

        if not self.is_configured():
            on_error("AI功能未配置，请先设置API密钥哦~")
            return

        self.is_processing = True

        # 添加到历史
        self.history.add_message("user", message)

        # 在后台线程调用API
        def _call_api():
            try:
                response = self._call_llm_api(message)
                self.is_processing = False
                if response:
                    self.history.add_message("assistant", response)
                    # 在主线程回调
                    self.app.root.after(0, lambda: on_response(response))
                else:
                    self.app.root.after(
                        0, lambda: on_error("获取回复失败，请稍后再试~")
                    )
            except Exception as e:
                self.is_processing = False
                error_msg = str(e)
                print(f"AI API调用错误: {error_msg}")
                self.app.root.after(0, lambda: on_error(f"出错了: {error_msg[:50]}..."))

        threading.Thread(target=_call_api, daemon=True).start()

    def _call_llm_api(self, message: str) -> Optional[str]:
        """调用LLM API"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            # 构建消息
            system_prompt = self._get_system_prompt()
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.history.get_last_context(context_size=5))

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 150,
                "temperature": 0.7,
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = (
                        data["choices"][0].get("message", {}).get("content", "").strip()
                    )
                    return content
                else:
                    print(f"API响应格式异常: {data}")
                    return None
            else:
                error_text = response.text
                print(f"API错误 {response.status_code}: {error_text}")
                return None

        except requests.exceptions.Timeout:
            print("API请求超时")
            return None
        except requests.exceptions.RequestException as e:
            print(f"API请求错误: {e}")
            return None
        except Exception as e:
            print(f"API调用异常: {e}")
            return None

    def clear_history(self) -> None:
        """清空对话历史"""
        self.history.clear()

    def reload_config(self) -> None:
        """重新加载配置"""
        self._load_config()

    def set_personality(self, personality: str) -> bool:
        """设置性格"""
        if personality in self.PERSONALITIES:
            self.current_personality = personality
            return True
        return False

    def get_available_personalities(self) -> List[str]:
        """获取可用性格列表"""
        return list(self.PERSONALITIES.keys())


# 快捷提问模板
QUICK_QUESTIONS = [
    "讲个笑话",
    "今天星期几？",
    "给我点建议",
    "我累了",
    "谢谢你",
]

# 爱弥斯专属快捷问题
EMYS_QUICK_QUESTIONS = [
    "讲个笑话",
    "今天星期几？",
    "给我点建议",
    "我累了",
]


class QuickChatManager:
    """快捷聊天管理"""

    def __init__(self, chat_engine: AIChatEngine):
        self.chat_engine = chat_engine
        # 根据当前人设选择问题列表
        if chat_engine.current_personality == "aemeath":
            self.questions = EMYS_QUICK_QUESTIONS.copy()
        else:
            self.questions = QUICK_QUESTIONS.copy()

    def get_random_question(self) -> str:
        """获取随机快捷问题"""
        import random

        return random.choice(self.questions)

    def get_all_questions(self) -> List[str]:
        """获取所有快捷问题"""
        return self.questions.copy()

    def get_emys_quick_reply(self, question: str) -> str:
        """获取爱弥斯的快捷回复（本地预设，不调用API）"""
        from src.ai.emys_character import get_quick_reply

        if self.chat_engine.current_personality == "aemeath":
            return get_quick_reply(question)
        return ""
