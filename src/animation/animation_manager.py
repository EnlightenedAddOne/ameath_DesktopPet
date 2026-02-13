"""动画管理（从 src/core/pet_core.py 拆分）"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional, Tuple

from PIL import Image, ImageTk

from src.animation.cache import AnimationCache, AnimationCacheEntry
from src.animation.gif_utils import flip_frames, load_gif_frames, load_gif_frames_raw
from src.constants import (
    BEHAVIOR_MODE_ACTIVE,
    BEHAVIOR_MODE_QUIET,
    MOTION_REST,
    SCALE_OPTIONS,
)

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class AnimationManager:
    """动画管理器

    说明：为了兼容现有逻辑，动画帧仍存放在 app 上（move_frames/current_frames/...），
    此管理器负责加载/缓存/切换与动画循环。
    """

    def __init__(self, app: "DesktopPet") -> None:
        self.app = app
        self.cache = AnimationCache()
        self._raw_gif_cache: dict[str, Tuple[list, list]] = {}
        self._raw_gif_cache_enabled = False

    def load_animations(self) -> None:
        """加载动画资源（带缓存）"""
        app = self.app
        cache_key = int(app.scale_index)

        cached = self.cache.get(cache_key)
        if cached:
            app.move_frames = cached.move_frames
            app.move_delays = cached.move_delays
            app.move_frames_left = cached.move_frames_left
            app.idle_gifs = cached.idle_gifs
            app.drag_frames = cached.drag_frames
            app.drag_delays = cached.drag_delays
            app.music_frames = cached.music_frames
            app.music_delays = cached.music_delays

            app.current_frames = app.move_frames
            app.current_delays = app.move_delays
            self._sync_window_size_and_position()
            return

        # 移动动画
        move_frames, move_delays, move_pil_frames = load_gif_frames(
            "move.gif", app.scale
        )
        app.move_frames = move_frames
        app.move_delays = move_delays
        app.move_frames_left = flip_frames(move_pil_frames)
        move_pil_frames.clear()

        # 待机动画
        app.idle_gifs = []
        for i in range(1, 5):
            idle_frames, idle_delays, _ = load_gif_frames(f"idle{i}.gif", app.scale)
            if idle_frames:
                app.idle_gifs.append((idle_frames, idle_delays))

        # 拖动动画
        drag_frames, drag_delays, _ = load_gif_frames("drag.gif", app.scale)
        app.drag_frames = drag_frames
        app.drag_delays = drag_delays

        # 音乐动画（延迟加载）
        app.music_frames = []
        app.music_delays = []
        if getattr(app, "_music_playing", False):
            self.ensure_music_frames()

        # 设置当前动画
        app.current_frames = app.move_frames
        app.current_delays = app.move_delays
        self._sync_window_size_and_position()

        entry = AnimationCacheEntry(
            move_frames=app.move_frames,
            move_delays=app.move_delays,
            move_frames_left=app.move_frames_left,
            idle_gifs=app.idle_gifs,
            drag_frames=app.drag_frames,
            drag_delays=app.drag_delays,
            music_frames=app.music_frames,
            music_delays=app.music_delays,
        )
        self.cache.set(cache_key, entry)
        if getattr(app, "_music_playing", False):
            self.ensure_music_frames()
            self.cache.update_music(cache_key, app.music_frames, app.music_delays)

    def ensure_music_frames(self) -> None:
        """确保音乐动画已加载"""
        app = self.app
        if getattr(app, "music_frames", None) and getattr(app, "music_delays", None):
            if app.music_frames and app.music_delays:
                return

        raw_frames, raw_delays = self._raw_gif_cache.get("ameath.gif", ([], []))
        if not raw_frames:
            raw_frames, raw_delays = load_gif_frames_raw("ameath.gif")
            if self._raw_gif_cache_enabled:
                self._raw_gif_cache["ameath.gif"] = (raw_frames, raw_delays)

        app.music_delays = raw_delays
        if getattr(app, "move_frames", None) and app.move_frames and raw_frames:
            base_size = (app.move_frames[0].width(), app.move_frames[0].height())
            resized = [
                frame.resize(base_size, Image.Resampling.BILINEAR)
                for frame in raw_frames
            ]
            app.music_frames = [ImageTk.PhotoImage(frame) for frame in resized]

    def preload_raw_gifs(self) -> None:
        """预加载部分原始 GIF 帧，减少缩放时解码耗时"""
        if not self._raw_gif_cache_enabled:
            return
        if "ameath.gif" not in self._raw_gif_cache:
            raw_frames, raw_delays = load_gif_frames_raw("ameath.gif")
            self._raw_gif_cache["ameath.gif"] = (raw_frames, raw_delays)

    def animate(self) -> None:
        """动画循环"""
        app = self.app
        app._animate_after_id = None
        if not getattr(app, "current_frames", None):
            app._animate_after_id = app.root.after(100, self.animate)
            return

        if getattr(app, "_resizing", False):
            app._animate_after_id = app.root.after(30, self.animate)
            return

        if getattr(app, "dragging", False):
            app._animate_after_id = app.root.after(50, self.animate)
            return

        app.label.config(image=app.current_frames[app.frame_index])
        delay = app.current_delays[app.frame_index] if app.current_delays else 100

        app.frame_index = (app.frame_index + 1) % len(app.current_frames)
        app._animate_after_id = app.root.after(delay, self.animate)

    def switch_to_idle(self) -> None:
        """切换到待机动画"""
        app = self.app
        if app.is_paused or getattr(app, "_music_playing", False):
            return

        app.is_moving = False
        app._move_ticks_since_move = 0
        if app.idle_gifs:
            if app.behavior_mode == BEHAVIOR_MODE_ACTIVE:
                frames, delays = random.choice(app.idle_gifs)
            else:
                frames, delays = self.pick_idle_gif()
            app.current_frames = frames
            app.current_delays = delays
            app.frame_index = 0

        if app.behavior_mode != BEHAVIOR_MODE_QUIET:
            return

    def switch_to_move(self) -> None:
        """切换到移动动画"""
        app = self.app
        if app.is_paused or getattr(app, "_music_playing", False):
            return
        if app.behavior_mode == BEHAVIOR_MODE_QUIET:
            return

        app.is_moving = True
        app._move_ticks_since_move = 0
        app.current_frames = (
            app.move_frames if app.moving_right else app.move_frames_left
        )
        app.current_delays = app.move_delays
        app.frame_index = 0

        if app._move_after_id:
            app.root.after_cancel(app._move_after_id)
            app._move_after_id = None
        app.motion.tick()

    def pick_idle_gif(self) -> Tuple[list, list]:
        """选择待机动画（均匀轮换）"""
        app = self.app
        if not app.idle_gifs:
            return app.current_frames, app.current_delays

        idle2_index = 1
        if len(app.idle_gifs) > idle2_index:
            app._last_idle_index = idle2_index
            return app.idle_gifs[idle2_index]

        app._last_idle_index = 0
        return app.idle_gifs[0]

    def switch_to_music_animation(self) -> None:
        """切换到音乐动画"""
        app = self.app
        if not getattr(app, "music_frames", None):
            self.ensure_music_frames()
        if not app.music_frames:
            return

        if app._last_frames is None or app._last_delays is None:
            app._last_frames = app.current_frames
            app._last_delays = app.current_delays
            app._pre_music_motion_state = app.motion_state
            app._pre_music_is_moving = app.is_moving

        app.current_frames = app.music_frames
        app.current_delays = app.music_delays
        app.frame_index = 0
        app.motion_state = MOTION_REST
        app.is_moving = False
        self._sync_window_size_and_position()

    def restore_animation_after_music(self) -> None:
        """恢复播放前动画"""
        app = self.app
        if app._last_frames is not None and app._last_delays is not None:
            app.current_frames = app._last_frames
            app.current_delays = app._last_delays
            app.frame_index = 0
        else:
            self.switch_to_move()

        app.motion_state = app._pre_music_motion_state
        app.is_moving = app._pre_music_is_moving
        self._sync_window_size_and_position()

    def _sync_window_size_and_position(self) -> None:
        app = self.app
        if getattr(app, "current_frames", None):
            app.w = app.current_frames[0].width()
            app.h = app.current_frames[0].height()
        else:
            app.w, app.h = 100, 100

        if hasattr(app, "x") and hasattr(app, "y"):
            app.root.geometry(f"{app.w}x{app.h}+{int(app.x)}+{int(app.y)}")
        else:
            app.x = 200
            app.y = 200
            app.root.geometry(f"{app.w}x{app.h}+{app.x}+{app.y}")
        app.root.update_idletasks()

    def apply_scale_change(self) -> None:
        """缩放变更后的统一收尾逻辑（窗口/帧/音乐动画同步）"""
        app = self.app

        # 更新窗口大小
        self._sync_window_size_and_position()

        # 重置动画帧
        app.frame_index = 0
        if getattr(app, "_music_playing", False):
            if getattr(app, "_pre_music_is_moving", False):
                app._last_frames = (
                    app.move_frames if app.moving_right else app.move_frames_left
                )
                app._last_delays = app.move_delays
            elif app.idle_gifs:
                frames, delays = self.pick_idle_gif()
                app._last_frames = frames
                app._last_delays = delays
            self.ensure_music_frames()
            self.switch_to_music_animation()
        else:
            if not app.is_moving and app.idle_gifs:
                frames, delays = self.pick_idle_gif()
                app.current_frames = frames
                app.current_delays = delays
            else:
                app.current_frames = (
                    app.move_frames if app.moving_right else app.move_frames_left
                )
                app.current_delays = app.move_delays

        if app.current_frames:
            app.label.config(image=app.current_frames[0])
            app.root.update_idletasks()
