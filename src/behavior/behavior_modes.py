"""行为模式参数配置"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.constants import (
    BEHAVIOR_MODE_ACTIVE,
    BEHAVIOR_MODE_CLINGY,
    BEHAVIOR_MODE_QUIET,
    REST_CHANCE,
    STOP_CHANCE,
    TARGET_CHANGE_MAX,
    TARGET_CHANGE_MIN,
)


@dataclass(frozen=True)
class BehaviorParams:
    follow_override: Optional[bool]
    stop_chance: Optional[float]
    rest_chance: Optional[float]
    target_min: Optional[int]
    target_max: Optional[int]
    speed_mul: float
    min_move_ticks: int


def get_behavior_params(mode: str) -> BehaviorParams:
    """根据模式返回行为参数"""
    if mode == BEHAVIOR_MODE_QUIET:
        return BehaviorParams(
            follow_override=False,
            stop_chance=min(STOP_CHANCE * 2.0, 0.9),
            rest_chance=min(REST_CHANCE * 1.5, 0.95),
            target_min=int(TARGET_CHANGE_MIN * 1.6),
            target_max=int(TARGET_CHANGE_MAX * 1.6),
            speed_mul=0.7,
            min_move_ticks=0,
        )

    if mode == BEHAVIOR_MODE_CLINGY:
        return BehaviorParams(
            follow_override=True,
            stop_chance=max(STOP_CHANCE * 0.3, 0.0001),
            rest_chance=max(REST_CHANCE * 0.3, 0.05),
            target_min=int(TARGET_CHANGE_MIN * 0.7),
            target_max=int(TARGET_CHANGE_MAX * 0.7),
            speed_mul=1.1,
            min_move_ticks=10,
        )

    # 默认活泼模式
    return BehaviorParams(
        follow_override=None,
        stop_chance=None,
        rest_chance=0.08,
        target_min=None,
        target_max=None,
        speed_mul=1.0,
        min_move_ticks=18,
    )
