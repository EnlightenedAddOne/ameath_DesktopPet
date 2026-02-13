"""运动控制器（从 src/core/pet_core.py 拆分）"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional, Tuple

from src.behavior.behavior_modes import get_behavior_params
from src.config import update_config
from src.constants import (
    BEHAVIOR_MODE_ACTIVE,
    BEHAVIOR_MODE_CLINGY,
    BEHAVIOR_MODE_QUIET,
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
    REST_CHANCE,
    REST_DISTANCE,
    REST_DURATION_MAX,
    REST_DURATION_MIN,
    RESPAWN_MARGIN,
    SPEED_CURIOUS,
    SPEED_FOLLOW,
    SPEED_WANDER,
    STOP_CHANCE,
    STOP_DURATION_MAX,
    STOP_DURATION_MIN,
    TARGET_CHANGE_MAX,
    TARGET_CHANGE_MIN,
)

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class MotionController:
    """运动控制器

    说明：状态字段仍存放在 app 上（vx/vy/target_x/...），controller 负责更新。
    """

    def __init__(self, app: "DesktopPet") -> None:
        self.app = app

    def init_state(self) -> None:
        """初始化运动相关状态（目标点/计时器等）"""
        self.app.target_x, self.app.target_y = self._get_random_target()
        self.app.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)
        self.app.rest_timer = 0

    def tick(self) -> None:
        """运动状态机主循环（性能优化版）"""
        self.app._move_after_id = None
        if self.app._music_playing:
            return self._schedule(MOVE_INTERVAL if MOVE_INTERVAL < 100 else 100)

        if self.app.is_paused or self.app.dragging:
            delay = 100 if self.app.is_paused else 50
            return self._schedule(delay)

        if self.app.behavior_mode == BEHAVIOR_MODE_QUIET:
            if self.app.is_moving:
                self.app._switch_to_idle()
            return self._schedule(MOVE_INTERVAL)

        # 随机停下休息
        if self.app.motion_state == MOTION_WANDER and self.app.is_moving:
            stop_chance = self.app._behavior_stop_chance
            if stop_chance is None:
                stop_chance = STOP_CHANCE
            if (
                self.app._move_ticks_since_move >= self.app._behavior_min_move_ticks
                and random.random() < stop_chance
            ):
                self.app.motion_state = MOTION_REST
                self.app.rest_timer = random.randint(
                    STOP_DURATION_MIN, STOP_DURATION_MAX
                )
                self.app._switch_to_idle()
                return self._schedule(MOVE_INTERVAL)

        # 休息状态处理
        if self.app.motion_state == MOTION_REST:
            self.app.rest_timer -= MOVE_INTERVAL
            if self.app.rest_timer <= 0:
                self.app.motion_state = MOTION_WANDER
                self.app.target_x, self.app.target_y = self._get_random_target()
                self.app.target_timer = random.randint(
                    TARGET_CHANGE_MIN, TARGET_CHANGE_MAX
                )
                self.app._switch_to_move()
            return self._schedule(MOVE_INTERVAL)

        mx = self.app.root.winfo_pointerx()
        my = self.app.root.winfo_pointery()
        mouse_moved = (mx, my) != self.app._last_mouse
        self.app._last_mouse = (mx, my)

        dx = self.app.target_x - self.app.x
        dy = self.app.target_y - self.app.y
        dist_sq = dx * dx + dy * dy
        dist = dist_sq**0.5 if dist_sq > 0 else 1

        follow_mouse = self.app.follow_mouse
        if self.app._behavior_follow_override is not None:
            follow_mouse = self.app._behavior_follow_override
        if self.app.behavior_mode == BEHAVIOR_MODE_ACTIVE:
            follow_mouse = False

        if not follow_mouse and self.app.motion_state in (
            MOTION_FOLLOW,
            MOTION_CURIOUS,
        ):
            self.app.motion_state = MOTION_WANDER

        if follow_mouse:
            dist_mouse_sq = (mx - self.app.x) ** 2 + (my - self.app.y) ** 2
            if dist_mouse_sq > FOLLOW_START_DIST**2:
                self.app.motion_state = MOTION_FOLLOW
            elif dist_mouse_sq < FOLLOW_STOP_DIST**2:
                self.app.motion_state = MOTION_CURIOUS
            else:
                self.app.motion_state = MOTION_WANDER
        elif self.app.motion_state == MOTION_WANDER and dist < REST_DISTANCE:
            rest_chance = self.app._behavior_rest_chance
            if rest_chance is None:
                rest_chance = REST_CHANCE
            if random.random() < rest_chance:
                self.app.motion_state = MOTION_REST
                self.app.rest_timer = random.randint(
                    REST_DURATION_MIN, REST_DURATION_MAX
                )
                self.app._switch_to_idle()
                self.app.root.after(MOVE_INTERVAL, self.tick)
                return
            self.app.target_x, self.app.target_y = self._get_random_target()
            self.app.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)

        if self.app.motion_state == MOTION_WANDER:
            self.app.target_timer -= 1
            if self.app.target_timer <= 0:
                self.app.target_x, self.app.target_y = self._get_random_target()
                target_min = self.app._behavior_target_min
                target_max = self.app._behavior_target_max
                if target_min is None:
                    target_min = TARGET_CHANGE_MIN
                if target_max is None:
                    target_max = TARGET_CHANGE_MAX
                self.app.target_timer = random.randint(target_min, target_max)

        speed_mul = self._get_speed_multiplier()

        if self.app.motion_state in (MOTION_FOLLOW, MOTION_CURIOUS) and mouse_moved:
            offset = (
                FOLLOW_DISTANCE
                if self.app.motion_state == MOTION_FOLLOW
                else FOLLOW_STOP_DIST
            )
            self.app.target_x = mx + random.randint(-offset, offset)
            self.app.target_y = my + random.randint(-offset, offset)
            dx = self.app.target_x - self.app.x
            dy = self.app.target_y - self.app.y
            dist = max(1, (dx * dx + dy * dy) ** 0.5)

        desired_vx = dx / dist * self.app._speed_x * speed_mul
        desired_vy = dy / dist * self.app._speed_y * speed_mul
        self.app.vx = self.app.vx * INERTIA_FACTOR + desired_vx * INTENT_FACTOR
        self.app.vy = self.app.vy * INERTIA_FACTOR + desired_vy * INTENT_FACTOR

        if self.app.is_moving and not self.app._music_playing:
            new_moving_right = self.app.vx >= 0.5
            new_moving_left = self.app.vx <= -0.5
            if new_moving_right and not self.app.moving_right:
                self.app.moving_right = True
                self.app.current_frames = self.app.move_frames
                self.app.current_delays = self.app.move_delays
                self.app.frame_index = 0
            elif new_moving_left and self.app.moving_right:
                self.app.moving_right = False
                self.app.current_frames = self.app.move_frames_left
                self.app.current_delays = self.app.move_delays
                self.app.frame_index = 0

        self.app._move_tick += 1
        if self.app._move_tick % JITTER_INTERVAL == 0:
            self.app._jitter_x = random.uniform(-JITTER, JITTER)
            self.app._jitter_y = random.uniform(-JITTER, JITTER)

        self.app.vx += self.app._jitter_x
        self.app.vy += self.app._jitter_y
        self.app.x += self.app.vx
        self.app.y += self.app.vy

        self._handle_edge()

        ix, iy = int(self.app.x), int(self.app.y)
        if (ix, iy) != self.app._last_pos:
            self.app.root.geometry(f"+{ix}+{iy}")
            self.app._last_pos = (ix, iy)
            if hasattr(self.app, "speech_bubble") and self.app.speech_bubble:
                self.app.speech_bubble.update_position()
            if hasattr(self.app, "pomodoro_indicator") and self.app.pomodoro_indicator:
                self.app.pomodoro_indicator.update_position()
            if hasattr(self.app, "music_panel") and self.app.music_panel:
                self.app.music_panel.update_position()

        self.app._move_ticks_since_move += 1
        return self._schedule(MOVE_INTERVAL)

    def _schedule(self, delay: int) -> None:
        if self.app._move_after_id:
            self.app.root.after_cancel(self.app._move_after_id)
            self.app._move_after_id = None
        self.app._move_after_id = self.app.root.after(delay, self.tick)

    def _get_random_target(self) -> Tuple[int, int]:
        if random.random() < OUTSIDE_TARGET_CHANCE:
            side = random.choice(["left", "right", "top", "bottom"])
            margin = RESPAWN_MARGIN + 50
            if side == "left":
                return (-margin, random.randint(0, self.app.screen_h - self.app.h))
            if side == "right":
                return (
                    self.app.screen_w + margin,
                    random.randint(0, self.app.screen_h - self.app.h),
                )
            if side == "top":
                return (random.randint(0, self.app.screen_w - self.app.w), -margin)
            return (
                random.randint(0, self.app.screen_w - self.app.w),
                self.app.screen_h + margin,
            )
        return (
            random.randint(0, self.app.screen_w - self.app.w),
            random.randint(0, self.app.screen_h - self.app.h),
        )

    def _get_speed_multiplier(self) -> float:
        multipliers = {
            MOTION_WANDER: SPEED_WANDER,
            MOTION_FOLLOW: SPEED_FOLLOW,
            MOTION_CURIOUS: SPEED_CURIOUS,
        }
        base = multipliers.get(self.app.motion_state, 1.0)
        return base * self.app._behavior_speed_mul

    def _handle_edge(self) -> None:
        # 出屏（保持原行为：目前不处理重生）
        if (
            self.app.x < -self.app.w
            or self.app.x > self.app.screen_w
            or self.app.y < -self.app.h
            or self.app.y > self.app.screen_h
        ):
            pass

        hit_edge = False
        if self.app.x <= 0:
            self.app.x = 0
            self.app.vx = abs(self.app.vx)
            hit_edge = True
        elif self.app.x + self.app.w >= self.app.screen_w:
            self.app.x = self.app.screen_w - self.app.w
            self.app.vx = -abs(self.app.vx)
            hit_edge = True

        if self.app.y <= 0:
            self.app.y = 0
            self.app.vy = abs(self.app.vy)
            hit_edge = True
        elif self.app.y + self.app.h >= self.app.screen_h:
            self.app.y = self.app.screen_h - self.app.h
            self.app.vy = -abs(self.app.vy)
            hit_edge = True

        if hit_edge:
            new_moving_right = self.app.vx > 0.5
            new_moving_left = self.app.vx < -0.5
            if new_moving_right and not self.app.moving_right:
                self.app.moving_right = True
                self.app.current_frames = self.app.move_frames
                self.app.current_delays = self.app.move_delays
                self.app.frame_index = 0
            elif new_moving_left and self.app.moving_right:
                self.app.moving_right = False
                self.app.current_frames = self.app.move_frames_left
                self.app.current_delays = self.app.move_delays
                self.app.frame_index = 0

    def apply_behavior_mode(self, mode: str) -> None:
        """应用行为模式参数"""
        self.app.behavior_mode = mode
        params = get_behavior_params(mode)
        self.app._behavior_follow_override = params.follow_override
        self.app._behavior_stop_chance = params.stop_chance
        self.app._behavior_rest_chance = params.rest_chance
        self.app._behavior_target_min = params.target_min
        self.app._behavior_target_max = params.target_max
        self.app._behavior_speed_mul = params.speed_mul
        self.app._behavior_min_move_ticks = params.min_move_ticks

        if params.follow_override is not None:
            self.app.set_follow_mouse(params.follow_override)

        if mode == BEHAVIOR_MODE_QUIET:
            self.app.motion_state = MOTION_REST
            self.app._switch_to_idle()
        elif (
            not self.app.is_paused
            and not self.app.dragging
            and not self.app._music_playing
        ):
            self.app.motion_state = MOTION_WANDER
            self.app._switch_to_move()

        if hasattr(self.app, "tray_controller") and self.app.tray_controller:
            if self.app.tray_controller.icon:
                self.app.tray_controller.icon.menu = (
                    self.app.tray_controller.build_menu()
                )

    def set_behavior_mode(self, mode: str) -> None:
        """设置行为模式"""
        if mode not in (
            BEHAVIOR_MODE_QUIET,
            BEHAVIOR_MODE_ACTIVE,
            BEHAVIOR_MODE_CLINGY,
        ):
            return
        self.apply_behavior_mode(mode)
        update_config(behavior_mode=mode)
