import tkinter as tk
from PIL import Image, ImageTk
import itertools
import random
import os
import json
import ctypes
import threading
import time

# ============ 配置 ============
GIF_DIR = "gifs"
SCALE = 0.5
SPEED_X = 3
SPEED_Y = 2
TRANSPARENT_COLOR = "pink"
STOP_CHANCE = 0.005  # 每帧停下的概率（约每秒0.3次）
STOP_DURATION_MIN = 2000  # 最小停止时间(ms)
STOP_DURATION_MAX = 5000  # 最大停止时间(ms)
LAYER_TOPMOST = True  # True=窗口最顶层, False=桌面最底层
CONFIG_FILE = "config.json"

# Windows API 常量
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

# 消息钩子常量
WH_SHELL = 10
HSHELL_WINDOWACTIVATED = 4
HSHELL_RUDEAPPACTIVATION = 0x8004

# 全局变量
current_topmost = True  # 当前层级设置


class WinMessageHook:
    """Windows消息钩子，更高效地处理Win+D"""

    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.hook = None
        self.running = True
        self.keep_topmost = True

    def shell_hook(self, nCode, wParam, lParam):
        """Shell钩子回调"""
        if nCode >= 0:
            # 窗口激活事件
            if wParam == HSHELL_WINDOWACTIVATED or wParam == HSHELL_RUDEAPPACTIVATION:
                # 检查目标窗口是否是桌面或任务栏
                try:
                    foreground = ctypes.windll.user32.GetForegroundWindow()
                    class_name = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetClassNameW(foreground, class_name, 256)

                    # 如果前台是WorkerW或Progman（桌面窗口），恢复置顶
                    if "WorkerW" in class_name.value or "Progman" in class_name.value:
                        ctypes.windll.user32.SetWindowPos(
                            self.hwnd,
                            HWND_TOPMOST if self.keep_topmost else HWND_NOTOPMOST,
                            0,
                            0,
                            0,
                            0,
                            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
                        )
                except:
                    pass

        return ctypes.windll.user32.CallNextHookEx(self.hook, nCode, wParam, lParam)

    def start(self):
        """启动钩子"""

        def callback(nCode, wParam, lParam):
            return self.shell_hook(nCode, wParam, lParam)

        self.hook = ctypes.windll.user32.SetWindowsHookExW(WH_SHELL, callback, None, 0)
        if not self.hook:
            return False

        # 消息循环
        msg = ctypes.windll.user32.GetMessageW(None, 0, 0)
        while self.running and msg != 0:
            ctypes.windll.user32.TranslateMessage(msg)
            ctypes.windll.user32.DispatchMessageW(msg)
            msg = ctypes.windll.user32.GetMessageW(None, 0, 0)
        return True

    def stop(self):
        """停止钩子"""
        self.running = False
        if self.hook:
            ctypes.windll.user32.UnhookWindowsHookEx(self.hook)


def start_hook(hwnd):
    """启动消息钩子线程"""
    hook = WinMessageHook(hwnd)
    hook.keep_topmost = current_topmost
    threading.Thread(target=hook.start, daemon=True).start()
    return hook


# ==============================


