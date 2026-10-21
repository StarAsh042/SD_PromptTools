# -*- coding: utf-8 -*-
"""极简 i18n：一个 locale 一个 JSON catalog，缺 key 回退到默认语言并留下痕迹。

设计约束（来自 i18n 书写规范）：
  - key 用语义化点分小写，不用页面位置或整句；
  - 一条完整消息一个 key，不在代码里拼接句子；
  - 缺 key 不能静默变成空字符串：标记成 [missing:xxx] 并记录，测试里直接判红；
  - 占位符用 {name}，缺变量直接抛错，不显示 undefined。
"""
import json
import logging
import re
from pathlib import Path

LOCALES = ("zh-CN", "en-US")
DEFAULT_LOCALE = "zh-CN"
FALLBACK_LOCALE = "zh-CN"

_CATALOG_DIR = Path(__file__).with_name("locales")
_PLACEHOLDER = re.compile(r"\{(\w+)\}")

_catalogs: dict[str, dict[str, str]] = {}
_missing: list[tuple[str, str]] = []
_current_locale = DEFAULT_LOCALE
logger = logging.getLogger(__name__)


def load_catalogs() -> dict[str, dict[str, str]]:
    """读取并缓存所有 catalog；文件缺失时用空 catalog，让缺 key 立刻暴露。"""
    global _catalogs
    if _catalogs:
        return _catalogs
    catalogs: dict[str, dict[str, str]] = {}
    for locale in LOCALES:
        path = _CATALOG_DIR / f"{locale}.json"
        if not path.exists():
            logger.error("locale 文件缺失: %s", path)
            catalogs[locale] = {}
            continue
        with open(path, "r", encoding="utf-8") as f:
            catalogs[locale] = json.load(f)
    _catalogs = catalogs
    return _catalogs


def reload_catalogs() -> None:
    """测试用：丢掉缓存重新读盘。"""
    global _catalogs
    _catalogs = {}


def available_locales() -> tuple:
    return LOCALES


def set_locale(locale: str) -> str:
    global _current_locale
    if locale not in LOCALES:
        raise ValueError(f"unsupported locale: {locale}")
    _current_locale = locale
    return _current_locale


def get_locale() -> str:
    return _current_locale


def missing_keys() -> list:
    """本次进程里出现过的缺失 key，测试据此判红。"""
    return list(_missing)


def clear_missing() -> None:
    _missing.clear()


def t(key: str, **variables) -> str:
    """取当前语言的文案；缺 key 回退默认语言，再缺就返回可见标记。"""
    catalogs = load_catalogs()
    template = catalogs.get(_current_locale, {}).get(key)
    if template is None:
        template = catalogs.get(FALLBACK_LOCALE, {}).get(key)
        if template is not None and _current_locale != FALLBACK_LOCALE:
            logger.warning("缺少翻译，回退 %s: %s", FALLBACK_LOCALE, key)
            _missing.append((_current_locale, key))
    if template is None:
        logger.error("缺少 key: %s", key)
        _missing.append((_current_locale, key))
        return f"[missing:{key}]"

    def replace(match):
        name = match.group(1)
        if name not in variables:
            raise KeyError(f"缺少占位符变量 {name!r}（key={key}）")
        return str(variables[name])

    return _PLACEHOLDER.sub(replace, template)


def catalog_keys(locale: str) -> set:
    return set(load_catalogs().get(locale, {}))


def placeholders_of(text: str) -> set:
    return set(_PLACEHOLDER.findall(text))
