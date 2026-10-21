# -*- coding: utf-8 -*-
"""pytest 全局配置：隔离网络与导入路径。

Gradio 导入时会启动遥测线程去连外网；在无网络或超时的环境里，
这个后台线程会在测试结束时抛 ConnectTimeout，掩盖真正的测试结果。
"""
import os
import sys

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
