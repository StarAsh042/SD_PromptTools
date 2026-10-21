# -*- coding: utf-8 -*-
"""启动环境修正的门禁：回环地址必须绕过代理，且不能覆盖用户已有配置。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import envsetup


def test_merge_into_empty_sets_all_loopback_hosts():
    assert envsetup.merge_no_proxy("") == "127.0.0.1,localhost,::1"


def test_merge_keeps_existing_entries():
    assert envsetup.merge_no_proxy("example.com,10.0.0.0/8") == "example.com,10.0.0.0/8,127.0.0.1,localhost,::1"


def test_merge_does_not_duplicate_case_insensitively():
    assert envsetup.merge_no_proxy("127.0.0.1,LOCALHOST") == "127.0.0.1,LOCALHOST,::1"


def test_prepare_sets_no_proxy_and_disables_analytics():
    env = {}

    envsetup.prepare(env)

    assert env["NO_PROXY"] == "127.0.0.1,localhost,::1"
    assert env["no_proxy"] == "127.0.0.1,localhost,::1"
    assert env["GRADIO_ANALYTICS_ENABLED"] == "False"


def test_prepare_does_not_override_explicit_analytics_choice():
    env = {"GRADIO_ANALYTICS_ENABLED": "True"}

    envsetup.prepare(env)

    assert env["GRADIO_ANALYTICS_ENABLED"] == "True"


def test_prepare_is_idempotent():
    env = {}
    envsetup.prepare(env)
    first = env["NO_PROXY"]

    envsetup.prepare(env)

    assert env["NO_PROXY"] == first
