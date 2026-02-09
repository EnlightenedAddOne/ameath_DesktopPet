import tkinter as tk
from PIL import Image, ImageTk
import itertools
import random
import os
import json
import ctypes
import sys


# ============ PyInstaller 资源路径处理 ============
def resource_path(relative_path):
    """获取打包后的资源绝对路径"""
    try:
        # PyInstaller 创建的临时目录
        base_path = sys._MEIPASS  # type: ignore
    except AttributeError:
        # 开发环境
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ============ 配置 ============
GIF_DIR = "gifs"
SCALE_OPTIONS = [0.3, 0.4, 0.5, 0.6, 0.7]  # 缩放档位
DEFAULT_SCALE_INDEX = 2  # 默认0.5
SPEED_X = 3
SPEED_Y = 2
TRANSPARENT_COLOR = "pink"
STOP_CHANCE = 0.005  # 每帧停下的概率（约每秒0.3次）
STOP_DURATION_MIN = 2000  # 最小停止时间(ms)
STOP_DURATION_MAX = 5000  # 最大停止时间(ms)

# 帧率配置（性能优化）
MOVE_INTERVAL = 30  # 移动更新间隔(ms) ≈33fps
JITTER_INTERVAL = 5  # 抖动更新间隔(帧数) 每5帧更新一次随机抖动

# 运动配置
EDGE_ESCAPE_CHANCE = 0.3  # 撞边后直接消失概率
RESPAWN_MARGIN = 50  # 重生在屏幕外多少像素
TARGET_CHANGE_MIN = 200  # 目标点最小帧数（约4秒）
TARGET_CHANGE_MAX = 500  # 目标点最大帧数（约10秒）
OUTSIDE_TARGET_CHANCE = 0.4  # 目标点在屏幕外的概率
FOLLOW_DISTANCE = 80  # 跟随鼠标保持的距离
INERTIA_FACTOR = 0.95  # 惯性因子
INTENT_FACTOR = 0.05  # 意图因子
JITTER = 0.15  # 随机抖动幅度

# 状态机配置
MOTION_WANDER = "wander"  # 随机游荡
MOTION_FOLLOW = "follow"  # 跟随鼠标
MOTION_CURIOUS = "curious"  # 好奇：近距离观察
MOTION_REST = "rest"  # 休息：停下不动

# 状态参数
REST_CHANCE = 0.6  # 到达目标后休息的概率
REST_DURATION_MIN = 1000  # 休息最小时间(ms)
REST_DURATION_MAX = 3000  # 休息最大时间(ms)
REST_DISTANCE = 20  # 到达目标的判定距离

# 跟随参数
FOLLOW_START_DIST = 200  # 开始跟随的距离
FOLLOW_STOP_DIST = 60  # 停止跟随/好奇的距离

# 速度倍率
SPEED_WANDER = 0.8  # 游荡速度
SPEED_FOLLOW = 1.2  # 跟随速度
SPEED_CURIOUS = 0.5  # 好奇速度（慢）

CONFIG_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "ameath_config.json"
)

# Windows API 常量
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020


# ==============================


