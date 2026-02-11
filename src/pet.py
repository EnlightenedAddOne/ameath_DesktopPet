"""桌面宠物主类模块"""

from __future__ import annotations

import ctypes
import random
import tkinter as tk
from typing import Any, Optional, Tuple

import pygame
from PIL import Image, ImageTk

from src.animations import (
    flip_frames,
    load_all_animations,
    load_gif_frames,
    load_gif_frames_raw,
)
from src.config import load_config, save_config, update_config
from src.constants import (
    BEHAVIOR_MODE_ACTIVE,
    BEHAVIOR_MODE_CLINGY,
    BEHAVIOR_MODE_QUIET,
    DEFAULT_SCALE_INDEX,
    DEFAULT_TRANSPARENCY_INDEX,
    FOLLOW_DISTANCE,
    FOLLOW_START_DIST,
    FOLLOW_STOP_DIST,
    INERTIA_FACTOR,
    INTENT_FACTOR,
    JITTER,
    JITTER_INTERVAL,
    MOTION_CURIOUS,
    MOTION_FOLLOW,
    MOTION_REST,
    MOTION_WANDER,
    MOVE_INTERVAL,
    OUTSIDE_TARGET_CHANCE,
    POMODORO_REST_MINUTES,
    POMODORO_WORK_MINUTES,
    REST_CHANCE,
    REST_DISTANCE,
    REST_DURATION_MAX,
    REST_DURATION_MIN,
    RESPAWN_MARGIN,
    SCALE_OPTIONS,
    SPEED_CURIOUS,
    SPEED_FOLLOW,
    SPEED_WANDER,
    SPEED_X,
    SPEED_Y,
    STOP_CHANCE,
    STOP_DURATION_MAX,
    STOP_DURATION_MIN,
    TARGET_CHANGE_MAX,
    TARGET_CHANGE_MIN,
    TRANSPARENCY_OPTIONS,
    TRANSPARENT_COLOR,
)
from src.quick_menu import QuickMenu
from src.pomodoro_indicator import PomodoroIndicator
from src.speech_bubble import SpeechBubble
from src.startup import check_and_fix_startup, set_auto_startup
from src.system import get_window_handle, set_click_through, set_window_topmost
from src.utils import resource_path


