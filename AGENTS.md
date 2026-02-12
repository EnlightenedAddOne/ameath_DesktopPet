# AGENTS.md - Ameath Coding Guidelines

## Project Overview
Ameath is a Windows desktop pet application built with tkinter, Pillow, and pystray.
Python 3.12+ is required. The repo uses a `src/` module layout with a thin
bootstrap in `main.py`.

## Build, Run, Lint, Test

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run the App (Development)
```bash
python main.py
```

### Build Windows Executable
```bash
pyinstaller ameath.spec
```

### Lint with Ruff
```bash
ruff check .
ruff check --fix .
```

### Syntax Check (All Modules)
```bash
python -m py_compile main.py src/*.py
```

### Tests
- Manual test: run `python main.py` and exercise tray/menu actions.
- If a pytest suite is added later, use:
```bash
pytest
pytest path/to/test_file.py::test_name
```

## Code Style Guidelines

### Imports
Group imports in this order with a blank line between groups:
1. Standard library
2. Third-party
3. Local modules (absolute imports; no relative imports)

Example:
```python
# 1. Standard library
import json
from pathlib import Path
from typing import Any, Dict, Optional

# 2. Third-party
import tkinter as tk
from PIL import Image, ImageTk
import pystray

# 3. Local modules (relative imports not used)
from constants import CONFIG_FILE
from config import load_config
```

### Formatting
- 4 spaces indentation
- UTF-8 encoding; Chinese comments and docstrings are preferred
- Max line length around 100 characters
- Use double quotes for strings
- Avoid trailing whitespace

### Naming Conventions
- Constants: `UPPER_CASE` (e.g., `GIF_DIR`, `SPEED_X`)
- Classes: `PascalCase` (e.g., `DesktopPet`, `TrayController`)
- Functions/variables: `snake_case` (e.g., `load_config`, `move_frames`)
- Private: `_leading_underscore` (e.g., `_config_cache`, `_init_window`)

### Type Hints
Use type hints for public functions and key helpers.
```python
def load_config(force_refresh: bool = False) -> Dict[str, Any]:
    """加载配置"""
    ...

def resource_path(relative_path: str) -> str:
    """获取资源路径"""
    ...
```

### Docstrings
Use Chinese with Google style.
```python
def function_name(param: type) -> return_type:
    """简短描述

    Args:
        param: 参数说明

    Returns:
        返回值说明
    """
```

### Error Handling
Use specific exceptions; avoid bare `except:`.
```python
try:
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    data = default_value
except json.JSONDecodeError as e:
    print(f"解析失败: {e}")
    data = default_value
```

### Windows API Handling
Wrap Windows API calls and log failures with specific exceptions.
```python
try:
    ctypes.windll.user32.SetWindowPos(...)
except (OSError, ctypes.WinError) as e:
    print(f"操作失败: {e}")
    return False
```

### Resource Paths (PyInstaller compatible)
Always resolve assets with `resource_path`.
```python
from utils import resource_path

path = resource_path("assets/gifs/move.gif")
```

### Configuration Management
Use config helpers and cache appropriately.
```python
from config import load_config, update_config

config = load_config()
update_config(scale_index=3)
```

### Performance Notes
- Cache config in memory (`_config_cache`)
- Avoid excessive `winfo_pointer` calls; cache mouse positions
- Use squared distance for comparisons

## Cursor/Copilot Rules
No `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` found.
