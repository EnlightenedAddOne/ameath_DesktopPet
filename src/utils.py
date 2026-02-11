"""工具函数模块"""

import os
import sys
from pathlib import Path


def resource_path(relative_path: str) -> str:
    """获取打包后的资源绝对路径

    支持 PyInstaller 打包后的环境和开发环境

    Args:
        relative_path: 相对路径

    Returns:
        绝对路径
    """
    try:
        # PyInstaller 创建的临时目录
        base_path = sys._MEIPASS  # type: ignore
    except AttributeError:
        # 开发环境
        base_path = Path(__file__).resolve().parent.parent
    return str(Path(base_path) / relative_path)


def get_version() -> str:
    """自动获取当前版本

    1. 优先读取 version.txt（打包后）
    2. 回退到 git 标签
    3. 默认为 "dev"

    Returns:
        版本号字符串
    """
    # 1. 优先读取 version.txt
    try:
        version_path = Path(resource_path("version.txt"))
        if version_path.exists():
            version = version_path.read_text(encoding="utf-8").strip()
            if version:
                return version
    except (OSError, IOError):
        pass

    # 2. 尝试从 git 获取
    try:
        import subprocess

        version = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=Path(__file__).parent,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if version:
            return version
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return "dev"


def normalize_version(v: str) -> list:
    """标准化版本号用于比较

    Args:
        v: 版本号字符串

    Returns:
        版本号各部分组成的整数列表
    """
    v = v.lstrip("v")
    if v == "dev" or not v:
        return []
    try:
        return [int(p) for p in v.split(".") if p.isdigit()]
    except ValueError:
        return []


def version_greater_than(v1: str, v2: str) -> bool:
    """比较两个版本号

    Args:
        v1: 版本1
        v2: 版本2

    Returns:
        v1 > v2 返回 True
    """
    parts1 = normalize_version(v1)
    parts2 = normalize_version(v2)
    if not parts1 or not parts2:
        return False

    max_len = max(len(parts1), len(parts2))
    parts1 = parts1 + [0] * (max_len - len(parts1))
    parts2 = parts2 + [0] * (max_len - len(parts2))

    return parts1 > parts2
