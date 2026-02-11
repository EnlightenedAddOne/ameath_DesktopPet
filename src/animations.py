"""动画处理模块"""

import itertools
import time
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageTk

from src.constants import GIF_DIR
from src.utils import resource_path

# 类型别名
FrameSet = Tuple[List[ImageTk.PhotoImage], List[int], List[Image.Image]]


def load_gif_frames_raw(filename: str) -> Tuple[List[Image.Image], List[int]]:
    """加载 GIF 原始帧（不缩放）

    Args:
        filename: GIF 文件名（相对于 gifs 目录）

    Returns:
        (PIL帧列表, 延迟列表)
    """
    path = Path(resource_path(str(GIF_DIR))) / filename
    start_time = time.perf_counter()
    pil_frames: List[Image.Image] = []
    delays: List[int] = []

    try:
        gif = Image.open(path)
    except (FileNotFoundError, IOError) as e:
        print(f"无法加载 GIF 文件 {filename}: {e}")
        return [], []

    frame_count = 0
    for i in itertools.count():
        try:
            gif.seek(i)
            frame = gif.convert("RGBA")
            pil_frames.append(frame)
            delays.append(gif.info.get("duration", 80))
            frame_count += 1
        except EOFError:
            break

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    print(f"GIF原始加载耗时 {elapsed_ms}ms | {filename} | frames={frame_count}")

    return pil_frames, delays


def load_gif_frames(filename: str, scale: float = 1.0) -> FrameSet:
    """加载并缩放 GIF 文件

    Args:
        filename: GIF 文件名（相对于 gifs 目录）
        scale: 缩放比例

    Returns:
        (PhotoImage帧列表, 延迟列表, PIL帧列表)
    """
    photoimage_frames: List[ImageTk.PhotoImage] = []
    pil_frames: List[Image.Image] = []
    delays: List[int] = []

    path = Path(resource_path(str(GIF_DIR))) / filename

    start_time = time.perf_counter()
    try:
        gif = Image.open(path)
    except (FileNotFoundError, IOError) as e:
        print(f"无法加载 GIF 文件 {filename}: {e}")
        return [], [], []

    frame = None
    frame_count = 0
    for i in itertools.count():
        try:
            gif.seek(i)
            frame = gif.convert("RGBA")
            w, h = frame.size

            # 确保缩放后尺寸有效
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))

            resized = frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
            photoimage_frames.append(ImageTk.PhotoImage(resized))
            pil_frames.append(resized)
            delays.append(gif.info.get("duration", 80))
            frame_count += 1
        except EOFError:
            break

    # 确保至少有一帧
    if not photoimage_frames and frame is not None:
        fallback = frame.resize((100, 100), Image.Resampling.LANCZOS)
        photoimage_frames.append(ImageTk.PhotoImage(fallback))
        pil_frames.append(fallback)
        delays.append(80)

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    print(
        f"GIF加载耗时 {elapsed_ms}ms | {filename} | scale={scale} | frames={frame_count}"
    )

    return photoimage_frames, delays, pil_frames


def flip_frames(frames: List[Image.Image]) -> List[ImageTk.PhotoImage]:
    """水平翻转所有 PIL Image 帧

    Args:
        frames: PIL Image 帧列表

    Returns:
        翻转后的 PhotoImage 列表
    """
    return [
        ImageTk.PhotoImage(img.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
        for img in frames
    ]


def load_all_animations(scale: float) -> dict:
    """加载所有动画资源

    Args:
        scale: 缩放比例

    Returns:
        包含所有动画的字典
    """
    animations = {
        "move": load_gif_frames("move.gif", scale),
        "move_left": None,  # 将通过 flip_frames 生成
        "drag": load_gif_frames("drag.gif", scale),
        "idle": [],
    }

    # 加载待机动画
    for i in range(1, 5):
        idle_frames = load_gif_frames(f"idle{i}.gif", scale)
        if idle_frames[0]:  # 确保有帧
            animations["idle"].append((idle_frames[0], idle_frames[1]))

    # 生成向左移动的动画
    if animations["move"][2]:  # 如果有 PIL 帧
        animations["move_left"] = flip_frames(animations["move"][2])

    return animations