def load_config():
    """加载配置"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "scale_index": DEFAULT_SCALE_INDEX,
            "auto_startup": False,
            "click_through": True,
            "follow_mouse": False,
        }


def save_config(config):
    """保存配置"""
    config_dir = os.path.dirname(CONFIG_FILE)
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def set_auto_startup(enable):
    """设置开机自启"""
    key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    value_name = "DesktopPet"

    # 检测程序是否打包成exe
    if getattr(sys, "frozen", False):
        # 打包后的exe，使用exe本身路径
        executable_path = sys.executable
    else:
        # 开发的py文件，使用pythonw启动
        import winreg

        # 获取pythonw完整路径
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Python\PythonCore\3.*\InstallPath",
                0,
                winreg.KEY_READ,
            ) as reg_key:
                python_path, _ = winreg.QueryValueEx(reg_key, "InstallPath")
                executable_path = os.path.join(python_path, "pythonw.exe")
        except Exception:
            # 回退到PATH中的pythonw
            executable_path = "pythonw"
        executable_path = f'{executable_path} "{os.path.abspath(__file__)}"'

    # 实际设置的启动命令
    if getattr(sys, "frozen", False):
        startup_cmd = f'"{executable_path}"'
    else:
        startup_cmd = executable_path

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_ALL_ACCESS
        ) as reg_key:
            if enable:
                winreg.SetValueEx(reg_key, value_name, 0, winreg.REG_SZ, startup_cmd)
            else:
                try:
                    winreg.DeleteValue(reg_key, value_name)
                except FileNotFoundError:
                    pass
    except Exception as e:
        print(f"设置开机自启失败: {e}")


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
    frame = None
    for i in itertools.count():
        try:
            gif.seek(i)
            frame = gif.convert("RGBA")
            w, h = frame.size
            new_w, new_h = int(w * scale), int(h * scale)
            # 确保缩放后尺寸有效
            if new_w <= 0 or new_h <= 0:
                new_w = max(1, new_w)
                new_h = max(1, new_h)
            resized = frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
            photoimage_frames.append(ImageTk.PhotoImage(resized))
            pil_frames.append(resized)
            delays.append(gif.info.get("duration", 80))
        except EOFError:
            break
    # 确保至少有一帧
    if not photoimage_frames and frame is not None:
        photoimage_frames.append(
            ImageTk.PhotoImage(frame.resize((100, 100), Image.Resampling.LANCZOS))
        )
        pil_frames.append(frame.resize((100, 100), Image.Resampling.LANCZOS))
        delays.append(80)
    return photoimage_frames, delays, pil_frames


class DesktopGif:
    from typing import Any

    app: Any = None  # 用于系统托盘

    def __init__(self, root):
        self.root = root
        self._request_quit = False  # 退出标志（主线程统一收尾）

        # 加载配置
        config = load_config()
        self.scale_index = config.get("scale_index", DEFAULT_SCALE_INDEX)
        self.auto_startup = config.get("auto_startup", False)
        self.scale = SCALE_OPTIONS[self.scale_index]

        root.overrideredirect(True)
        root.attributes("-topmost", True)  # 默认顶层
        root.config(bg=TRANSPARENT_COLOR)
        root.attributes("-transparentcolor", TRANSPARENT_COLOR)

        # ---------- 加载所有GIF ----------
        # 加载move.gif (使用 resource_path 支持打包)
        move_path = resource_path(os.path.join(GIF_DIR, "move.gif"))
        self.move_frames, self.move_delays, self.move_pil_frames = load_gif_frames(
            move_path, self.scale
        )
        # 加载翻转的move帧（向左）
        self.move_frames_left = flip_frames(self.move_pil_frames)

        # 加载idle1~5.gif
        self.idle_gifs = []
        for i in range(1, 6):
            idle_path = resource_path(os.path.join(GIF_DIR, f"idle{i}.gif"))
            frames, delays, _ = load_gif_frames(idle_path, self.scale)
            self.idle_gifs.append((frames, delays))

        # 当前状态
        self.current_frames = self.move_frames
        self.current_delays = self.move_delays
        self.is_moving = True
        self.is_paused = False  # 暂停状态
        self.moving_right = True  # 当前移动方向
        self.frame_index = 0
        self.dragging = False  # 拖动状态
        self.drag_start_x = 0
        self.drag_start_y = 0

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

        # 加载鼠标穿透配置并设置
        config = load_config()
        self.click_through = config.get("click_through", True)
        self.follow_mouse = config.get("follow_mouse", False)
        self.set_click_through(self.click_through)

        self.screen_w = root.winfo_screenwidth()
        self.screen_h = root.winfo_screenheight()

        self.vx = SPEED_X
        self.vy = SPEED_Y

        # 运动系统：目标点和计时器（立即设置一个随机目标，不要当前位置）
        self.target_x, self.target_y = self.get_random_target()
        self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)

        # 状态机变量
        self.motion_state = MOTION_WANDER  # 当前运动状态
        self.rest_timer = 0  # 休息计时器

        # 绑定拖动事件
        self.label.bind("<ButtonPress-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.do_drag)
        self.label.bind("<ButtonRelease-1>", self.stop_drag)

        self.animate()
        self.move()

        # 获取正确的窗口句柄
        self.root.update_idletasks()
        self.hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())

        # 启动轻量级置顶轮询（替代Shell Hook）
        self.root.after(2000, self.ensure_topmost)

        # 启动退出轮询（主线程统一收尾）
        self.root.after(100, self.check_quit)

    def ensure_topmost(self):
        """轻量级置顶轮询（替代Shell Hook）"""
        if not self.is_paused:  # 只在非暂停时确保置顶
            try:
                ctypes.windll.user32.SetWindowPos(
                    self.hwnd,
                    HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
                )
            except:
                pass
        self.root.after(2000, self.ensure_topmost)

    def check_quit(self):
        """主线程轮询退出标志（确保托盘在主线程正确销毁）"""
        if self._request_quit:
            try:
                if hasattr(self, "app") and self.app:
                    self.app.stop()  # 在主线程 stop 托盘
            except:
                pass
            self.root.destroy()
            return
        self.root.after(100, self.check_quit)

    def set_click_through(self, enable):
        """设置鼠标穿透"""
        try:
            # 动态获取窗口句柄
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enable:
                ctypes.windll.user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT
                )
            else:
                ctypes.windll.user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT
                )
        except Exception as e:
            print(f"设置鼠标穿透失败: {e}")

    def do_drag(self, event):
        """拖动中"""
        if self.dragging:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.x += dx
            self.y += dy
            self.root.geometry(f"+{int(self.x)}+{int(self.y)}")

    def stop_drag(self, event):
        """停止拖动"""
        self.dragging = False

    def set_scale(self, index):
        """设置缩放"""
        self.scale_index = index
        self.scale = SCALE_OPTIONS[index]
        config = load_config()
        config["scale_index"] = index
        save_config(config)

        # 重新加载GIF (使用 resource_path 支持打包)
        move_path = resource_path(os.path.join(GIF_DIR, "move.gif"))
        result = load_gif_frames(move_path, self.scale)
        if result[0]:  # 确保有帧
            self.move_frames, self.move_delays, self.move_pil_frames = result
            self.move_frames_left = flip_frames(self.move_pil_frames)
        else:
            print("加载move.gif失败")
            return

        self.idle_gifs = []
        for i in range(1, 6):
            idle_path = resource_path(os.path.join(GIF_DIR, f"idle{i}.gif"))
            result = load_gif_frames(idle_path, self.scale)
            if result[0]:
                self.idle_gifs.append((result[0], result[1]))

        # 确保有idle帧可用
        if not self.idle_gifs:
            self.idle_gifs.append((self.move_frames, self.move_delays))

        # 更新窗口大小
        if self.move_frames:
            self.w = self.move_frames[0].width()
            self.h = self.move_frames[0].height()
            self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

        # 重置帧索引，切换到move帧
        self.frame_index = 0
        self.current_frames = (
            self.move_frames if self.moving_right else self.move_frames_left
        )
        self.current_delays = self.move_delays

    def toggle_pause(self):
        """切换暂停/继续"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            # 暂停：停止移动，切换到idle动画
            self.is_moving = False
            frames, delays = random.choice(self.idle_gifs)
            self.current_frames = frames
            self.current_delays = delays
            self.frame_index = 0
        else:
            # 继续：恢复移动
            self.is_moving = True
            self.current_frames = (
                self.move_frames if self.moving_right else self.move_frames_left
            )
            self.current_delays = self.move_delays
            self.frame_index = 0

    def start_drag(self, event):
        """开始拖动（鼠标穿透关闭时才可用）"""
        if self.click_through:
            return
        self.dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def switch_to_idle(self):
        """切换到随机idle状态（随机停下功能）"""
        # 如果是暂停状态，不处理
        if self.is_paused:
            return
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
        # 如果是暂停状态，不处理
        if self.is_paused:
            return
        self.is_moving = True
        self.current_frames = (
            self.move_frames if self.moving_right else self.move_frames_left
        )
        self.current_delays = self.move_delays
        self.frame_index = 0

    # ============ 运动系统方法 ============

    def get_random_target(self):
        """获取随机目标点（偶尔在屏幕外，触发边缘效果）"""
        # 使用配置的概率，让宠物尝试冲边界
        if random.random() < OUTSIDE_TARGET_CHANCE:
            side = random.choice(["left", "right", "top", "bottom"])
            margin = RESPAWN_MARGIN + 50  # 比重生距离再远一点
            if side == "left":
                return (-margin, random.randint(0, self.screen_h - self.h))
            elif side == "right":
                return (
                    self.screen_w + margin,
                    random.randint(0, self.screen_h - self.h),
                )
            elif side == "top":
                return (random.randint(0, self.screen_w - self.w), -margin)
            else:  # bottom
                return (
                    random.randint(0, self.screen_w - self.w),
                    self.screen_h + margin,
                )
        else:
            return (
                random.randint(0, self.screen_w - self.w),
                random.randint(0, self.screen_h - self.h),
            )

    def get_follow_target(self):
        """获取跟随鼠标的目标点"""
        mx = self.root.winfo_pointerx()
        my = self.root.winfo_pointery()
        # 保持一定距离，不要贴脸
        offset = FOLLOW_DISTANCE
        tx = mx + random.randint(-offset, offset)
        ty = my + random.randint(-offset, offset)
        # 限制在屏幕内
        tx = max(0, min(self.screen_w - self.w, tx))
        ty = max(0, min(self.screen_h - self.h, ty))
        return tx, ty

    def respawn_from_edge(self):
        """从屏幕边缘外侧重生"""
        side = random.choice(["left", "right", "top", "bottom"])
        if side == "left":
            self.x = -RESPAWN_MARGIN
            self.y = random.randint(0, self.screen_h - self.h)
        elif side == "right":
            self.x = self.screen_w + RESPAWN_MARGIN
            self.y = random.randint(0, self.screen_h - self.h)
        elif side == "top":
            self.y = -RESPAWN_MARGIN
            self.x = random.randint(0, self.screen_w - self.w)
        else:  # bottom
            self.y = self.screen_h + RESPAWN_MARGIN
            self.x = random.randint(0, self.screen_w - self.w)

        # 给一点入场速度
        self.vx = random.choice([-3, 3])
        self.vy = random.randint(-2, 2)

    def handle_edge(self):
        """处理边缘：反弹或出屏重生"""
        escaped = False

        # 检测是否出屏
        if self.x < -self.w or self.x > self.screen_w:
            escaped = True
        if self.y < -self.h or self.y > self.screen_h:
            escaped = True

        if escaped:
            if random.random() < EDGE_ESCAPE_CHANCE:
                self.respawn_from_edge()
                return True
            else:
                # 反弹
                self.vx = -self.vx
                self.vy = -self.vy
                # 拉回屏幕内
                self.x = max(0, min(self.screen_w - self.w, self.x))
                self.y = max(0, min(self.screen_h - self.h, self.y))
        return False

    # ============ 动画方法 ============

    def animate(self):
        if not self.current_frames:
            self.root.after(100, self.animate)
            return
        self.label.config(image=self.current_frames[self.frame_index])
        delay = self.current_delays[self.frame_index] if self.current_delays else 100

        self.frame_index = (self.frame_index + 1) % len(self.current_frames)
        self.root.after(delay, self.animate)

    def move(self):
        """运动状态机主循环（性能优化版）"""
        # 暂停时停止所有运动
        if self.is_paused:
            self.root.after(100, self.move)
            return

        # ============ 休息状态 ============
        if self.motion_state == MOTION_REST:
            self.rest_timer -= MOVE_INTERVAL
            if self.rest_timer <= 0:
                # 休息结束，恢复游荡
                self.motion_state = MOTION_WANDER
                self.target_x, self.target_y = self.get_random_target()
                self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)
                self.switch_to_move()
            self.root.after(MOVE_INTERVAL, self.move)
            return

        # ============ 鼠标位置缓存 ============
        mx = self.root.winfo_pointerx()
        my = self.root.winfo_pointery()
        mouse_moved = (mx, my) != getattr(self, "_last_mouse", (mx, my))
        self._last_mouse = (mx, my)

        # ============ 计算到目标的距离 ============
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        # ============ 状态判断与切换 ============

        # 跟随模式：根据距离切换follow/curious
        if self.follow_mouse:
            dist_mouse = ((mx - self.x) ** 2 + (my - self.y) ** 2) ** 0.5

            if dist_mouse > FOLLOW_START_DIST:
                self.motion_state = MOTION_FOLLOW
            elif dist_mouse < FOLLOW_STOP_DIST:
                self.motion_state = MOTION_CURIOUS

        # 游荡模式：到达目标后决定是否休息
        elif self.motion_state == MOTION_WANDER and dist < REST_DISTANCE:
            if random.random() < REST_CHANCE:
                # 休息一下
                self.motion_state = MOTION_REST
                self.rest_timer = random.randint(REST_DURATION_MIN, REST_DURATION_MAX)
                self.switch_to_idle()
                self.root.after(MOVE_INTERVAL, self.move)
                return
            else:
                # 继续游荡，换个目标
                self.target_x, self.target_y = self.get_random_target()
                self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)

        # ============ 定时更换目标（仅游荡模式） ============
        if self.motion_state == MOTION_WANDER:
            self.target_timer -= 1
            if self.target_timer <= 0:
                self.target_x, self.target_y = self.get_random_target()
                self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)

        # ============ 计算速度倍率 ============
        if self.motion_state == MOTION_WANDER:
            speed_mul = SPEED_WANDER
        elif self.motion_state == MOTION_FOLLOW:
            speed_mul = SPEED_FOLLOW
        elif self.motion_state == MOTION_CURIOUS:
            speed_mul = SPEED_CURIOUS
        else:
            speed_mul = 1.0

        # ============ 跟随/好奇模式：只在鼠标移动时更新目标 ============
        if self.motion_state in (MOTION_FOLLOW, MOTION_CURIOUS):
            if mouse_moved:  # 只有鼠标移动时才更新目标
                if self.motion_state == MOTION_FOLLOW:
                    offset = FOLLOW_DISTANCE
                else:  # curious
                    offset = FOLLOW_STOP_DIST
                self.target_x = mx + random.randint(-offset, offset)
                self.target_y = my + random.randint(-offset, offset)

                # 重新计算距离
                dx = self.target_x - self.x
                dy = self.target_y - self.y
                dist = max(1, (dx * dx + dy * dy) ** 0.5)

        # ============ 朝目标移动（惯性 + 意图） ============
        desired_vx = dx / dist * SPEED_X * speed_mul
        desired_vy = dy / dist * SPEED_Y * speed_mul

        # 惯性融合
        self.vx = self.vx * INERTIA_FACTOR + desired_vx * INTENT_FACTOR
        self.vy = self.vy * INERTIA_FACTOR + desired_vy * INTENT_FACTOR

        # ============ 抖动降频：每N帧更新一次 ============
        if not hasattr(self, "_move_tick"):
            self._move_tick = 0
        self._move_tick += 1

        if self._move_tick % JITTER_INTERVAL == 0:
            self._jitter_x = random.uniform(-JITTER, JITTER)
            self._jitter_y = random.uniform(-JITTER, JITTER)
        self.vx += getattr(self, "_jitter_x", 0)
        self.vy += getattr(self, "_jitter_y", 0)

        # 应用移动
        self.x += self.vx
        self.y += self.vy

        # ============ 边缘处理 ============
        if not self.handle_edge():
            # 没出屏时才检查边界碰撞
            hit_edge = False
            if self.x <= 0:
                self.x = 0
                self.vx = abs(self.vx)  # 向右反弹
                hit_edge = True
            elif self.x + self.w >= self.screen_w:
                self.x = self.screen_w - self.w
                self.vx = -abs(self.vx)  # 向左反弹
                hit_edge = True

            if self.y <= 0:
                self.y = 0
                self.vy = abs(self.vy)  # 向下
                hit_edge = True
            elif self.y + self.h >= self.screen_h:
                self.y = self.screen_h - self.h
                self.vy = -abs(self.vy)  # 向上
                hit_edge = True

            # 撞边时更新方向状态
            new_moving_right = self.vx > 0.5
            new_moving_left = self.vx < -0.5

            if new_moving_right and not self.moving_right:
                self.moving_right = True
                self.current_frames = self.move_frames
                self.current_delays = self.move_delays
                self.frame_index = 0
            elif new_moving_left and self.moving_right:
                self.moving_right = False
                self.current_frames = self.move_frames_left
                self.current_delays = self.move_delays
                self.frame_index = 0

        # 只在位置明显变化时更新geometry
        ix, iy = int(self.x), int(self.y)
        last_pos = getattr(self, "_last_pos", None)
        if (ix, iy) != last_pos:
            self.root.geometry(f"+{ix}+{iy}")
            self._last_pos = (ix, iy)

        self.root.after(MOVE_INTERVAL, self.move)


