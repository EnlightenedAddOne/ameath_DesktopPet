"""番茄钟逻辑（从 src/pet_core.py 拆分）"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.constants import POMODORO_REST_MINUTES, POMODORO_WORK_MINUTES

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class PomodoroManager:
    """番茄钟管理器

    说明：为了保持现有对外行为不变，番茄钟的状态字段仍保存在 app 上（例如
    `_pomodoro_enabled/_pomodoro_remaining/...`），此管理器负责读写这些字段。
    """

    def __init__(self, app: "DesktopPet") -> None:
        self.app = app

    def toggle(self) -> None:
        """开始/停止番茄钟"""
        if self.app._pomodoro_enabled:
            self._stop()
        else:
            self._start()

    def reset(self) -> None:
        """重置番茄钟"""
        if not self.app._pomodoro_enabled:
            return
        self.app._pomodoro_phase = "work"
        self.app._pomodoro_total = POMODORO_WORK_MINUTES * 60
        self.app._pomodoro_remaining = self.app._pomodoro_total
        self.app._pomodoro_paused = False
        self._update_indicator()
        self._schedule_tick()
        self.app.speech_bubble.show("番茄钟已重置，开始专注~", duration=2500)

    def _start(self) -> None:
        """启动番茄钟"""
        self.app._pomodoro_enabled = True
        self.app._pomodoro_phase = "work"
        self.app._pomodoro_total = POMODORO_WORK_MINUTES * 60
        self.app._pomodoro_remaining = self.app._pomodoro_total
        self.app._pomodoro_paused = False
        self._update_indicator()
        self._schedule_tick()
        self.app.speech_bubble.show("番茄钟开始：专注 25 分钟", duration=3000)

    def _stop(self) -> None:
        """停止番茄钟"""
        self.app._pomodoro_enabled = False
        self.app._pomodoro_paused = False
        self.app._pomodoro_remaining = 0
        self.app._pomodoro_total = 0
        if self.app._pomodoro_after_id:
            self.app.root.after_cancel(self.app._pomodoro_after_id)
            self.app._pomodoro_after_id = None
        self.app.pomodoro_indicator.hide()
        self.app.speech_bubble.show("番茄钟已停止", duration=2000)

    def _schedule_tick(self) -> None:
        """调度番茄钟计时"""
        if self.app._pomodoro_after_id:
            self.app.root.after_cancel(self.app._pomodoro_after_id)
            self.app._pomodoro_after_id = None
        if not self.app._pomodoro_enabled or self.app._pomodoro_paused:
            return
        self.app._pomodoro_after_id = self.app.root.after(1000, self._tick)

    def _tick(self) -> None:
        """番茄钟计时回调"""
        self.app._pomodoro_after_id = None
        if not self.app._pomodoro_enabled or self.app._pomodoro_paused:
            return
        self.app._pomodoro_remaining -= 1
        if self.app._pomodoro_remaining <= 0:
            self._switch_phase()
        self._update_indicator()
        self._schedule_tick()

    def _switch_phase(self) -> None:
        """切换番茄钟阶段"""
        if self.app._pomodoro_phase == "work":
            self.app._pomodoro_phase = "rest"
            self.app._pomodoro_total = POMODORO_REST_MINUTES * 60
            self.app._pomodoro_remaining = self.app._pomodoro_total
            self.app.speech_bubble.show("休息 5 分钟，放松一下~", duration=3000)
            self.app._switch_to_idle()
        else:
            self.app._pomodoro_phase = "work"
            self.app._pomodoro_total = POMODORO_WORK_MINUTES * 60
            self.app._pomodoro_remaining = self.app._pomodoro_total
            self.app.speech_bubble.show("专注时间到，继续加油！", duration=3000)
        self._update_indicator()

    def _update_indicator(self) -> None:
        """更新番茄钟进度显示"""
        if not self.app._pomodoro_enabled:
            self.app.pomodoro_indicator.hide()
            return

        phase_text = "专注" if self.app._pomodoro_phase == "work" else "休息"
        self.app.pomodoro_indicator.update_progress(
            phase_text, self.app._pomodoro_remaining, self.app._pomodoro_total
        )
