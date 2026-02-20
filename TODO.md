# 待实现功能清单

## 1. 屏幕识别AI对话功能

### 功能概述
监听用户切换窗口，触发截屏并调用AI分析屏幕内容，桌宠通过气泡回复。

### 技术方案
- **模型**: 智谱 GLM-4V-Flash（免费）
- **触发方式**: Windows API `SetWinEventHook` 监听 `EVENT_SYSTEM_FOREGROUND`
- **截图**: `mss` 库
- **调用方式**: 智谱官方 SDK `zhipuai`

### 配置项（新增）
```python
# config.py 新增配置
"screen_ai_enabled": False,           # 是否启用
"screen_ai_trigger_prob": 0.3,        # 触发概率 0.0-1.0
"screen_ai_model": "glm-4v-flash",    # 识图模型
"screen_ai_api_key": "",               # API密钥（可复用ai_api_key）
"screen_ai_base_url": "https://open.bigmodel.cn/api/paas/v4"
```

### 实现步骤

#### 1.1 新建 `src/ai/screen_analyzer.py`
- `ScreenAnalyzer` 类
- `start_listening()` - 启动窗口监听
- `stop_listening()` - 停止监听
- `capture_screen()` - 截取屏幕
- `analyze_screen(image)` - 调用智谱API分析
- `trigger_speaking(response)` - 触发气泡回复

#### 1.2 更新 `src/config.py`
- 添加屏幕识别相关配置项

#### 1.3 更新 `src/ai/config_dialog.py`
添加识图AI配置区域：
- [ ] 启用屏幕识别复选框
- [ ] 触发概率滑块 (0-100%)
- [ ] API密钥输入（可选择复用现有AI配置）
- [ ] 测试连接按钮

#### 1.4 更新 `src/platform/tray.py`
AI助手子菜单添加：
- [ ] "屏幕识别" 开关（勾选状态关联配置）

#### 1.5 更新 `src/core/pet_core.py`
- 初始化 `ScreenAnalyzer`
- 接入气泡回复系统

### 依赖
```bash
pip install zhipuai mss
```

### 参考代码结构
```python
# src/ai/screen_analyzer.py
import ctypes
from ctypes import wintypes
import mss
import base64
from zhipuai import ZhipuAI

class ScreenAnalyzer:
    def __init__(self, app):
        self.app = app
        self.enabled = False
        self.trigger_prob = 0.3
        self.client = None
    
    def start_listening(self):
        # 使用 SetWinEventHook 监听窗口切换
        pass
    
    def _on_window_change(self, ...):
        if random.random() < self.trigger_prob:
            self._analyze_current_screen()
    
    def _analyze_current_screen(self):
        # 截图 -> base64 -> 调用智谱API -> 气泡回复
        pass
```

---

## 2. 音效添加