if __name__ == "__main__":
    root = tk.Tk()

    # 尝试导入pystray
    try:
        import pystray
        from PIL import Image as PILImage

        app = DesktopGif(root)
        # 不隐藏窗口，直接显示

        # 创建托盘图标（使用ameath.gif）
        try:
            icon_gif = Image.open(resource_path("gifs/ameath.gif"))
            icon_gif.seek(0)  # 取第一帧
            icon_image = icon_gif.convert("RGBA")
            icon_image = icon_image.resize((64, 64), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"加载托盘图标失败，使用默认图标: {e}")
            icon_image = PILImage.new("RGB", (64, 64), color="pink")

        def on_toggle_startup(icon, item):
            """切换开机自启"""
            app.auto_startup = not app.auto_startup
            set_auto_startup(app.auto_startup)
            config = load_config()
            config["auto_startup"] = app.auto_startup
            save_config(config)
            icon.menu = create_menu(app)

        def on_toggle_visible(icon, item):
            """切换隐藏/显示"""
            if app.root.state() == "withdrawn":
                app.root.deiconify()
            else:
                app.root.withdraw()
            icon.menu = create_menu(app)

        def on_toggle_pause(icon, item):
            """切换暂停/继续"""
            app.toggle_pause()
            icon.menu = create_menu(app)

        def on_set_scale(icon, item, index):
            """设置缩放"""
            app.set_scale(index)
            icon.menu = create_menu(app)

        def on_quit(icon):
            """退出（只发信号，主线程统一收尾）"""
            app._request_quit = True

        def on_toggle_click_through(icon, item):
            """切换鼠标穿透"""
            app.click_through = not app.click_through
            app.set_click_through(app.click_through)
            config = load_config()
            config["click_through"] = app.click_through
            save_config(config)
            icon.menu = create_menu(app)

        def on_toggle_follow(icon, item):
            """切换跟随鼠标"""
            app.follow_mouse = not app.follow_mouse
            config = load_config()
            config["follow_mouse"] = app.follow_mouse
            save_config(config)
            icon.menu = create_menu(app)

        def on_scale_0(icon, item):
            on_set_scale(icon, item, 0)

        def on_scale_1(icon, item):
            on_set_scale(icon, item, 1)

        def on_scale_2(icon, item):
            on_set_scale(icon, item, 2)

        def on_scale_3(icon, item):
            on_set_scale(icon, item, 3)

        def on_scale_4(icon, item):
            on_set_scale(icon, item, 4)

        def create_menu(app_instance):
            """动态创建菜单"""
            # 缩放子菜单
            scale_handlers = [
                on_scale_0,
                on_scale_1,
                on_scale_2,
                on_scale_3,
                on_scale_4,
            ]
            scale_items = []
            for i in range(len(SCALE_OPTIONS)):
                scale_items.append(
                    pystray.MenuItem(
                        f"{SCALE_OPTIONS[i]}x",
                        scale_handlers[i],
                        checked=lambda it, idx=i: app_instance.scale_index == idx,
                        radio=True,
                    )
                )
            scale_menu = pystray.Menu(*scale_items)

            return (
                pystray.MenuItem(
                    "隐藏" if app_instance.root.state() == "normal" else "显示",
                    on_toggle_visible,
                ),
                pystray.MenuItem(
                    "暂停" if not app_instance.is_paused else "继续",
                    on_toggle_pause,
                ),
                pystray.MenuItem(
                    "跟随鼠标",
                    on_toggle_follow,
                    checked=lambda it: app_instance.follow_mouse,
                ),
                pystray.MenuItem(
                    "鼠标穿透",
                    on_toggle_click_through,
                    checked=lambda it: app_instance.click_through,
                ),
                pystray.MenuItem(
                    "开机自启",
                    on_toggle_startup,
                    checked=lambda it: app_instance.auto_startup,
                ),
                pystray.MenuItem("缩放", scale_menu),
                pystray.MenuItem("退出", on_quit),
            )

        # 创建菜单
        menu = create_menu(app)

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