def load_config():
    """加载配置"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"layer_topmost": LAYER_TOPMOST}


def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def flip_frames(pil_frames):
    """水平翻转所有PIL Image帧，返回PhotoImage"""
    flipped = []
    for img in pil_frames:
        flipped_img = ImageTk.PhotoImage(img.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
        flipped.append(flipped_img)
    return flipped


def load_gif_frames(gif_path, scale=1.0):
    """加载并缩放GIF，返回(photoimage_frames, delays, pil_frames)"""
    photoimage_frames = []
    pil_frames = []
    delays = []
    gif = Image.open(gif_path)
    for i in itertools.count():
        try:
            gif.seek(i)
            frame = gif.convert("RGBA")
            w, h = frame.size
            resized = frame.resize(
                (int(w * scale), int(h * scale)), Image.Resampling.LANCZOS
            )
            photoimage_frames.append(ImageTk.PhotoImage(resized))
            pil_frames.append(resized)
            delays.append(gif.info.get("duration", 80))
        except EOFError:
            break
    return photoimage_frames, delays, pil_frames


class DesktopGif:
    def __init__(self, root):
        self.root = root
        self.app = None  # 用于系统托盘

        # 加载配置
        config = load_config()
        self.layer_topmost = config.get("layer_topmost", LAYER_TOPMOST)

        root.overrideredirect(True)
        root.attributes("-topmost", self.layer_topmost)
        root.config(bg=TRANSPARENT_COLOR)
        root.attributes("-transparentcolor", TRANSPARENT_COLOR)

        # ---------- 加载所有GIF ----------
        # 加载move.gif
        move_path = os.path.join(GIF_DIR, "move.gif")
        self.move_frames, self.move_delays, self.move_pil_frames = load_gif_frames(
            move_path, SCALE
        )
        # 加载翻转的move帧（向左）
        self.move_frames_left = flip_frames(self.move_pil_frames)

        # 加载idle1~5.gif
        self.idle_gifs = []
        for i in range(1, 6):
            idle_path = os.path.join(GIF_DIR, f"idle{i}.gif")
            frames, delays, _ = load_gif_frames(idle_path, SCALE)
            self.idle_gifs.append((frames, delays))

        # 当前状态
        self.current_frames = self.move_frames
        self.current_delays = self.move_delays
        self.is_moving = True
        self.moving_right = True  # 当前移动方向
        self.frame_index = 0

        self.label = tk.Label(root, bg=TRANSPARENT_COLOR, bd=0)
        self.label.pack()

        self.w = self.current_frames[0].width()
        self.h = self.current_frames[0].height()

        # ⚠️ 不要放在 (0,0)
        self.x = 200
        self.y = 200
        root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")

        # 强制刷新，让 winfo_x/y 生效
        root.update_idletasks()

        self.screen_w = root.winfo_screenwidth()
        self.screen_h = root.winfo_screenheight()

        self.vx = SPEED_X
        self.vy = SPEED_Y

        self.animate()
        self.move()

        # 启动Windows消息钩子（应对Win+D）
        self.root.update_idletasks()
        hwnd = ctypes.windll.user32.FindWindowW(None, None)
        start_hook(hwnd)

    def update_layer(self, topmost):
        """更新窗口层级"""
        global current_topmost
        self.layer_topmost = topmost
        current_topmost = topmost
        self.root.attributes("-topmost", topmost)
        config = load_config()
        config["layer_topmost"] = topmost
        save_config(config)

    def switch_to_idle(self):
        """切换到随机idle状态"""
        self.is_moving = False
        frames, delays = random.choice(self.idle_gifs)
        self.current_frames = frames
        self.current_delays = delays
        self.frame_index = 0

        # 随机停止一段时间后恢复移动
        stop_duration = random.randint(STOP_DURATION_MIN, STOP_DURATION_MAX)
        self.root.after(stop_duration, self.switch_to_move)

    def switch_to_move(self):
        """切换到移动状态"""
        self.is_moving = True
        self.current_frames = (
            self.move_frames if self.moving_right else self.move_frames_left
        )
        self.current_delays = self.move_delays
        self.frame_index = 0

    def animate(self):
        self.label.config(image=self.current_frames[self.frame_index])
        delay = self.current_delays[self.frame_index]

        self.frame_index = (self.frame_index + 1) % len(self.current_frames)
        self.root.after(delay, self.animate)

    def move(self):
        if self.is_moving:
            # 随机决定是否停下
            if random.random() < STOP_CHANCE:
                self.switch_to_idle()
            else:
                # 用自己维护的坐标，不再信 winfo_x/y
                self.x += self.vx
                self.y += self.vy

                # 撞墙处理（并拉回边界）
                direction_changed = False
                if self.x <= 0:
                    self.x = 0
                    self.vx = -self.vx
                    direction_changed = True
                elif self.x + self.w >= self.screen_w:
                    self.x = self.screen_w - self.w
                    self.vx = -self.vx
                    direction_changed = True

                if self.y <= 0:
                    self.y = 0
                    self.vy = -self.vy
                elif self.y + self.h >= self.screen_h:
                    self.y = self.screen_h - self.h
                    self.vy = -self.vy

                # 方向改变时切换帧
                if direction_changed:
                    self.moving_right = self.vx > 0
                    if not self.is_moving:
                        self.is_moving = True  # 恢复移动时切换方向
                    self.current_frames = (
                        self.move_frames if self.moving_right else self.move_frames_left
                    )
                    self.current_delays = self.move_delays
                    self.frame_index = 0

                self.root.geometry(f"+{self.x}+{self.y}")

        self.root.after(20, self.move)


if __name__ == "__main__":
    root = tk.Tk()

    # 尝试导入pystray
    try:
        import pystray
        from PIL import Image as PILImage

        app = DesktopGif(root)
        # 不隐藏窗口，直接显示

        # 创建托盘图标
        icon_image = PILImage.new("RGB", (64, 64), color="pink")

        def on_toggle_layer(icon, item):
            """切换层级"""
            new_topmost = not app.layer_topmost
            app.update_layer(new_topmost)
            item.checked = new_topmost
            item.title = "桌面宠物 - " + ("顶层" if new_topmost else "底层")

        def on_quit(icon):
            """退出"""
            icon.stop()
            app.root.destroy()

        # 创建菜单（移除显示窗口选项）
        menu = (
            pystray.MenuItem(
                "切换层级 (当前: 顶层)",
                on_toggle_layer,
                checked=lambda item: app.layer_topmost,
            ),
            pystray.MenuItem("退出", on_quit),
        )

        icon = pystray.Icon("desktop_pet", icon_image, "桌面宠物", menu)
        app.app = icon

        # 延迟启动托盘，让窗口先显示
        root.update_idletasks()
        root.after(500, lambda: icon.run_detached())

        root.mainloop()

    except ImportError:
        # 没有pystray时正常运行窗口
        print("未安装pystray，将只显示窗口。可运行: pip install pystray")
        DesktopGif(root)
        root.mainloop()
