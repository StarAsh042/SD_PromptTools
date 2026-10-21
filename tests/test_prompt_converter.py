# -*- coding: utf-8 -*-
"""特征测试：锁定 1.0.0 的转换行为。

这些断言是「现状快照」，包括现状里的怪异输出。它们的作用是：
任何后续改动（Rust 迁移、i18n）让输出发生一个字节的变化，这里就会红。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from prompt_converter import (
    PromptConverter,
    clean_output,
    escape_inner_parentheses,
    round_half_up,
)

NAI_TO_SD = [
    ('', ''),
    ('masterpiece', 'masterpiece'),
    ('masterpiece, best quality', 'masterpiece,best quality'),
    ('{{masterpiece}}', '(masterpiece:1.103)'),
    ('{{{{masterpiece}}}}', '(masterpiece:1.216)'),
    ('[[bad]]', '(bad:0.907)'),
    ('[[[[bad]]]]', '(bad:0.823)'),
    ('{{masterpiece}}, [[bad]]', '(masterpiece:1.103),(bad:0.907)'),
    ('{{{masterpiece}}}', '(masterpiece:1.158)'),
    ('{masterpiece, best quality}', '(masterpiece:1.050),(best quality:1.050)'),
    ('((masterpiece))', '((masterpiece))'),
    ('{{masterpiece, best quality}}, [[bad, ugly]]', '(masterpiece:1.103),(best quality:1.103),(bad:0.907),(ugly:0.907)'),
    ('artist:foo, {{zzz}}', 'artist:foo,(zzz:1.103)'),
    ('test_tag(test_tag)', 'test_tag(test_tag)'),
    ('{{test_tag(test_tag)}}', '(test_tag_\\(test_tag\\):1.103)'),
    ('a, b , c', 'a,b,c'),
    ('masterpiece。。', 'masterpiece'),
    ('{masterpiece}、[[bad]]', '(masterpiece:1.050),(,bad:0.907)'),
    ('{{masterpiece}} , {{bad}}', '(masterpiece:1.103),(bad:1.103)'),
    ('\\(escaped\\)', '\\(escaped\\)'),
    ('{{foo\\(bar\\)}}', '(foo\\\\(bar\\):1.103)'),
    ('test_tag:1.0', 'test_tag:1.0'),
    ('[{{nested}}]', '(nested:1.050)'),
    ('tag with space, {{another tag}}', 'tag with space,(another tag:1.103)'),
    ('{{masterpiece}}{{bad}}', '(masterpiece:1.103),(bad:1.103)'),
    ('[[a]][[b]]', '(a:0.907),(b:0.907)'),
    ('{{{{{{{{{{deep}}}}}}}}}}', '(deep:1.629)'),
    ('{a,[b,{c}]}', '(a:1.050),b,(c:1.050)'),
    ('a,,b', 'a,b'),
    ('  spaced  ', 'spaced'),
]

SD_TO_NAI = [
    ('', ''),
    ('masterpiece', 'masterpiece'),
    ('(masterpiece:1.05)', '{masterpiece}'),
    ('(masterpiece:1.15)', '{{{masterpiece}}}'),
    ('(masterpiece:0.90)', '[[masterpiece]]'),
    ('{{{masterpiece}}}', '{{{masterpiece}}}'),
    ('(masterpiece:1.05), (bad:0.95)', '{masterpiece},[bad]'),
    ('(test_tag(test_tag):1.10)', '{{test_tag_(test_tag)}}'),
    ('(a:1.0)', 'a'),
    ('(a:1.0005)', 'a'),
    ('(a:1.1005)', '{{a}}'),
    ('(a b:1.05)', '{a b}'),
    ('(masterpiece:1.05) , (bad:0.95)', '{masterpiece},[bad]'),
    ('(masterpiece:1.05),,', '{masterpiece}'),
    ('test_tag_\\(x\\), (test_tag:1.05)', 'test_tag_\\,{x),_(test_tag}'),
    ('((a):1.05)', '{_(a)}'),
    ('(a:1.2)', '{{{{a}}}}'),
    ('(a:0.8)', '[[[[a]]]]'),
    ('(a:1.05)(b:0.95)', '{a},[b]'),
    ('a, b, c', 'a,b,c'),
    ('(masterpiece:1.0500001)', '{masterpiece}'),
]

ROUND_CASES = [
    ((1.1025,), 1.103),
    ((0.9074, 3), 0.907),
    ((2.0005,), 2.001),
    ((-1.1025,), -1.103),
    ((0.0,), 0.0),
    ((1.0,), 1.0),
    ((1.10249,), 1.102),
    ((0.9995,), 1.0),
]

ESCAPE_CASES = [
    ('mamimi(mamamimi)', 'mamimi_\\(mamamimi\\)'),
    ('a(b)c', 'a_\\(b\\)c'),
    ('(a)', '\\(a\\)'),
    ('a_(b)', 'a_\\(b\\)'),
    ('a\\(b\\)', 'a\\\\(b\\)'),
    ('()', '\\(\\)'),
    (')(', '\\)_\\('),
    ('((x))', '\\(_\\(x\\)\\)'),
]

CLEAN_CASES = [
    ('a, , b。', 'a,b'),
    ('、、', ''),
    (' a , b ', ' a,b '),
    ('a,,b', 'a,b'),
    (',a,', 'a'),
    ('a , , , b', 'a,b'),
    ('', ''),
]


@pytest.mark.parametrize("src,expected", NAI_TO_SD)
def test_nai_to_sd(src, expected):
    assert PromptConverter.nai_to_sd(src) == expected


@pytest.mark.parametrize("src,expected", SD_TO_NAI)
def test_sd_to_nai(src, expected):
    assert PromptConverter.sd_to_nai(src) == expected


@pytest.mark.parametrize("args,expected", ROUND_CASES)
def test_round_half_up(args, expected):
    assert round_half_up(*args) == expected


@pytest.mark.parametrize("src,expected", ESCAPE_CASES)
def test_escape_inner_parentheses(src, expected):
    assert escape_inner_parentheses(src) == expected


@pytest.mark.parametrize("src,expected", CLEAN_CASES)
def test_clean_output(src, expected):
    assert clean_output(src) == expected


def test_non_string_input_returns_empty():
    assert PromptConverter.nai_to_sd(None) == ""
    assert PromptConverter.nai_to_sd(123) == ""


def test_parse_and_count_brackets_contract():
    tags, pos = PromptConverter.parse_and_count_brackets("{{a}}, [b]")
    assert tags == [("a", 1.103), ("b", 0.952)]
    assert pos == len("{{a}}, [b]")
