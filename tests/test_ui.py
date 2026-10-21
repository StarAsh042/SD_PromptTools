# -*- coding: utf-8 -*-
"""界面装配测试：只验证能构建出组件树，不启动服务。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from gradio_interface import GradioInterface


def test_interface_can_be_built():
    ui = GradioInterface()

    assert isinstance(ui.demo, gr.Blocks)


def test_interface_has_two_tabs():
    ui = GradioInterface()

    labels = [b.label for b in ui.demo.blocks.values() if isinstance(b, gr.Tab)]

    assert labels == ["提示词格式转换器", "元数据探测器"]
