"""Ameath 桌面宠物 - 主入口

飞吧，朝向春天
"""

import tkinter as tk

# 必须先启用 DPI 感知
from src.platform.system import enable_dpi_awareness

enable_dpi_awareness()

from src.config import load_config
from src.platform.hotkey import hotkey_manager
from src.core.pet_core import DesktopPet
from src.platform.tray import TrayController


def main():
    """主函数"""
    try:
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
    except KeyboardInterrupt:
        print("\n程序已退出。如果要使用划词翻译功能，请：")
        print("1. 使用 pythonw main.py 或打包后的 exe 运行（无控制台）")
        print("2. 或在浏览器中选中文本后，切换到宠物窗口再长按Ctrl")


if __name__ == "__main__":
    main()
