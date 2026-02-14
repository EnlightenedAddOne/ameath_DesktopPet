"""配置管理模块"""

import json
from typing import Any, Dict, Optional
from src.constants import (
    AI_DEFAULT_MODELS,
    AI_PROVIDER_DEEPSEEK,
    CONFIG_FILE,
    DEFAULT_SCALE_INDEX,
    DEFAULT_TRANSPARENCY_INDEX,
    DEFAULT_TRANSLATE_LANG,
    TRANSLATE_LANGUAGES,
)

# 配置缓存
_config_cache: Optional[Dict[str, Any]] = None


def _default_config() -> Dict[str, Any]:
    """返回默认配置"""
    return {
        "scale_index": DEFAULT_SCALE_INDEX,
        "transparency_index": DEFAULT_TRANSPARENCY_INDEX,
        "auto_startup": False,
        "click_through": True,
        "follow_mouse": False,
        "behavior_mode": "active",
        # AI配置
        "ai_enabled": False,
        "ai_provider": AI_PROVIDER_DEEPSEEK,
        "ai_api_key": "",
        "ai_model": AI_DEFAULT_MODELS[AI_PROVIDER_DEEPSEEK],
        "ai_base_url": "",
        "ai_personality": "aemeath",
        # 翻译配置
        "translate_enabled": False,
        "translate_target_lang": DEFAULT_TRANSLATE_LANG,
    }


def load_config(force_refresh: bool = False) -> Dict[str, Any]:
    """加载配置，使用缓存减少IO

    Args:
        force_refresh: 是否强制刷新缓存

    Returns:
        配置字典
    """
    global _config_cache

    if not force_refresh and _config_cache is not None:
        return _config_cache.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"配置文件不存在，使用默认配置")
        data = _default_config()
    except json.JSONDecodeError as e:
        print(f"配置文件损坏 ({e})，使用默认配置")
        data = _default_config()

    _config_cache = data.copy()
    return data


def save_config(config: Dict[str, Any]) -> None:
    """保存配置到文件

    Args:
        config: 配置字典
    """
    global _config_cache

    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        _config_cache = config.copy()
    except (OSError, IOError) as e:
        print(f"保存配置失败: {e}")


def update_config(**kwargs) -> Dict[str, Any]:
    """更新配置并保存

    Args:
        **kwargs: 要更新的配置项

    Returns:
        更新后的配置字典
    """
    config = load_config()
    config.update(kwargs)
    save_config(config)
    return config.copy()


def get_config_value(key: str, default=None) -> Any:
    """获取单个配置值

    Args:
        key: 配置键名
        default: 默认值

    Returns:
        配置值
    """
    config = load_config()
    return config.get(key, default)
