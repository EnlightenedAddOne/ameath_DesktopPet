# Ameath 项目重构说明

## 项目结构

重构后的代码从单个 `main.py`（1353行）拆分成了以下模块：

```
.
├── constants.py        # 所有常量定义（配置值、Windows API 常量等）
├── config.py          # 配置管理（加载、保存、更新）
├── utils.py           # 通用工具函数（资源路径、版本获取等）
├── system.py          # Windows 系统功能（DPI、窗口置顶、鼠标穿透）
├── startup.py         # 开机自启管理
├── animations.py      # GIF 动画加载和处理
├── tray.py            # 系统托盘控制器
├── pet.py             # 桌面宠物主类（DesktopPet）
├── version_checker.py # 版本检查功能
└── main.py            # 程序入口（53行）
```

## 主要改进

### 1. 模块拆分
- **职责分离**：每个模块只负责一个功能领域
- **可维护性**：代码结构清晰，便于理解和修改
- **可测试性**：模块独立，便于单元测试

### 2. 性能优化
- **配置缓存**：使用 `_config_cache` 避免重复读取配置文件
- **鼠标位置缓存**：在 `move()` 中缓存鼠标位置，减少 `winfo_pointerx/y` 调用
- **距离计算优化**：使用平方距离比较避免开方运算
- **窗口更新优化**：仅在位置变化时调用 `geometry()`
- **抖动降频**：每 5 帧更新一次随机抖动

### 3. 异常处理改进
- **具体异常类型**：
  - `FileNotFoundError` 代替裸 `except`
  - `json.JSONDecodeError` 处理配置解析错误
  - `OSError` 和 `ctypes.WinError` 处理 Windows API 错误
  - `subprocess.SubprocessError` 处理命令执行错误
- **错误信息**：提供有意义的错误提示
- **优雅降级**：出错时使用默认值，不影响程序运行

### 4. 代码质量
- **类型注解**：函数参数和返回值都有类型提示
- **文档字符串**：所有公共方法都有文档说明
- **命名规范**：清晰的命名，遵循 PEP 8
- **单一职责**：每个函数只做一件事

## 文件说明

### constants.py (2366 字节)
所有项目常量集中定义：
- 路径配置
- 缩放和透明度选项
- 运动参数
- Windows API 常量
- 状态机常量

### config.py (2249 字节)
配置管理模块：
- `load_config()`：带缓存的配置加载
- `save_config()`：配置保存
- `update_config()`：配置更新
- `get_config_value()`：获取单个配置值

### utils.py (2346 字节)
工具函数：
- `resource_path()`：PyInstaller 资源路径处理
- `get_version()`：获取当前版本（支持 version.txt 和 git）
- `normalize_version()`：版本号标准化
- `version_greater_than()`：版本比较

### system.py (2174 字节)
Windows 系统功能：
- `enable_dpi_awareness()`：DPI 感知
- `set_window_topmost()`：窗口置顶
- `set_click_through()`：鼠标穿透
- `get_window_handle()`：获取窗口句柄

### startup.py (2622 字节)
开机自启管理：
- `get_startup_executable_path()`：获取注册表路径
- `set_auto_startup()`：设置开机自启
- `check_and_fix_startup()`：检查和修复启动路径

### animations.py (2940 字节)
动画处理：
- `load_gif_frames()`：加载 GIF 帧
- `flip_frames()`：水平翻转帧
- `load_all_animations()`：加载所有动画资源

### tray.py (5458 字节)
系统托盘控制器：
- 菜单构建
- 事件处理
- 图标管理

### pet.py (18924 字节)
桌面宠物主类 `DesktopPet`：
- 窗口初始化
- 动画管理
- 运动系统（状态机）
- 事件处理
- 性能优化版本

### version_checker.py (3577 字节)
版本检查：
- `check_new_version()`：检查最新版本
- `show_update_dialog()`：显示更新对话框
- `check_version_and_notify()`：后台检查并通知

### main.py (1066 字节)
程序入口：
- DPI 感知初始化
- 创建宠物实例
- 启动托盘
- 版本检查
- 主循环

## 性能提升

### 优化前
- 每次 `move()` 调用都读取配置文件
- 多次调用 `winfo_pointerx/y`
- 频繁进行距离开方计算
- 每次移动都调用 `geometry()`

### 优化后
- 配置使用内存缓存，减少 IO
- 鼠标位置每帧只获取一次
- 使用平方距离比较，减少开方运算
- 仅在位置变化时更新窗口
- 抖动计算每 5 帧更新一次

## 如何运行

```bash
python main.py
```

## 打包

```bash
pyinstaller ameath.spec
```

注意：需要更新 `ameath.spec` 以包含新的模块文件。
