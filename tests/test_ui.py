# -*- coding: utf-8 -*-
"""界面装配与语言切换测试：只验证组件树与回调返回值，不启动服务。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr
import pytest

import i18n
from gradio_interface import GradioInterface


@pytest.fixture(autouse=True)
def _reset_locale():
    yield
    i18n.set_locale(i18n.DEFAULT_LOCALE)


def test_interface_can_be_built():
    ui = GradioInterface()

    assert isinstance(ui.demo, gr.Blocks)


def test_interface_has_two_tabs():
    ui = GradioInterface()

    labels = [b.label for b in ui.demo.blocks.values() if isinstance(b, gr.Tab)]

    assert labels == ["提示词格式转换器", "元数据探测器"]


def test_language_dropdown_offers_both_locales():
    ui = GradioInterface()

    dropdowns = [b for b in ui.demo.blocks.values() if isinstance(b, gr.Dropdown)]

    assert len(dropdowns) == 1
    assert [choice[1] for choice in dropdowns[0].choices] == list(i18n.available_locales())


def test_switch_language_returns_one_update_per_text():
    ui = GradioInterface()

    updates = ui.switch_language("en-US")

    assert len(updates) == len(ui._i18n_targets)
    labels = [u["label"] for u in updates if "label" in u]
    values = [u["value"] for u in updates if "value" in u]
    assert "Prompt Format Converter" in labels
    assert "Metadata Inspector" in labels
    assert "Convert to SD →" in values
    assert "Built by" in "".join(str(v) for v in values if v)


def test_switching_back_restores_chinese():
    ui = GradioInterface()
    ui.switch_language("en-US")

    updates = ui.switch_language("zh-CN")

    labels = [u["label"] for u in updates if "label" in u]
    assert "提示词格式转换器" in labels
    assert i18n.get_locale() == "zh-CN"
