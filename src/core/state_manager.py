"""状态管理（从 src/core/pet_core.py 拆分）"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from src.constants import (
    BEHAVIOR_MODE_ACTIVE,
    MOTION_WANDER,
    SPEED_X,
    SPEED_Y,
)
from src.ui.music_panel import MusicPanel
from src.ui.pomodoro_indicator import PomodoroIndicator
from src.ui.quick_menu import QuickMenu
from src.ui.speech_bubble import SpeechBubble

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class StateManager:
    """状态管理器

    说明：为了降低拆分风险，状态字段仍保存在 app 上；此管理器负责集中初始化。
    """

    def __init__(self, app: "DesktopPet") -> None:
        self.app = app

    def init_state(self) -> None:
        """初始化状态变量"""
        app = self.app

        # 屏幕尺寸（必须先初始化）
        app.screen_w = app.root.winfo_screenwidth()
        app.screen_h = app.root.winfo_screenheight()

        # 运动状态
        app.is_moving = True
        app.is_paused = False
        app.moving_right = True
        app.motion_state = MOTION_WANDER
        app._pre_music_motion_state = app.motion_state
        app._pre_music_is_moving = app.is_moving

        # 动画状态
        app.frame_index = 0
        app._last_frames: Optional[list] = None
        app._last_delays: Optional[list] = None
        app._music_playing = False
        app._music_paused = False
        app._music_playlist = []
        app._music_index = 0
        app._music_start_time = 0.0
        app._music_pause_start = 0.0
        app._music_paused_total = 0.0
        app._music_length_cache: dict[str, float] = {}

        # 拖动状态
        app.dragging = False
        app.drag_start_x = 0
        app.drag_start_y = 0
        app._pre_drag_frames = None
        app._pre_drag_delays = None
        app._pending_drag = False
        app._mouse_down_x = 0
        app._mouse_down_y = 0
        app._drag_started = False

        # 目标点
        app.motion.init_state()

        # 速度
        app.vx = SPEED_X
        app.vy = SPEED_Y
        app._speed_x = SPEED_X
        app._speed_y = SPEED_Y

        # 性能优化缓存
        app._last_mouse: Tuple[int, int] = (0, 0)
        app._last_pos: Optional[Tuple[int, int]] = None
        app._move_tick = 0
        app._jitter_x = 0.0
        app._jitter_y = 0.0

        # 待机动画轮换
        app._idle_cycle = []
        app._last_idle_index: Optional[int] = None

        # 互动系统
        app.speech_bubble = SpeechBubble(app)
        app.quick_menu = QuickMenu(app)
        app.pomodoro_indicator = PomodoroIndicator(app)
        app.music_panel = MusicPanel(app)
        app._last_click_time = 0
        app._click_count = 0
        app._is_showing_greeting = False

        # 智能作息系统
        app.routine.init_state()

        # 行为模式参数（运行时可调整）
        app._behavior_follow_override: Optional[bool] = None
        app._behavior_stop_chance: Optional[float] = None
        app._behavior_rest_chance: Optional[float] = None
        app._behavior_target_min: Optional[int] = None
        app._behavior_target_max: Optional[int] = None
        app._behavior_speed_mul = 1.0
        app._behavior_min_move_ticks = 0

        app._move_after_id = None
        app._move_ticks_since_move = 0

        # after 任务句柄（用于退出时取消，避免 TclError）
        app._animate_after_id = None
        app._routine_after_id = None
        app._topmost_after_id = None
        app._quit_after_id = None
        app._music_after_id = None

        # 番茄钟状态
        app._pomodoro_enabled = False
        app._pomodoro_phase = "work"
        app._pomodoro_remaining = 0
        app._pomodoro_paused = False
        app._pomodoro_after_id = None
        app._pomodoro_total = 0

        app._idle_after_id = None

        # 应用行为模式（读取自配置）
        if getattr(app, "behavior_mode", None) is None:
            app.behavior_mode = BEHAVIOR_MODE_ACTIVE
        app.motion.apply_behavior_mode(app.behavior_mode)
