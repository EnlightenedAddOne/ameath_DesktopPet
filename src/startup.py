"""开机自启管理模块"""

import os
import sys
from typing import Optional

from src.constants import RUN_KEY, VALUE_NAME


def get_startup_executable_path() -> Optional[str]:
    """获取注册表中保存的 exe 路径

    Returns:
        注册表中的路径或 None
    """
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ
        ) as reg_key:
            return winreg.QueryValueEx(reg_key, VALUE_NAME)[0]
    except (OSError, FileNotFoundError):
        return None


def set_auto_startup(enable: bool) -> bool:
    """设置开机自启

    Args:
        enable: 是否启用

    Returns:
        是否成功
    """
    # 检测程序是否打包成 exe
    if getattr(sys, "frozen", False):
        # 打包后的 exe，使用 exe 本身路径
        executable_path = sys.executable
        startup_cmd = f'"{executable_path}"'
    else:
        # 开发的 py 文件，使用 pythonw 启动
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Python\PythonCore\3.*\InstallPath",
                0,
                winreg.KEY_READ,
            ) as reg_key:
                python_path, _ = winreg.QueryValueEx(reg_key, "InstallPath")
                executable_path = os.path.join(python_path, "pythonw.exe")
        except (OSError, FileNotFoundError):
            executable_path = "pythonw"

        startup_cmd = f'{executable_path} "{os.path.abspath(__file__)}"'

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_ALL_ACCESS
        ) as reg_key:
            if enable:
                winreg.SetValueEx(reg_key, VALUE_NAME, 0, winreg.REG_SZ, startup_cmd)
            else:
                try:
                    winreg.DeleteValue(reg_key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except (OSError, PermissionError) as e:
        print(f"设置开机自启失败: {e}")
        return False


def check_and_fix_startup() -> bool:
    """检查并修复开机自启路径（exe 移动后自动修复）

    Returns:
        是否进行了修复
    """
    if not getattr(sys, "frozen", False):
        return False

    saved_path = get_startup_executable_path()
    current_path = f'"{sys.executable}"'

    if saved_path and saved_path != current_path:
        print("检测到 exe 位置已变更，自动更新开机自启...")
        return set_auto_startup(True)

    return False
