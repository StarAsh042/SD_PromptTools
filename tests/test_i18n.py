# -*- coding: utf-8 -*-
"""i18n 门禁：key 对齐、占位符对齐、缺 key 行为可见。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import i18n


@pytest.fixture(autouse=True)
def _reset_state():
    i18n.reload_catalogs()
    i18n.clear_missing()
    i18n.set_locale(i18n.DEFAULT_LOCALE)
    yield
    i18n.reload_catalogs()
    i18n.clear_missing()
    i18n.set_locale(i18n.DEFAULT_LOCALE)


def test_every_locale_catalog_loads():
    catalogs = i18n.load_catalogs()

    assert set(catalogs) == set(i18n.available_locales())
    for locale, catalog in catalogs.items():
        assert catalog, f"{locale} 的 catalog 为空"


def test_key_parity():
    reference = i18n.catalog_keys(i18n.DEFAULT_LOCALE)

    for locale in i18n.available_locales():
        keys = i18n.catalog_keys(locale)
        assert keys == reference, (
            f"{locale} 与 {i18n.DEFAULT_LOCALE} 的 key 不一致："
            f"缺少 {sorted(reference - keys)}，多出 {sorted(keys - reference)}"
        )


def test_placeholder_parity():
    catalogs = i18n.load_catalogs()
    reference = catalogs[i18n.DEFAULT_LOCALE]

    for locale in i18n.available_locales():
        catalog = catalogs[locale]
        for key, text in catalog.items():
            assert i18n.placeholders_of(text) == i18n.placeholders_of(reference[key]), (
                f"{locale}:{key} 的占位符与默认语言不一致"
            )


def test_default_locale_matches_fallback_and_is_complete():
    assert i18n.FALLBACK_LOCALE == i18n.DEFAULT_LOCALE
    assert i18n.catalog_keys(i18n.DEFAULT_LOCALE)


def test_translation_returns_target_locale_text():
    i18n.set_locale("en-US")

    assert i18n.t("tabs.converter") == "Prompt Format Converter"
    assert i18n.missing_keys() == []


def test_interpolation():
    zh = i18n.t("app.footer", version="4.19.2")
    i18n.set_locale("en-US")
    en = i18n.t("app.footer", version="4.19.2")

    assert "4.19.2" in zh
    assert "4.19.2" in en
    assert "{" not in zh and "{" not in en


def test_missing_variable_is_an_error():
    with pytest.raises(KeyError):
        i18n.t("app.footer")


def test_missing_key_is_visible_and_recorded(monkeypatch):
    catalogs = i18n.load_catalogs()
    monkeypatch.delitem(catalogs["en-US"], "converter.heading")
    monkeypatch.delitem(catalogs["zh-CN"], "converter.heading")
    i18n.set_locale("en-US")

    text = i18n.t("converter.heading")

    assert text.startswith("[missing:converter.heading]")
    assert ("en-US", "converter.heading") in i18n.missing_keys()


def test_fallback_to_default_locale_is_recorded(monkeypatch):
    monkeypatch.setitem(i18n.load_catalogs()["zh-CN"], "only.in.zh", "只有中文")
    i18n.set_locale("en-US")

    text = i18n.t("only.in.zh")

    assert text == "只有中文"
    assert ("en-US", "only.in.zh") in i18n.missing_keys()


def test_unknown_locale_is_rejected():
    with pytest.raises(ValueError):
        i18n.set_locale("ja-JP")
