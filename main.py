"""Ameath 桌面宠物 - 启动入口"""

from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap() -> None:
    base_dir = Path(__file__).resolve().parent
    src_dir = base_dir / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from src.main import main as app_main

    app_main()


if __name__ == "__main__":
    _bootstrap()
