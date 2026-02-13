"""桌面宠物主类模块"""

from __future__ import annotations

import random
import tkinter as tk
from typing import Any, Tuple

from src.config import load_config, update_config
from src.constants import (
    BEHAVIOR_MODE_ACTIVE,
    BEHAVIOR_MODE_CLINGY,
    BEHAVIOR_MODE_QUIET,
    DEFAULT_SCALE_INDEX,
    DEFAULT_TRANSPARENCY_INDEX,
    SCALE_OPTIONS,
    TRANSPARENCY_OPTIONS,
)
from src.startup import check_and_fix_startup, set_auto_startup

from src.productivity.pomodoro import PomodoroManager
from src.behavior.routine_manager import RoutineManager
from src.behavior.motion_controller import MotionController

from src.animation.animation_manager import AnimationManager
from src.core.state_manager import StateManager
from src.core.window_manager import WindowManager
from src.interaction.click_handler import ClickHandler
from src.interaction.drag_handler import DragHandler
from src.media.music_controller import MusicController


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
        self._resizing = False

        # 组合式管理器
        self.window = WindowManager(self)
        self.state = StateManager(self)
        self.animation = AnimationManager(self)
        self.drag = DragHandler(self)
        self.click = ClickHandler(self)
        self.music = MusicController(self)
        self.pomodoro = PomodoroManager(self)
        self.routine = RoutineManager(self)
        self.motion = MotionController(self)

        # 初始化窗口
        self.window.init_window()

        # 加载配置
        self._load_config()

        # 检查开机自启
        check_and_fix_startup()

        # 加载动画资源
        self.animation.load_animations()

        # 初始化状态
        self.state.init_state()

        # 预加载音乐原始帧，避免切换倍率时重复解码
        self.animation.preload_raw_gifs()

        # 绑定事件
        self._bind_events()

        # 启动循环
        self._start_loops()

    def _init_window(self) -> None:
        """初始化窗口"""
        self.window.init_window()

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
        # 应用鼠标穿透（需要先拿到 hwnd）
        self.window.init_handle_and_click_through()

    def _init_state(self) -> None:
        """初始化状态变量"""
        self.state.init_state()

    # 动画加载/缓存/音乐帧相关逻辑已迁移至 src/animation/animation_manager.py

    def _bind_events(self) -> None:
        """绑定事件"""
        self.label.bind("<ButtonPress-1>", self.click.on_mouse_down)
        self.label.bind("<B1-Motion>", self.drag.do_drag)
        self.label.bind("<ButtonRelease-1>", self.click.on_mouse_up)

    def _start_loops(self) -> None:
        """启动循环"""
        self.music.init_backend()
        self.animation.animate()
        self.motion.tick()
        self._topmost_after_id = self.root.after(2000, self._ensure_topmost)
        self._quit_after_id = self.root.after(100, self._check_quit)
        self._routine_after_id = self.root.after(
            1000, self.routine.tick
        )  # 1秒后开始作息检查

    # ============ 番茄钟（兼容对外方法名） ============

    def toggle_pomodoro(self) -> None:
        """开始/停止番茄钟"""
        self.pomodoro.toggle()

    def reset_pomodoro(self) -> None:
        """重置番茄钟"""
        self.pomodoro.reset()

    # ============ 动画方法 ============

    def animate(self) -> None:
        """动画循环"""
        self.animation.animate()

    # ============ 状态切换方法 ============

    def _switch_to_idle(self) -> None:
        """切换到待机动画"""
        self.animation.switch_to_idle()

    def _switch_to_move(self) -> None:
        """切换到移动动画"""
        self.animation.switch_to_move()

    def set_behavior_mode(self, mode: str) -> None:
        """设置行为模式"""
        self.motion.set_behavior_mode(mode)

    def update_config(self, **kwargs: object) -> None:
        """更新配置（兼容托盘等模块的调用方式）"""
        update_config(**kwargs)

    def _pick_idle_gif(self) -> Tuple[list, list]:
        """选择待机动画（兼容旧调用点）"""
        return self.animation.pick_idle_gif()

    # ============ 拖动方法 ============

    # 拖动/点击逻辑已迁移至 src/interaction/*.py

    def show_greeting(self) -> None:
        """显示问候语"""
        if self._music_playing:
            return
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
            self.animation.switch_to_move()

    def toggle_click_through(self) -> None:
        """切换鼠标穿透"""
        self.click_through = not self.click_through
        self.window.set_click_through(self.click_through)
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
        self.animation.load_animations()

        if hasattr(self, "tray_controller") and self.tray_controller:
            if self.tray_controller.icon:
                self.tray_controller.icon.menu = self.tray_controller.build_menu()

        self.animation.apply_scale_change()

        self._resizing = False

    def set_transparency(self, index: int, persist: bool = True) -> None:
        """设置透明度"""
        if not (0 <= index < len(TRANSPARENCY_OPTIONS)):
            return

        self.transparency_index = index
        self.window.set_transparency(index)

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
        self._topmost_after_id = None
        if not self.is_paused:
            self.window.ensure_topmost()
        self._topmost_after_id = self.root.after(2000, self._ensure_topmost)

    def _check_quit(self) -> None:
        """检查退出标志"""
        self._quit_after_id = None
        if self._request_quit:
            self._cancel_pending_afters()
            self.music.stop()
            # 注销全局快捷键
            from src.platform.hotkey import hotkey_manager

            hotkey_manager.unregister_all()

            if hasattr(self, "tray_controller") and self.tray_controller:
                self.tray_controller.stop()
            if hasattr(self, "music_panel") and self.music_panel:
                self.music_panel.hide()
            self.root.destroy()
            return
        self._quit_after_id = self.root.after(100, self._check_quit)

    def _cancel_pending_afters(self) -> None:
        """取消已调度的 after 任务，避免退出时报 TclError"""
        after_ids: list[tuple[str, Optional[str]]] = [
            ("_animate_after_id", getattr(self, "_animate_after_id", None)),
            ("_move_after_id", getattr(self, "_move_after_id", None)),
            ("_routine_after_id", getattr(self, "_routine_after_id", None)),
            ("_topmost_after_id", getattr(self, "_topmost_after_id", None)),
            ("_quit_after_id", getattr(self, "_quit_after_id", None)),
            ("_pomodoro_after_id", getattr(self, "_pomodoro_after_id", None)),
            ("_music_after_id", getattr(self, "_music_after_id", None)),
        ]

        for name, after_id in after_ids:
            if not after_id:
                continue
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
            setattr(self, name, None)

    def toggle_music_playback(self) -> bool:
        """切换音乐播放

        Returns:
            True 表示正在播放，False 表示已停止
        """
        return self.music.toggle_playback()

    def toggle_music_pause(self) -> bool:
        """切换音乐暂停

        Returns:
            True 表示暂停中，False 表示正在播放
        """
        return self.music.toggle_pause()

    def is_music_playing(self) -> bool:
        """判断音乐是否正在播放"""
        return self._music_playing

    def is_music_paused(self) -> bool:
        """判断音乐是否暂停"""
        return self._music_paused

    def next_music(self) -> None:
        """切换到下一首"""
        self.music.next()
        if self._music_playing and self.speech_bubble.is_visible():
            title = self.get_current_music_title()
            if title:
                self.speech_bubble.show(
                    f"🎵 {title}", duration=None, allow_during_music=True
                )

    def prev_music(self) -> None:
        """切换到上一首"""
        self.music.prev()
        if self._music_playing and self.speech_bubble.is_visible():
            title = self.get_current_music_title()
            if title:
                self.speech_bubble.show(
                    f"🎵 {title}", duration=None, allow_during_music=True
                )

    def get_current_music_path(self) -> str:
        """获取当前音乐路径"""
        return self.music.get_current_path()

    def get_current_music_title(self) -> str:
        """获取当前音乐标题（取文件名 '-' 前）"""
        return self.music.get_current_title()

    def get_music_position(self) -> float:
        """获取当前音乐播放位置（秒）"""
        return self.music.get_position()

    def get_music_length(self) -> float:
        """获取当前音乐总时长（秒）"""
        return self.music.get_length()

    def seek_music(self, seconds: float) -> None:
        """跳转到指定位置（秒）"""
        self.music.seek(seconds)

    # 音乐播放逻辑已迁移至 src/media/music_controller.py
