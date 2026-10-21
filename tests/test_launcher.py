# -*- coding: utf-8 -*-
"""启动器门禁：环境检查必须与真实环境一致。

这些断言在 CI 与本地都成立，因为两个环境都已经装好依赖与 Rust 扩展。
"""
import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import start


def test_python_version_is_supported():
    assert start.python_ok()


def test_runtime_requirements_are_installed():
    assert start.missing_requirements() == []


def test_core_extension_is_importable():
    assert start.has_module(start.CORE_MODULE)


def test_check_mode_reports_ready():
    assert start.main(["--check"]) == 0


def test_find_free_port_skips_occupied():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        occupied = busy.getsockname()[1]

        assert start.find_free_port(occupied, attempts=5) != occupied


def test_wheel_lookup_returns_none_or_wheel():
    wheel = start.newest_wheel()

    assert wheel is None or wheel.suffix == ".whl"
