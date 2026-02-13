"""动画缓存（从 src/core/pet_core.py 拆分）"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(slots=True)
class AnimationCacheEntry:
    """单个缩放档位的动画缓存"""

    move_frames: list
    move_delays: list
    move_frames_left: list
    idle_gifs: list
    drag_frames: list
    drag_delays: list
    music_frames: list
    music_delays: list


class AnimationCache:
    """按 scale_index 缓存动画资源"""

    def __init__(self) -> None:
        self._cache: dict[int, AnimationCacheEntry] = {}

    def get(self, key: int) -> Optional[AnimationCacheEntry]:
        return self._cache.get(key)

    def set(self, key: int, entry: AnimationCacheEntry) -> None:
        self._prune_keep(key)
        self._cache[key] = entry

    def update_music(self, key: int, music_frames: list, music_delays: list) -> None:
        entry = self._cache.get(key)
        if entry is None:
            return
        entry.music_frames = music_frames
        entry.music_delays = music_delays

    def _prune_keep(self, keep_key: int) -> None:
        for k in list(self._cache.keys()):
            if k != keep_key:
                del self._cache[k]
