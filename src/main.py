"""Ameath 桌面宠物 - 主入口

飞吧，朝向春天
"""

import tkinter as tk

# 必须先启用 DPI 感知
from src.system import enable_dpi_awareness

enable_dpi_awareness()

from src.config import load_config
from src.hotkey import hotkey_manager
from src.pet import DesktopPet
from src.tray import TrayController


def main():
    """主函数"""
    root = tk.Tk()
    root.withdraw()  # 先隐藏窗口，避免闪烁

    # 检查是否跳过更新检查
    config = load_config()

    # 创建宠物实例
    app = DesktopPet(root)

    # 注册全局快捷键
    root.after(100, lambda: hotkey_manager.register_app(app))

    # 创建并启动托盘
    tray = TrayController(app)
    app.tray_controller = tray
    tray.run()

    # 显示窗口
    root.deiconify()

    # 启动主循环
    root.mainloop()


if __name__ == "__main__":
    main()
