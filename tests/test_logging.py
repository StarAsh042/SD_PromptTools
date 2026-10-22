# -*- coding: utf-8 -*-
"""日志配置门禁：多次调用只能挂一套 handler。

main / metadata_extractor / image_processor 都会调用 setup_logging()，
而 getLogger(__name__) 返回的是同一个 logger；不判空就会重复打印。
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging_config import setup_logging


def test_setup_logging_is_idempotent():
    first = setup_logging()
    handler_count = len(first.handlers)

    second = setup_logging()

    assert second is first
    assert len(second.handlers) == handler_count


def test_only_one_console_and_one_file_handler():
    logger = setup_logging()

    console = [h for h in logger.handlers if type(h) is logging.StreamHandler]
    files = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]

    assert len(console) == 1
    assert len(files) == 1


def test_repeated_calls_keep_handler_count():
    for _ in range(3):
        logger = setup_logging()

    assert len(logger.handlers) == 2
