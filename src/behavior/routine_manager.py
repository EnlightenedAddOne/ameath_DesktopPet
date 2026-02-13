"""作息提醒管理器（从 src/core/pet_core.py 拆分）"""

from __future__ import annotations

import random
from datetime import datetime
from typing import TYPE_CHECKING

from src.constants import REMINDERS, SLEEP_SPEED_MULTIPLIER, REMINDER_CHANCE

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class RoutineManager:
    """智能作息系统管理器

    为减少改动，作息相关状态字段仍保存在 app 上（例如
    `_current_time_period/_last_reminder_time/_is_sleeping/...`）。
    """

    def __init__(self, app: "DesktopPet") -> None:
        self.app = app

    def init_state(self) -> None:
        """初始化作息相关状态"""
        self.app._current_time_period = self.get_time_period()
        self.app._last_reminder_time = {}
        self.app._is_sleeping = False
        self.app._original_speed_x = self.app._speed_x
        self.app._original_speed_y = self.app._speed_y

    def get_time_period(self) -> str:
        """获取当前时间段"""
        from src.constants import (
            TIME_AFTERNOON_START,
            TIME_EVENING_START,
            TIME_MORNING_START,
            TIME_NIGHT_START,
            TIME_NOON_START,
            TIME_SLEEP_START,
        )

        hour = datetime.now().hour
        if TIME_SLEEP_START <= hour < TIME_MORNING_START:
            return "sleep"
        if TIME_MORNING_START <= hour < TIME_NOON_START:
            return "morning"
        if TIME_NOON_START <= hour < TIME_AFTERNOON_START:
            return "noon"
        if TIME_AFTERNOON_START <= hour < TIME_EVENING_START:
            return "afternoon"
        if TIME_EVENING_START <= hour < TIME_NIGHT_START:
            return "evening"
        return "night"

    def tick(self) -> None:
        """检查作息状态（每分钟调用一次）"""
        self.app._routine_after_id = None
        current_period = self.get_time_period()
        if current_period != self.app._current_time_period:
            self.app._current_time_period = current_period

            from src.ai.emys_character import EMYS_RESPONSES

            if current_period == "sleep":
                self.app._is_sleeping = True
                self.app._speed_x = int(
                    self.app._original_speed_x * SLEEP_SPEED_MULTIPLIER
                )
                self.app._speed_y = int(
                    self.app._original_speed_y * SLEEP_SPEED_MULTIPLIER
                )
                text = random.choice(EMYS_RESPONSES["greeting_night"])
                self.app.speech_bubble.show(text, duration=5000)
            elif self.app._is_sleeping:
                self.app._is_sleeping = False
                self.app._speed_x = self.app._original_speed_x
                self.app._speed_y = self.app._original_speed_y
                text = random.choice(EMYS_RESPONSES["greeting_morning"])
                self.app.speech_bubble.show(text, duration=5000)

        # 定期问候语（低概率触发）
        # AI对话模式下不触发，音乐播放模式下会被自动阻止
        if (
            not self.app._is_sleeping
            and not self.app.is_paused
            and not self.app.is_ai_chat_panel_visible()
            and random.random() < REMINDER_CHANCE
        ):
            # 60%概率触发提醒，40%概率触发闲聊
            if random.random() < 0.6:
                # 触发提醒
                current_time = datetime.now()
                for reminder_type, config in REMINDERS.items():
                    last_time = self.app._last_reminder_time.get(reminder_type)
                    if (
                        last_time is None
                        or (current_time - last_time).total_seconds() / 60
                        >= config["interval"]
                    ):
                        message = random.choice(config["messages"])
                        self.app.speech_bubble.show(message, duration=5000)
                        self.app._last_reminder_time[reminder_type] = current_time
                        break
            else:
                # 触发闲聊 random_chat
                from src.ai.emys_character import EMYS_RESPONSES

                message = random.choice(EMYS_RESPONSES["random_chat"])
                self.app.speech_bubble.show(message, duration=5000)

        self.app._routine_after_id = self.app.root.after(60000, self.tick)
