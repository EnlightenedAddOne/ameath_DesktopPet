"""常量定义模块"""

from pathlib import Path
import os

# ============ 路径配置 ============
BASE_DIR = Path(__file__).resolve().parent.parent
GIF_DIR = BASE_DIR / "assets" / "gifs"
CONFIG_FILE = Path(os.environ.get("APPDATA", Path.home())) / "ameath_config.json"

# ============ 显示配置 ============
SCALE_OPTIONS = [0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9]
DEFAULT_SCALE_INDEX = 3
TRANSPARENCY_OPTIONS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
DEFAULT_TRANSPARENCY_INDEX = 0
TRANSPARENT_COLOR = "pink"

# ============ 运动配置 ============
SPEED_X = 3
SPEED_Y = 2
MOVE_INTERVAL = 30  # 移动更新间隔(ms) ≈33fps
JITTER_INTERVAL = 5  # 抖动更新间隔(帧数)
JITTER = 0.15  # 随机抖动幅度
INERTIA_FACTOR = 0.95  # 惯性因子
INTENT_FACTOR = 0.05  # 意图因子

# ============ 行为配置 ============
STOP_CHANCE = 0.0003  # 每帧停下的概率
STOP_DURATION_MIN = 5000  # 最小停止时间(ms)
STOP_DURATION_MAX = 5000  # 最大停止时间(ms)
EDGE_ESCAPE_CHANCE = 0.3  # 撞边后直接消失概率
RESPAWN_MARGIN = 50  # 重生在屏幕外多少像素

# ============ 目标配置 ============
TARGET_CHANGE_MIN = 200  # 目标点最小帧数
TARGET_CHANGE_MAX = 500  # 目标点最大帧数
OUTSIDE_TARGET_CHANCE = 0.4  # 目标点在屏幕外的概率
FOLLOW_DISTANCE = 80  # 跟随鼠标保持的距离

# ============ 状态机配置 ============
MOTION_WANDER = "wander"
MOTION_FOLLOW = "follow"
MOTION_CURIOUS = "curious"
MOTION_REST = "rest"

# ============ 行为模式 ============
BEHAVIOR_MODE_QUIET = "quiet"
BEHAVIOR_MODE_ACTIVE = "active"
BEHAVIOR_MODE_CLINGY = "clingy"

# ============ 番茄钟配置 ============
POMODORO_WORK_MINUTES = 25
POMODORO_REST_MINUTES = 5

# ============ 状态参数 ============
REST_CHANCE = 0.6
REST_DURATION_MIN = 1000
REST_DURATION_MAX = 3000
REST_DISTANCE = 20
STAY_PUT_CHANCE = 0.3

# ============ 跟随参数 ============
FOLLOW_START_DIST = 200
FOLLOW_STOP_DIST = 60

# ============ 速度倍率 ============
SPEED_WANDER = 0.8
SPEED_FOLLOW = 1.2
SPEED_CURIOUS = 0.5

# ============ Windows API 常量 ============
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

# ============ 注册表配置 ============
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "DesktopPet"

# ============ 智能作息配置 ============
# 时间段定义
TIME_MORNING_START = 6  # 早上 6:00
TIME_NOON_START = 11  # 中午 11:00
TIME_AFTERNOON_START = 14  # 下午 14:00
TIME_EVENING_START = 18  # 晚上 18:00
TIME_NIGHT_START = 22  # 夜晚 22:00
TIME_SLEEP_START = 0  # 凌晨 00:00

# 作息行为参数
SLEEP_SPEED_MULTIPLIER = 0.3  # 睡觉时移动速度
SLEEP_STOP_CHANCE = 0.01  # 睡觉时停下概率
NIGHT_IDLE_CHANCE = 0.7  # 夜晚待机概率

# ============ 提醒功能配置 ============
REMINDER_CHANCE = 0.3  # 触发概率降低为30%

REMINDERS = {
    "water": {
        "interval": 60,  # 分钟
        "messages": [
            "记得喝水哦~ 身体是革命的本钱嘛！💧",
            "补充水分很重要！要不要一起喝水呀？",
            "该喝水啦~ 我也在补充能量呢！",
            "水是生命之源哦，快去喝水吧！",
        ],
    },
    "rest": {
        "interval": 90,  # 分钟
        "messages": [
            "休息一下吧~ 眼睛也需要放假呢",
            "眼睛需要休息哦~ 看看远处放松一下吧",
            "起来活动活动嘛，一直坐着对身体不好呢",
            "适当休息才能更有效率哦，要劳逸结合！",
        ],
    },
    "posture": {
        "interval": 120,  # 分钟
        "messages": [
            "注意坐姿哦~ 挺直腰板的样子最帅了！",
            "不要驼背啦~ 良好的体态很重要呢",
            "调整一下坐姿吧，我会一直陪着你的",
            "时刻保持优雅！坐姿也要美美哒~",
        ],
    },
}