class DesktopPet:
    """桌面宠物主类"""

    # 类变量用于系统托盘
    tray_icon: Any = None

    def __init__(self, root: tk.Tk):
        """初始化桌面宠物

        Args:
            root: tkinter 根窗口
        """
        self.root = root
        self._request_quit = False
        self._animation_cache: dict[int, dict[str, Any]] = {}
        self._raw_gif_cache: dict[str, Tuple[list, list]] = {}
        self._raw_gif_cache_enabled = False
        self._resizing = False

        # 初始化窗口
        self._init_window()

        # 加载配置
        self._load_config()

        # 检查开机自启
        check_and_fix_startup()

        # 加载动画资源
        self._load_animations()

        # 初始化状态
        self._init_state()

        # 预加载音乐原始帧，避免切换倍率时重复解码
        self._preload_raw_gifs()

        # 绑定事件
        self._bind_events()

        # 启动循环
        self._start_loops()

    def _init_window(self) -> None:
        """初始化窗口"""
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.config(bg=TRANSPARENT_COLOR)
        self.root.attributes("-transparentcolor", TRANSPARENT_COLOR)

        # 创建标签
        self.label = tk.Label(self.root, bg=TRANSPARENT_COLOR, bd=0)
        self.label.pack()

    def _load_config(self) -> None:
        """加载配置"""
        config = load_config()

        self.scale_index = config.get("scale_index", DEFAULT_SCALE_INDEX)
        self.scale_options = SCALE_OPTIONS
        self.transparency_index = config.get(
            "transparency_index", DEFAULT_TRANSPARENCY_INDEX
        )
        self.auto_startup = config.get("auto_startup", False)
        self.click_through = config.get("click_through", True)
        self.follow_mouse = config.get("follow_mouse", False)
        self.behavior_mode = config.get("behavior_mode", BEHAVIOR_MODE_ACTIVE)
        self.scale = SCALE_OPTIONS[self.scale_index]

        # 应用透明度
        self.set_transparency(self.transparency_index, persist=False)
        # 应用鼠标穿透
        self.root.update_idletasks()
        self.hwnd = get_window_handle(self.root)
        if self.hwnd:
            set_click_through(self.hwnd, self.click_through)

    def _load_animations(self) -> None:
        """加载动画资源"""
        cache_key = self.scale_index
        cached = self._animation_cache.get(cache_key)
        if cached:
            self.move_frames = cached["move_frames"]
            self.move_delays = cached["move_delays"]
            self.move_pil_frames = []
            self.move_frames_left = cached["move_frames_left"]
            self.idle_gifs = cached["idle_gifs"]
            self.drag_frames = cached["drag_frames"]
            self.drag_delays = cached["drag_delays"]
            self.music_frames = cached["music_frames"]
            self.music_delays = cached["music_delays"]

            self.current_frames = self.move_frames
            self.current_delays = self.move_delays

            if self.current_frames:
                self.w = self.current_frames[0].width()
                self.h = self.current_frames[0].height()
            else:
                self.w, self.h = 100, 100

            if hasattr(self, "x") and hasattr(self, "y"):
                self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")
            else:
                self.x = 200
                self.y = 200
                self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
            self.root.update_idletasks()
            return

        # 移动动画
        move_result = load_gif_frames("move.gif", self.scale)
        self.move_frames, self.move_delays, move_pil_frames = move_result
        self.move_frames_left = flip_frames(move_pil_frames)
        move_pil_frames.clear()
        base_size = None
        if self.move_frames:
            base_size = (self.move_frames[0].width(), self.move_frames[0].height())

        # 待机动画
        self.idle_gifs = []
        for i in range(1, 5):
            idle_frames = load_gif_frames(f"idle{i}.gif", self.scale)
            if idle_frames[0]:
                self.idle_gifs.append((idle_frames[0], idle_frames[1]))

        # 拖动动画
        drag_result = load_gif_frames("drag.gif", self.scale)
        self.drag_frames, self.drag_delays, _ = drag_result

        # 音乐动画（延迟加载）
        self.music_frames = []
        self.music_delays = []
        if getattr(self, "_music_playing", False):
            self._ensure_music_frames()

        # 设置当前动画
        self.current_frames = self.move_frames
        self.current_delays = self.move_delays

        # 窗口大小
        if self.current_frames:
            self.w = self.current_frames[0].width()
            self.h = self.current_frames[0].height()
        else:
            self.w, self.h = 100, 100

        # 初始位置
        if hasattr(self, "x") and hasattr(self, "y"):
            self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")
        else:
            self.x = 200
            self.y = 200
            self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        self.root.update_idletasks()

        self._prune_animation_cache(cache_key)
        self._animation_cache[cache_key] = {
            "move_frames": self.move_frames,
            "move_delays": self.move_delays,
            "move_pil_frames": [],
            "move_frames_left": self.move_frames_left,
            "idle_gifs": self.idle_gifs,
            "drag_frames": self.drag_frames,
            "drag_delays": self.drag_delays,
            "music_frames": self.music_frames,
            "music_delays": self.music_delays,
        }

        if getattr(self, "_music_playing", False):
            self._ensure_music_frames()
            cache_entry = self._animation_cache.get(cache_key)
            if cache_entry is not None:
                cache_entry["music_frames"] = self.music_frames
                cache_entry["music_delays"] = self.music_delays

    def _init_state(self) -> None:
        """初始化状态变量"""
        # 屏幕尺寸（必须先初始化）
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # 运动状态
        self.is_moving = True
        self.is_paused = False
        self.moving_right = True
        self.motion_state = MOTION_WANDER
        self._pre_music_motion_state = self.motion_state
        self._pre_music_is_moving = self.is_moving

        # 动画状态
        self.frame_index = 0
        self._last_frames: Optional[list] = None
        self._last_delays: Optional[list] = None
        self._music_playing = False
        self._music_playlist = []
        self._music_index = 0

        # 拖动状态
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self._pre_drag_frames = None
        self._pre_drag_delays = None
        self._pending_drag = False
        self._mouse_down_x = 0
        self._mouse_down_y = 0
        self._drag_started = False

        # 目标点
        self.target_x, self.target_y = self._get_random_target()
        self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)
        self.rest_timer = 0

        # 速度
        self.vx = SPEED_X
        self.vy = SPEED_Y

        # 性能优化缓存
        self._last_mouse: Tuple[int, int] = (0, 0)
        self._last_pos: Optional[Tuple[int, int]] = None
        self._move_tick = 0
        self._jitter_x = 0.0
        self._jitter_y = 0.0

        # 待机动画轮换
        self._idle_cycle = []
        self._last_idle_index: Optional[int] = None

        # 互动系统
        self.speech_bubble = SpeechBubble(self)
        self.quick_menu = QuickMenu(self)
        self.pomodoro_indicator = PomodoroIndicator(self)
        self._last_click_time = 0
        self._click_count = 0
        self._is_showing_greeting = False

        # 智能作息系统
        from datetime import datetime

        self._current_time_period = self._get_time_period()
        self._last_reminder_time = {}
        self._is_sleeping = False
        self._original_speed_x = SPEED_X
        self._original_speed_y = SPEED_Y

        # 行为模式参数（运行时可调整）
        self._behavior_follow_override: Optional[bool] = None
        self._behavior_stop_chance: Optional[float] = None
        self._behavior_rest_chance: Optional[float] = None
        self._behavior_target_min: Optional[int] = None
        self._behavior_target_max: Optional[int] = None
        self._behavior_speed_mul: float = 1.0
        self._behavior_min_move_ticks: int = 0

        self._move_after_id: Optional[str] = None
        self._move_ticks_since_move = 0

        # 番茄钟状态
        self._pomodoro_enabled = False
        self._pomodoro_phase = "work"
        self._pomodoro_remaining = 0
        self._pomodoro_paused = False
        self._pomodoro_after_id: Optional[str] = None
        self._pomodoro_total = 0

        self._idle_after_id: Optional[str] = None

        self._apply_behavior_mode(self.behavior_mode)

    def _resize_frames_to_base(
        self,
        frames: list,
        base_size: Tuple[int, int],
        resample: Image.Resampling = Image.Resampling.LANCZOS,
    ) -> list:
        """将帧缩放到基础尺寸"""
        width, height = base_size
        resized_frames = []
        for frame in frames:
            resized = frame.resize((width, height), resample)
            resized_frames.append(ImageTk.PhotoImage(resized))
        return resized_frames

    def _ensure_music_frames(self) -> None:
        """确保音乐动画已加载"""
        if self.music_frames and self.music_delays:
            return

        raw_frames, raw_delays = self._raw_gif_cache.get("ameath.gif", ([], []))
        if not raw_frames:
            raw_frames, raw_delays = load_gif_frames_raw("ameath.gif")
            if self._raw_gif_cache_enabled:
                self._raw_gif_cache["ameath.gif"] = (raw_frames, raw_delays)

        self.music_delays = raw_delays
        if self.move_frames and raw_frames:
            base_size = (self.move_frames[0].width(), self.move_frames[0].height())
            resized = [
                frame.resize(base_size, Image.Resampling.BILINEAR)
                for frame in raw_frames
            ]
            self.music_frames = [ImageTk.PhotoImage(frame) for frame in resized]

    def _get_time_period(self) -> str:
        """获取当前时间段"""
        from datetime import datetime
        from src.constants import (
            TIME_MORNING_START,
            TIME_NOON_START,
            TIME_AFTERNOON_START,
            TIME_EVENING_START,
            TIME_NIGHT_START,
            TIME_SLEEP_START,
        )

        hour = datetime.now().hour

        if TIME_SLEEP_START <= hour < TIME_MORNING_START:
            return "sleep"
        elif TIME_MORNING_START <= hour < TIME_NOON_START:
            return "morning"
        elif TIME_NOON_START <= hour < TIME_AFTERNOON_START:
            return "noon"
        elif TIME_AFTERNOON_START <= hour < TIME_EVENING_START:
            return "afternoon"
        elif TIME_EVENING_START <= hour < TIME_NIGHT_START:
            return "evening"
        else:
            return "night"

    def _preload_raw_gifs(self) -> None:
        """预加载部分原始 GIF 帧，减少缩放时解码耗时"""
        if not self._raw_gif_cache_enabled:
            return
        if "ameath.gif" not in self._raw_gif_cache:
            raw_frames, raw_delays = load_gif_frames_raw("ameath.gif")
            self._raw_gif_cache["ameath.gif"] = (raw_frames, raw_delays)

    def _prune_animation_cache(self, keep_key: int) -> None:
        """清理动画缓存，减少内存占用"""
        if not self._animation_cache:
            return
        for key in list(self._animation_cache.keys()):
            if key != keep_key:
                del self._animation_cache[key]

    def _check_routine(self) -> None:
        """检查作息状态（每分钟调用一次）"""
        from datetime import datetime
        from src.constants import REMINDERS, SLEEP_SPEED_MULTIPLIER, SPEED_X, SPEED_Y

        # 检查时间段变化
        current_period = self._get_time_period()

        if current_period != self._current_time_period:
            self._current_time_period = current_period

            # 进入睡眠时段
            if current_period == "sleep":
                self._is_sleeping = True
                # 降低移动速度
                global SPEED_X, SPEED_Y
                SPEED_X = int(self._original_speed_x * SLEEP_SPEED_MULTIPLIER)
                SPEED_Y = int(self._original_speed_y * SLEEP_SPEED_MULTIPLIER)
                # 显示晚安提示
                self.speech_bubble.show("夜深了，我困了...", duration=5000)

            # 离开睡眠时段
            elif self._is_sleeping:
                self._is_sleeping = False
                SPEED_X = self._original_speed_x
                SPEED_Y = self._original_speed_y
                self.speech_bubble.show("早上好！新的一天开始啦~", duration=5000)

        # 检查提醒
        if not self._is_sleeping and not self.is_paused:
            current_time = datetime.now()
            for reminder_type, config in REMINDERS.items():
                last_time = self._last_reminder_time.get(reminder_type)
                if (
                    last_time is None
                    or (current_time - last_time).total_seconds() / 60
                    >= config["interval"]
                ):
                    # 显示提醒
                    import random

                    message = random.choice(config["messages"])
                    self.speech_bubble.show(message, duration=5000)
                    self._last_reminder_time[reminder_type] = current_time
                    break  # 一次只显示一个提醒

        # 每分钟检查一次
        self.root.after(60000, self._check_routine)

    def _bind_events(self) -> None:
        """绑定事件"""
        self.label.bind("<ButtonPress-1>", self._on_mouse_down)
        self.label.bind("<B1-Motion>", self._do_drag)
        self.label.bind("<ButtonRelease-1>", self._on_mouse_up)

    def _start_loops(self) -> None:
        """启动循环"""
        self._init_music_backend()
        self.animate()
        self._schedule_move(MOVE_INTERVAL)
        self.root.after(2000, self._ensure_topmost)
        self.root.after(100, self._check_quit)
        self.root.after(1000, self._check_routine)  # 1秒后开始作息检查

    # ============ 动画方法 ============

    def animate(self) -> None:
        """动画循环"""
        if not self.current_frames:
            self.root.after(100, self.animate)
            return

        if self._resizing:
            self.root.after(30, self.animate)
            return

        if self.dragging:
            self.root.after(50, self.animate)
            return

        self.label.config(image=self.current_frames[self.frame_index])
        delay = self.current_delays[self.frame_index] if self.current_delays else 100

        self.frame_index = (self.frame_index + 1) % len(self.current_frames)
        self.root.after(delay, self.animate)

    # ============ 运动方法（优化版）=========

    def move(self) -> None:
        """运动状态机主循环（性能优化版）"""
        self._move_after_id = None
        if self._music_playing:
            return self._schedule_move(100)

        if self.is_paused or self.dragging:
            delay = 100 if self.is_paused else 50
            return self._schedule_move(delay)

        if self.behavior_mode == BEHAVIOR_MODE_QUIET:
            if self.is_moving:
                self._switch_to_idle()
            return self._schedule_move(MOVE_INTERVAL)

        # 随机停下休息
        if self.motion_state == MOTION_WANDER and self.is_moving:
            stop_chance = (
                self._behavior_stop_chance
                if self._behavior_stop_chance is not None
                else STOP_CHANCE
            )
            if (
                self._move_ticks_since_move >= self._behavior_min_move_ticks
                and random.random() < stop_chance
            ):
                self.motion_state = MOTION_REST
                self.rest_timer = random.randint(STOP_DURATION_MIN, STOP_DURATION_MAX)
                self._switch_to_idle()
                return self._schedule_move(MOVE_INTERVAL)

        # 休息状态处理
        if self.motion_state == MOTION_REST:
            self.rest_timer -= MOVE_INTERVAL
            if self.rest_timer <= 0:
                self.motion_state = MOTION_WANDER
                self.target_x, self.target_y = self._get_random_target()
                self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)
                self._switch_to_move()
            return self._schedule_move(MOVE_INTERVAL)

        # 缓存鼠标位置
        mx = self.root.winfo_pointerx()
        my = self.root.winfo_pointery()
        mouse_moved = (mx, my) != self._last_mouse
        self._last_mouse = (mx, my)

        # 计算到目标的距离（使用平方距离避免开方）
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist_sq = dx * dx + dy * dy
        dist = dist_sq**0.5 if dist_sq > 0 else 1

        follow_mouse = self.follow_mouse
        if self._behavior_follow_override is not None:
            follow_mouse = self._behavior_follow_override

        if self.behavior_mode == BEHAVIOR_MODE_ACTIVE:
            follow_mouse = False

        # 状态判断与切换
        if not follow_mouse and self.motion_state in (
            MOTION_FOLLOW,
            MOTION_CURIOUS,
        ):
            self.motion_state = MOTION_WANDER

        if follow_mouse:
            # 计算到鼠标的距离
            dist_mouse_sq = (mx - self.x) ** 2 + (my - self.y) ** 2

            if dist_mouse_sq > FOLLOW_START_DIST**2:
                self.motion_state = MOTION_FOLLOW
            elif dist_mouse_sq < FOLLOW_STOP_DIST**2:
                self.motion_state = MOTION_CURIOUS
            else:
                self.motion_state = MOTION_WANDER

        # 游荡模式到达目标
        elif self.motion_state == MOTION_WANDER and dist < REST_DISTANCE:
            rest_chance = (
                self._behavior_rest_chance
                if self._behavior_rest_chance is not None
                else REST_CHANCE
            )
            if random.random() < rest_chance:
                self.motion_state = MOTION_REST
                self.rest_timer = random.randint(REST_DURATION_MIN, REST_DURATION_MAX)
                self._switch_to_idle()
                self.root.after(MOVE_INTERVAL, self.move)
                return
            else:
                self.target_x, self.target_y = self._get_random_target()
                self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)

        # 定时更换目标
        if self.motion_state == MOTION_WANDER:
            self.target_timer -= 1
            if self.target_timer <= 0:
                self.target_x, self.target_y = self._get_random_target()
                target_min = (
                    self._behavior_target_min
                    if self._behavior_target_min is not None
                    else TARGET_CHANGE_MIN
                )
                target_max = (
                    self._behavior_target_max
                    if self._behavior_target_max is not None
                    else TARGET_CHANGE_MAX
                )
                self.target_timer = random.randint(target_min, target_max)

        # 获取速度倍率
        speed_mul = self._get_speed_multiplier()

        # 跟随/好奇模式更新目标
        if self.motion_state in (MOTION_FOLLOW, MOTION_CURIOUS) and mouse_moved:
            offset = (
                FOLLOW_DISTANCE
                if self.motion_state == MOTION_FOLLOW
                else FOLLOW_STOP_DIST
            )
            self.target_x = mx + random.randint(-offset, offset)
            self.target_y = my + random.randint(-offset, offset)

            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = max(1, (dx * dx + dy * dy) ** 0.5)

        # 计算速度（惯性 + 意图）
        desired_vx = dx / dist * SPEED_X * speed_mul
        desired_vy = dy / dist * SPEED_Y * speed_mul

        self.vx = self.vx * INERTIA_FACTOR + desired_vx * INTENT_FACTOR
        self.vy = self.vy * INERTIA_FACTOR + desired_vy * INTENT_FACTOR

        # 根据速度方向切换动画
        if self.is_moving and not self._music_playing:
            new_moving_right = self.vx >= 0.5
            new_moving_left = self.vx <= -0.5
            if new_moving_right and not self.moving_right:
                self.moving_right = True
                self.current_frames = self.move_frames
                self.current_delays = self.move_delays
                self.frame_index = 0
            elif new_moving_left and self.moving_right:
                self.moving_right = False
                self.current_frames = self.move_frames_left
                self.current_delays = self.move_delays
                self.frame_index = 0

        # 抖动降频
        self._move_tick += 1
        if self._move_tick % JITTER_INTERVAL == 0:
            self._jitter_x = random.uniform(-JITTER, JITTER)
            self._jitter_y = random.uniform(-JITTER, JITTER)

        self.vx += self._jitter_x
        self.vy += self._jitter_y

        # 应用移动
        self.x += self.vx
        self.y += self.vy

        # 处理边缘
        self._handle_edge()

        # 更新窗口位置（仅在位置变化时）
        ix, iy = int(self.x), int(self.y)
        if (ix, iy) != self._last_pos:
            self.root.geometry(f"+{ix}+{iy}")
            self._last_pos = (ix, iy)
            if hasattr(self, "speech_bubble") and self.speech_bubble:
                self.speech_bubble.update_position()
            if hasattr(self, "pomodoro_indicator") and self.pomodoro_indicator:
                self.pomodoro_indicator.update_position()

        self._move_ticks_since_move += 1
        return self._schedule_move(MOVE_INTERVAL)

    def _schedule_move(self, delay: int) -> None:
        """调度下一次移动"""
        if self._move_after_id:
            self.root.after_cancel(self._move_after_id)
            self._move_after_id = None
        self._move_after_id = self.root.after(delay, self.move)

    def _get_random_target(self) -> Tuple[int, int]:
        """获取随机目标点"""
        if random.random() < OUTSIDE_TARGET_CHANCE:
            side = random.choice(["left", "right", "top", "bottom"])
            margin = RESPAWN_MARGIN + 50

            if side == "left":
                return (-margin, random.randint(0, self.screen_h - self.h))
            elif side == "right":
                return (
                    self.screen_w + margin,
                    random.randint(0, self.screen_h - self.h),
                )
            elif side == "top":
                return (random.randint(0, self.screen_w - self.w), -margin)
            else:
                return (
                    random.randint(0, self.screen_w - self.w),
                    self.screen_h + margin,
                )
        else:
            return (
                random.randint(0, self.screen_w - self.w),
                random.randint(0, self.screen_h - self.h),
            )

    def _get_speed_multiplier(self) -> float:
        """获取速度倍率"""
        multipliers = {
            MOTION_WANDER: SPEED_WANDER,
            MOTION_FOLLOW: SPEED_FOLLOW,
            MOTION_CURIOUS: SPEED_CURIOUS,
        }
        base = multipliers.get(self.motion_state, 1.0)
        return base * self._behavior_speed_mul

    def _handle_edge(self) -> None:
        """处理边缘碰撞"""
        # 检查是否出屏
        if (
            self.x < -self.w
            or self.x > self.screen_w
            or self.y < -self.h
            or self.y > self.screen_h
        ):
            # 可以在这里添加重生逻辑
            pass

        # 边界反弹
        hit_edge = False
        if self.x <= 0:
            self.x = 0
            self.vx = abs(self.vx)
            hit_edge = True
        elif self.x + self.w >= self.screen_w:
            self.x = self.screen_w - self.w
            self.vx = -abs(self.vx)
            hit_edge = True

        if self.y <= 0:
            self.y = 0
            self.vy = abs(self.vy)
            hit_edge = True
        elif self.y + self.h >= self.screen_h:
            self.y = self.screen_h - self.h
            self.vy = -abs(self.vy)
            hit_edge = True

        # 更新方向状态
        if hit_edge:
            new_moving_right = self.vx > 0.5
            new_moving_left = self.vx < -0.5

            if new_moving_right and not self.moving_right:
                self.moving_right = True
                self.current_frames = self.move_frames
                self.current_delays = self.move_delays
                self.frame_index = 0
            elif new_moving_left and self.moving_right:
                self.moving_right = False
                self.current_frames = self.move_frames_left
                self.current_delays = self.move_delays
                self.frame_index = 0

    # ============ 状态切换方法 ============

    def _switch_to_idle(self) -> None:
        """切换到待机动画"""
        if self.is_paused:
            return

        if self._music_playing:
            return

        self.is_moving = False
        self._move_ticks_since_move = 0
        if self.idle_gifs:
            if self.behavior_mode == BEHAVIOR_MODE_ACTIVE:
                frames, delays = random.choice(self.idle_gifs)
            else:
                frames, delays = self._pick_idle_gif()
            self.current_frames = frames
            self.current_delays = delays
            self.frame_index = 0

        if self.behavior_mode != BEHAVIOR_MODE_QUIET:
            return

    def _switch_to_move(self) -> None:
        """切换到移动动画"""
        if self.is_paused:
            return

        if self._music_playing:
            return

        if self.behavior_mode == BEHAVIOR_MODE_QUIET:
            return

        self.is_moving = True
        self._move_ticks_since_move = 0
        self.current_frames = (
            self.move_frames if self.moving_right else self.move_frames_left
        )
        self.current_delays = self.move_delays
        self.frame_index = 0

        if self._move_after_id:
            self.root.after_cancel(self._move_after_id)
            self._move_after_id = None
        self._schedule_move(MOVE_INTERVAL)

    def _apply_behavior_mode(self, mode: str) -> None:
        """应用行为模式参数"""
        self.behavior_mode = mode

        follow_override: Optional[bool] = None

        if mode == BEHAVIOR_MODE_QUIET:
            follow_override = False
            self._behavior_stop_chance = min(STOP_CHANCE * 2.0, 0.9)
            self._behavior_rest_chance = min(REST_CHANCE * 1.5, 0.95)
            self._behavior_target_min = int(TARGET_CHANGE_MIN * 1.6)
            self._behavior_target_max = int(TARGET_CHANGE_MAX * 1.6)
            self._behavior_speed_mul = 0.7
            self._behavior_min_move_ticks = 0
        elif mode == BEHAVIOR_MODE_CLINGY:
            follow_override = True
            self._behavior_stop_chance = max(STOP_CHANCE * 0.3, 0.0001)
            self._behavior_rest_chance = max(REST_CHANCE * 0.3, 0.05)
            self._behavior_target_min = int(TARGET_CHANGE_MIN * 0.7)
            self._behavior_target_max = int(TARGET_CHANGE_MAX * 0.7)
            self._behavior_speed_mul = 1.1
            self._behavior_min_move_ticks = 10
        else:
            follow_override = None
            self._behavior_stop_chance = None
            self._behavior_rest_chance = 0.08
            self._behavior_target_min = None
            self._behavior_target_max = None
            self._behavior_speed_mul = 1.0
            self._behavior_min_move_ticks = 18

        self._behavior_follow_override = follow_override
        if follow_override is not None:
            self.set_follow_mouse(follow_override)

        if mode == BEHAVIOR_MODE_QUIET:
            self.motion_state = MOTION_REST
            self._switch_to_idle()
        elif not self.is_paused and not self.dragging and not self._music_playing:
            self.motion_state = MOTION_WANDER
            self._switch_to_move()

        if hasattr(self, "tray_controller") and self.tray_controller:
            if self.tray_controller.icon:
                self.tray_controller.icon.menu = self.tray_controller.build_menu()

    def set_behavior_mode(self, mode: str) -> None:
        """设置行为模式"""
        if mode not in (
            BEHAVIOR_MODE_QUIET,
            BEHAVIOR_MODE_ACTIVE,
            BEHAVIOR_MODE_CLINGY,
        ):
            return
        self._apply_behavior_mode(mode)
        update_config(behavior_mode=mode)

    def toggle_pomodoro(self) -> None:
        """开始/停止番茄钟"""
        if self._pomodoro_enabled:
            self._stop_pomodoro()
        else:
            self._start_pomodoro()

    def reset_pomodoro(self) -> None:
        """重置番茄钟"""
        if not self._pomodoro_enabled:
            return
        self._pomodoro_phase = "work"
        self._pomodoro_total = POMODORO_WORK_MINUTES * 60
        self._pomodoro_remaining = self._pomodoro_total
        self._pomodoro_paused = False
        self._update_pomodoro_indicator()
        self._schedule_pomodoro_tick()
        self.speech_bubble.show("番茄钟已重置，开始专注~", duration=2500)

    def _start_pomodoro(self) -> None:
        """启动番茄钟"""
        self._pomodoro_enabled = True
        self._pomodoro_phase = "work"
        self._pomodoro_total = POMODORO_WORK_MINUTES * 60
        self._pomodoro_remaining = self._pomodoro_total
        self._pomodoro_paused = False
        self._update_pomodoro_indicator()
        self._schedule_pomodoro_tick()
        self.speech_bubble.show("番茄钟开始：专注 25 分钟", duration=3000)

    def _stop_pomodoro(self) -> None:
        """停止番茄钟"""
        self._pomodoro_enabled = False
        self._pomodoro_paused = False
        self._pomodoro_remaining = 0
        self._pomodoro_total = 0
        if self._pomodoro_after_id:
            self.root.after_cancel(self._pomodoro_after_id)
            self._pomodoro_after_id = None
        self.pomodoro_indicator.hide()
        self.speech_bubble.show("番茄钟已停止", duration=2000)

    def _schedule_pomodoro_tick(self) -> None:
        """调度番茄钟计时"""
        if self._pomodoro_after_id:
            self.root.after_cancel(self._pomodoro_after_id)
            self._pomodoro_after_id = None
        if not self._pomodoro_enabled or self._pomodoro_paused:
            return
        self._pomodoro_after_id = self.root.after(1000, self._pomodoro_tick)

    def _pomodoro_tick(self) -> None:
        """番茄钟计时回调"""
        if not self._pomodoro_enabled or self._pomodoro_paused:
            return
        self._pomodoro_remaining -= 1
        if self._pomodoro_remaining <= 0:
            self._switch_pomodoro_phase()
        self._update_pomodoro_indicator()
        self._schedule_pomodoro_tick()

    def _switch_pomodoro_phase(self) -> None:
        """切换番茄钟阶段"""
        if self._pomodoro_phase == "work":
            self._pomodoro_phase = "rest"
            self._pomodoro_total = POMODORO_REST_MINUTES * 60
            self._pomodoro_remaining = self._pomodoro_total
            self.speech_bubble.show("休息 5 分钟，放松一下~", duration=3000)
            self._switch_to_idle()
        else:
            self._pomodoro_phase = "work"
            self._pomodoro_total = POMODORO_WORK_MINUTES * 60
            self._pomodoro_remaining = self._pomodoro_total
            self.speech_bubble.show("专注时间到，继续加油！", duration=3000)
        self._update_pomodoro_indicator()

    def _update_pomodoro_indicator(self) -> None:
        """更新番茄钟进度显示"""
        if not self._pomodoro_enabled:
            self.pomodoro_indicator.hide()
            return

        phase_text = "专注" if self._pomodoro_phase == "work" else "休息"
        self.pomodoro_indicator.update_progress(
            phase_text, self._pomodoro_remaining, self._pomodoro_total
        )

    def _pick_idle_gif(self) -> Tuple[list, list]:
        """选择待机动画（均匀轮换）"""
        if not self.idle_gifs:
            return self.current_frames, self.current_delays

        idle2_index = 1
        if len(self.idle_gifs) > idle2_index:
            self._last_idle_index = idle2_index
            return self.idle_gifs[idle2_index]

        self._last_idle_index = 0
        return self.idle_gifs[0]

    # ============ 拖动方法 ============

    def _start_drag(self, event: tk.Event) -> None:
        """开始拖动"""
        if self.click_through:
            return

        self.dragging = True
        self.drag_start_x = self._mouse_down_x
        self.drag_start_y = self._mouse_down_y
        self._pre_drag_frames = self.current_frames
        self._pre_drag_delays = self.current_delays
        self._click_count = 0
        self._drag_started = True

        if self.drag_frames:
            self.current_frames = self.drag_frames
            self.current_delays = [1000] * len(self.drag_frames)
            self.frame_index = 0
            self.label.config(image=self.current_frames[0])

    def _do_drag(self, event: tk.Event) -> None:
        """拖动中"""
        if not self.dragging and self._pending_drag:
            dx = event.x - self._mouse_down_x
            dy = event.y - self._mouse_down_y
            if abs(dx) > 5 or abs(dy) > 5:
                self._start_drag(event)

        if self.dragging:
            self.x = event.x_root - self.drag_start_x
            self.y = event.y_root - self.drag_start_y
            self.root.geometry(f"+{int(self.x)}+{int(self.y)}")
            # 更新气泡位置（跟随移动）
            if hasattr(self, "speech_bubble") and self.speech_bubble:
                self.speech_bubble.update_position()
            if hasattr(self, "pomodoro_indicator") and self.pomodoro_indicator:
                self.pomodoro_indicator.update_position()

    def _stop_drag(self, event: tk.Event) -> None:
        """停止拖动"""
        self.dragging = False
        if self._pre_drag_frames is not None:
            self.current_frames = self._pre_drag_frames
            self.current_delays = self._pre_drag_delays
            self.frame_index = 0

    def _on_mouse_down(self, event: tk.Event) -> None:
        """鼠标按下事件 - 处理单击/双击/拖动"""
        if self.click_through:
            return

        self._pending_drag = True
        self._mouse_down_x = event.x
        self._mouse_down_y = event.y
        self._drag_started = False

        import time

        current_time = int(time.time() * 1000)
        time_since_last_click = current_time - self._last_click_time

        if time_since_last_click < 300:  # 双击（300ms内）
            self._click_count = 2
            self._handle_double_click(event)
        else:
            self._click_count = 1
            self._last_click_time = current_time
            # 延迟处理单击，以区分双击
            self.root.after(300, lambda: self._handle_single_click(event))

    def _on_mouse_up(self, event: tk.Event) -> None:
        """鼠标释放事件"""
        if self.dragging:
            self._stop_drag(event)
        self._pending_drag = False

    def _handle_single_click(self, event: tk.Event) -> None:
        """处理单击 - 显示互动反馈"""
        # 如果已经处理了双击，跳过
        if self._click_count != 1:
            return

        if self._drag_started:
            return

        # 显示点击反应
        self.speech_bubble.show_click_reaction()

    def _handle_double_click(self, event: tk.Event) -> None:
        """处理双击 - 显示快捷菜单"""
        # 重置点击计数
        self._click_count = 0
        self._pending_drag = False
        # 显示快捷菜单
        self.quick_menu.show()

    def show_greeting(self) -> None:
        """显示问候语"""
        if not self._is_showing_greeting:
            self._is_showing_greeting = True
            self.speech_bubble.show_greeting()
            self.root.after(5000, lambda: setattr(self, "_is_showing_greeting", False))

    # ============ 公共方法 ============

    def toggle_pause(self) -> None:
        """切换暂停/继续"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.is_moving = False
            if self.idle_gifs:
                frames, delays = random.choice(self.idle_gifs)
                self.current_frames = frames
                self.current_delays = delays
                self.frame_index = 0
        else:
            self.is_moving = True
            self.current_frames = (
                self.move_frames if self.moving_right else self.move_frames_left
            )
            self.current_delays = self.move_delays
            self.frame_index = 0

    def toggle_click_through(self) -> None:
        """切换鼠标穿透"""
        self.click_through = not self.click_through
        if self.hwnd:
            set_click_through(self.hwnd, self.click_through)
        update_config(click_through=self.click_through)

    def toggle_follow_mouse(self) -> None:
        """切换跟随鼠标"""
        self.follow_mouse = not self.follow_mouse
        update_config(follow_mouse=self.follow_mouse)

    def set_follow_mouse(self, enable: bool) -> None:
        """设置跟随鼠标"""
        self.follow_mouse = enable
        update_config(follow_mouse=self.follow_mouse)

    def set_scale(self, index: int) -> None:
        """设置缩放"""
        if not (0 <= index < len(SCALE_OPTIONS)):
            return

        self._resizing = True
        self.scale_index = index
        self.scale = SCALE_OPTIONS[index]
        update_config(scale_index=index)

        # 重新加载动画
        self._load_animations()

        if hasattr(self, "tray_controller") and self.tray_controller:
            if self.tray_controller.icon:
                self.tray_controller.icon.menu = self.tray_controller.build_menu()

        # 更新窗口大小
        if self.move_frames:
            self.w = self.move_frames[0].width()
            self.h = self.move_frames[0].height()
            self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

        # 重置动画
        self.frame_index = 0
        if self._music_playing:
            if self._pre_music_is_moving:
                self._last_frames = (
                    self.move_frames if self.moving_right else self.move_frames_left
                )
                self._last_delays = self.move_delays
            elif self.idle_gifs:
                frames, delays = self._pick_idle_gif()
                self._last_frames = frames
                self._last_delays = delays
            self._ensure_music_frames()
            self._switch_to_music_animation()
        else:
            if not self.is_moving and self.idle_gifs:
                frames, delays = self._pick_idle_gif()
                self.current_frames = frames
                self.current_delays = delays
            else:
                self.current_frames = (
                    self.move_frames if self.moving_right else self.move_frames_left
                )
                self.current_delays = self.move_delays

        if self.current_frames:
            self.label.config(image=self.current_frames[0])
            self.root.update_idletasks()

        self._resizing = False

    def set_transparency(self, index: int, persist: bool = True) -> None:
        """设置透明度"""
        if not (0 <= index < len(TRANSPARENCY_OPTIONS)):
            return

        self.transparency_index = index
        alpha = TRANSPARENCY_OPTIONS[index]
        self.root.attributes("-alpha", alpha)

        if persist:
            update_config(transparency_index=index)

    def set_auto_startup_flag(self, enable: bool) -> bool:
        """设置开机自启"""
        return set_auto_startup(enable)

    def request_quit(self) -> None:
        """请求退出"""
        self._request_quit = True

    def _ensure_topmost(self) -> None:
        """确保窗口置顶"""
        if not self.is_paused and self.hwnd:
            set_window_topmost(self.hwnd)
        self.root.after(2000, self._ensure_topmost)

    def _check_quit(self) -> None:
        """检查退出标志"""
        if self._request_quit:
            self._stop_music()
            # 注销全局快捷键
            from src.hotkey import hotkey_manager

            hotkey_manager.unregister_all()

            if hasattr(self, "tray_controller") and self.tray_controller:
                self.tray_controller.stop()
            self.root.destroy()
            return
        self.root.after(100, self._check_quit)

    def toggle_music_playback(self) -> bool:
        """切换音乐播放

        Returns:
            True 表示正在播放，False 表示已停止
        """
        if self._music_playing:
            self._stop_music()
            return False

        if not self._music_playlist:
            self._music_playlist = self._load_music_playlist()

        if not self._music_playlist:
            self.speech_bubble.show("未找到音乐文件", duration=3000)
            return False

        if not self._start_music():
            self.speech_bubble.show("音乐播放失败", duration=3000)
            return False

        return True

    def is_music_playing(self) -> bool:
        """判断音乐是否正在播放"""
        return self._music_playing

    def _load_music_playlist(self) -> list:
        """加载音乐播放列表（按文件名排序）"""
        from pathlib import Path

        music_dir = Path(resource_path("assets/music"))
        if not music_dir.exists():
            return []

        return sorted(str(p) for p in music_dir.glob("*.mp3"))

    def _init_music_backend(self) -> None:
        """初始化音乐模块"""
        try:
            pygame.mixer.init()
        except pygame.error as e:
            print(f"初始化音乐模块失败: {e}")

    def _start_music(self) -> bool:
        """开始音乐播放"""
        if not pygame.mixer.get_init():
            self._init_music_backend()
        if not pygame.mixer.get_init():
            return False
        try:
            pygame.mixer.music.load(self._music_playlist[self._music_index])
            pygame.mixer.music.play()
        except pygame.error as e:
            print(f"音乐播放失败: {e}")
            return False

        self._last_frames = None
        self._last_delays = None
        self._music_playing = True
        self._ensure_music_frames()
        self._switch_to_music_animation()
        self._check_music_end()
        return True

    def _check_music_end(self) -> None:
        """检查音乐是否播放完毕"""
        if not self._music_playing:
            return

        if not pygame.mixer.music.get_busy():
            if self._music_playlist:
                self._music_index = (self._music_index + 1) % len(self._music_playlist)
                pygame.mixer.music.load(self._music_playlist[self._music_index])
                pygame.mixer.music.play()

        self.root.after(500, self._check_music_end)

    def _stop_music(self) -> None:
        """停止音乐播放"""
        if not self._music_playing:
            return

        try:
            pygame.mixer.music.stop()
        except pygame.error as e:
            print(f"停止音乐失败: {e}")

        self._music_playing = False
        self._restore_animation_after_music()

    def _switch_to_music_animation(self) -> None:
        """切换到音乐动画"""
        if not self.music_frames:
            self._ensure_music_frames()
        if self.music_frames:
            if self._last_frames is None or self._last_delays is None:
                self._last_frames = self.current_frames
                self._last_delays = self.current_delays
                self._pre_music_motion_state = self.motion_state
                self._pre_music_is_moving = self.is_moving
            self.current_frames = self.music_frames
            self.current_delays = self.music_delays
            self.frame_index = 0
            self.motion_state = MOTION_REST
            self.is_moving = False
            if self.current_frames:
                self.w = self.current_frames[0].width()
                self.h = self.current_frames[0].height()
                self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

    def _restore_animation_after_music(self) -> None:
        """恢复播放前动画"""
        if self._last_frames is not None and self._last_delays is not None:
            self.current_frames = self._last_frames
            self.current_delays = self._last_delays
            self.frame_index = 0
        else:
            self._switch_to_move()

        self.motion_state = self._pre_music_motion_state
        self.is_moving = self._pre_music_is_moving
        if self.current_frames:
            self.w = self.current_frames[0].width()
            self.h = self.current_frames[0].height()
            self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")
