# -*- coding: utf-8 -*-
"""等价性门禁：Rust 核心必须与 1.0.0 的 Python 参考实现逐字节一致。

这里的参考实现来自迁移前的真实代码（tests/reference_impl.py），
不是照抄 Rust 逻辑，所以两边同时写错的可能性很低。
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import sdprompt_core as core
from tests import reference_impl as ref

TOKENS = [
    "{", "}", "[", "]", "(", ")", ",", " ", "  ", "\t",
    "a", "tag", "masterpiece", "best quality", "test_tag", "mamimi",
    "。", "、", "，", ":", "artist:", "1.05", "\u00a0", "\\(", "\\)", "_{",
]


def build_corpus(size=1200, seed=20261021):
    rng = random.Random(seed)
    cases = [
        "",
        " ",
        ",",
        "{",
        "}",
        "{{a}}",
        "[[a]]",
        "{a,[b,{c}]}",
        "artist:foo, {{zzz}}",
        "masterpiece。。",
        r"\(escaped\)",
        r"{{foo\(bar\)}}",
        "a, , b",
        "a , , , b",
        ",a,",
    ]
    for depth in range(1, 13):
        cases.append("{" * depth + "deep" + "}" * depth)
        cases.append("[" * depth + "deep" + "]" * depth)
        cases.append("{" * depth + "x" + "]" * depth)
    while len(cases) < size:
        length = rng.randint(1, 20)
        cases.append("".join(rng.choice(TOKENS) for _ in range(length)))
    return cases


CORPUS = build_corpus()


def first_diffs(pairs, limit=5):
    return [p for p in pairs][:limit]


def test_corpus_is_large_enough():
    assert len(CORPUS) >= 1000
    assert len(set(CORPUS)) >= 1000


def test_module_version_matches_project():
    assert core.core_version() == "2.1.0"


def test_parse_matches_reference():
    diffs = []
    for text in CORPUS:
        expected = ref.parse_and_count_brackets(text)
        actual = core.parse_brackets(
            text, 0, 0, 0, ref.BRACKET_RULES["{"][0], ref.WEIGHT_PRECISION
        )
        if expected != actual:
            diffs.append((text, expected, actual))

    assert not diffs, "解析结果不一致（最多列 5 条）：%r" % (first_diffs(diffs),)


def test_escape_matches_reference():
    diffs = []
    for text in CORPUS:
        expected = ref.escape_inner_parentheses(text)
        actual = core.escape_inner_parentheses(text)
        if expected != actual:
            diffs.append((text, expected, actual))

    assert not diffs, "转义结果不一致：%r" % (first_diffs(diffs),)


def test_clean_matches_reference():
    diffs = []
    for text in CORPUS:
        expected = ref.clean_output(text)
        actual = core.clean_output(text)
        if expected != actual:
            diffs.append((text, expected, actual))

    assert not diffs, "清理结果不一致：%r" % (first_diffs(diffs),)


@pytest.mark.parametrize("decimals", [0, 1, 2, 3, 4, 6])
def test_round_matches_reference(decimals):
    rng = random.Random(20261021 + decimals)
    values = [0.0, -0.0, 1.0, 1.1025, 2.0005, 0.9995, 0.0005, 9.9999, -1.1025, -0.0005]
    values += [rng.uniform(-10, 10) for _ in range(400)]
    values += [rng.uniform(0, 2) for _ in range(400)]

    diffs = [
        (v, ref.round_half_up(v, decimals), core.round_half_up(v, decimals))
        for v in values
        if ref.round_half_up(v, decimals) != core.round_half_up(v, decimals)
    ]

    assert not diffs, "取整结果不一致：%r" % (first_diffs(diffs),)