# ============ 作者信息 ============
AUTHOR_BILIBILI = "-fugu-"
AUTHOR_EMAIL = "1977184420@qq.com"
GITEE_RELEASES_URL = "https://gitee.com/lzy-buaa-jdi/ameath/releases"

# ============ AI配置 ============
AI_PROVIDER_DEEPSEEK = "deepseek"
AI_PROVIDER_OPENAI = "openai"
AI_PROVIDER_QWEN = "qwen"
AI_PROVIDER_GLM = "glm"
AI_PROVIDER_KIMI = "kimi"
AI_PROVIDER_DOUBAO = "doubao"
AI_PROVIDER_CUSTOM = "custom"

AI_PROVIDERS = [
    AI_PROVIDER_DEEPSEEK,
    AI_PROVIDER_OPENAI,
    AI_PROVIDER_QWEN,
    AI_PROVIDER_GLM,
    AI_PROVIDER_KIMI,
    AI_PROVIDER_DOUBAO,
    AI_PROVIDER_CUSTOM,
]

AI_PROVIDER_NAMES = {
    AI_PROVIDER_DEEPSEEK: "DeepSeek",
    AI_PROVIDER_OPENAI: "OpenAI",
    AI_PROVIDER_QWEN: "千问 (Qwen)",
    AI_PROVIDER_GLM: "智谱GLM",
    AI_PROVIDER_KIMI: "Kimi",
    AI_PROVIDER_DOUBAO: "豆包 (Doubao)",
    AI_PROVIDER_CUSTOM: "自定义第三方API",
}

AI_DEFAULT_MODELS = {
    AI_PROVIDER_DEEPSEEK: "deepseek-chat",
    AI_PROVIDER_OPENAI: "gpt-3.5-turbo",
    AI_PROVIDER_QWEN: "qwen-plus",
    AI_PROVIDER_GLM: "glm-4-flash",
    AI_PROVIDER_KIMI: "moonshot/kimi-k2-0711-preview",
    AI_PROVIDER_DOUBAO: "doubao-1.5-pro-32k",
}

AI_MODELS = {
    AI_PROVIDER_DEEPSEEK: [
        "deepseek-chat",
        "deepseek-reasoner",
    ],
    AI_PROVIDER_OPENAI: [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    AI_PROVIDER_QWEN: [
        "qwen-plus",
        "qwen-max",
        "qwen-turbo",
        "qwen-long",
        "qwen-coder-plus",
        "qwen-coder-turbo",
    ],
    AI_PROVIDER_GLM: [
        "glm-4",
        "glm-4-flash",
        "glm-4-plus",
        "glm-4-air",
        "glm-4-flashx",
    ],
    AI_PROVIDER_KIMI: [
        "moonshot/kimi-k2-0711-preview",
        "moonshot/kimi-k2-turbo-preview",
        "moonshot/kimi-k2.5-preview",
    ],
    AI_PROVIDER_DOUBAO: [
        "doubao-1.5-pro-32k",
        "doubao-1.5-pro-256k",
        "doubao-1.5-lite-32k",
        "doubao-pro-32k",
    ],
}

AI_DEFAULT_BASE_URLS = {
    AI_PROVIDER_DEEPSEEK: "https://api.deepseek.com/v1",
    AI_PROVIDER_OPENAI: "https://api.openai.com/v1",
    AI_PROVIDER_QWEN: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    AI_PROVIDER_GLM: "https://open.bigmodel.cn/api/paas/v4",
    AI_PROVIDER_KIMI: "https://api.moonshot.ai/v1",
    AI_PROVIDER_DOUBAO: "https://ark.cn-beijing.volces.com/api/v3",
}

# AI快捷键
AI_CHAT_HOTKEY = "ctrl+shift+a"

# 翻译目标语言
TRANSLATE_LANGUAGES = {
    "zh": "简体中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
}

# 默认目标语言
DEFAULT_TRANSLATE_LANG = "zh"
