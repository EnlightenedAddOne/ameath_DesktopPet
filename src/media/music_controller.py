"""音乐控制（从 src/core/pet_core.py 拆分）"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from src.utils import resource_path

if TYPE_CHECKING:
    from src.core.pet_core import DesktopPet


class MusicController:
    """音乐控制器

    说明：为了避免影响外部模块，音乐状态字段仍保存在 app 上（_music_playing 等）。
    """

    def __init__(self, app: "DesktopPet") -> None:
        self.app = app

    def init_backend(self) -> None:
        """初始化音乐模块"""
        try:
            pygame.mixer.init()
        except pygame.error as e:
            print(f"初始化音乐模块失败: {e}")

    def toggle_playback(self) -> bool:
        """切换音乐播放"""
        app = self.app
        if app._music_playing:
            self.stop()
            return False

        if not app._music_playlist:
            app._music_playlist = self._load_playlist()

        if not app._music_playlist:
            app.speech_bubble.show("未找到音乐文件", duration=3000)
            return False

        if not self.start(from_seek=False):
            app.speech_bubble.show("音乐播放失败", duration=3000)
            return False

        return True

    def toggle_pause(self) -> bool:
        """切换音乐暂停"""
        app = self.app
        if not app._music_playing:
            return False
        if app._music_paused:
            self.resume()
            return False
        self.pause()
        return True

    def next(self) -> None:
        """切换到下一首"""
        app = self.app
        if not app._music_playlist:
            return
        app._music_index = (app._music_index + 1) % len(app._music_playlist)
        self.start(from_seek=False)

    def prev(self) -> None:
        """切换到上一首"""
        app = self.app
        if not app._music_playlist:
            return
        app._music_index = (app._music_index - 1) % len(app._music_playlist)
        self.start(from_seek=False)

    def get_current_path(self) -> str:
        app = self.app
        if not app._music_playlist:
            return ""
        return app._music_playlist[app._music_index]

    def get_current_title(self) -> str:
        path = self.get_current_path()
        if not path:
            return ""
        name = Path(path).stem
        if "-" in name:
            title = name.split("-", 1)[0].strip()
            return title or name
        return name

    def get_position(self) -> float:
        app = self.app
        if not app._music_playing:
            return 0.0
        if app._music_paused:
            pos = (
                app._music_pause_start - app._music_start_time - app._music_paused_total
            )
            return max(0.0, float(pos))
        now = time.monotonic()
        pos = now - app._music_start_time - app._music_paused_total
        return max(0.0, float(pos))

    def get_length(self) -> float:
        app = self.app
        path = self.get_current_path()
        if not path:
            return 0.0
        if path in app._music_length_cache:
            return app._music_length_cache[path]
        try:
            sound = pygame.mixer.Sound(path)
            length = float(sound.get_length())
            app._music_length_cache[path] = length
            return length
        except pygame.error:
            return 0.0

    def seek(self, seconds: float) -> None:
        app = self.app
        if not app._music_playlist:
            return
        if seconds < 0:
            seconds = 0.0
        length = self.get_length()
        if length > 0:
            seconds = min(seconds, length - 0.1)
        self.start(from_seek=True, start_pos=float(seconds))

    def start(self, from_seek: bool = False, start_pos: float = 0.0) -> bool:
        """开始音乐播放"""
        app = self.app
        if not pygame.mixer.get_init():
            self.init_backend()
        if not pygame.mixer.get_init():
            return False

        try:
            pygame.mixer.music.load(app._music_playlist[app._music_index])
            if start_pos > 0:
                pygame.mixer.music.play(start=start_pos)
            else:
                pygame.mixer.music.play()
        except pygame.error as e:
            print(f"音乐播放失败: {e}")
            if start_pos > 0:
                try:
                    pygame.mixer.music.play()
                except pygame.error as retry_error:
                    print(f"音乐跳转失败: {retry_error}")
                    return False
            else:
                return False

        app._last_frames = None
        app._last_delays = None
        app._music_playing = True
        app._music_paused = False
        app._music_start_time = time.monotonic() - float(start_pos)
        app._music_pause_start = 0.0
        app._music_paused_total = 0.0

        app.animation.ensure_music_frames()
        app.animation.switch_to_music_animation()
        app._music_after_id = app.root.after(500, self._check_end)
        return True

    def stop(self) -> None:
        """停止音乐播放"""
        app = self.app
        if not app._music_playing:
            return

        try:
            pygame.mixer.music.stop()
        except pygame.error as e:
            print(f"停止音乐失败: {e}")

        app._music_playing = False
        app._music_paused = False
        app._music_start_time = 0.0
        app._music_pause_start = 0.0
        app._music_paused_total = 0.0

        app.animation.restore_animation_after_music()
        if hasattr(app, "music_panel") and app.music_panel:
            app.music_panel.hide()

    def pause(self) -> None:
        """暂停音乐"""
        app = self.app
        if not app._music_playing or app._music_paused:
            return
        try:
            pygame.mixer.music.pause()
        except pygame.error as e:
            print(f"暂停音乐失败: {e}")
            return
        app._music_paused = True
        app._music_pause_start = time.monotonic()

    def resume(self) -> None:
        """恢复音乐"""
        app = self.app
        if not app._music_playing or not app._music_paused:
            return
        try:
            pygame.mixer.music.unpause()
        except pygame.error as e:
            print(f"恢复音乐失败: {e}")
            return
        pause_duration = time.monotonic() - app._music_pause_start
        app._music_paused_total += max(0.0, float(pause_duration))
        app._music_pause_start = 0.0
        app._music_paused = False

    def _check_end(self) -> None:
        """检查音乐是否播放完毕"""
        app = self.app
        app._music_after_id = None
        if not app._music_playing:
            return
        if app._music_paused:
            app._music_after_id = app.root.after(500, self._check_end)
            return

        if not pygame.mixer.music.get_busy():
            if app._music_playlist:
                app._music_index = (app._music_index + 1) % len(app._music_playlist)
                pygame.mixer.music.load(app._music_playlist[app._music_index])
                pygame.mixer.music.play()
                app._music_start_time = time.monotonic()
                app._music_pause_start = 0.0
                app._music_paused_total = 0.0

        app._music_after_id = app.root.after(500, self._check_end)

    def _load_playlist(self) -> list[str]:
        music_dir = Path(resource_path("assets/music"))
        if not music_dir.exists():
            return []
        return sorted(str(p) for p in music_dir.glob("*.mp3"))
