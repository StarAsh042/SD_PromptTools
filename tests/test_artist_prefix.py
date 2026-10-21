# -*- coding: utf-8 -*-
"""艺术家标签表的加载与前缀补全。

覆盖 1.0.0 的真实缺陷：表头带 BOM，用普通 utf-8 读取时字段名变成
"\\ufefftrigger"，在 LF 行尾的检出下会静默加载出空集合。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from prompt_converter import PromptConverter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def restore_triggers():
    old = PromptConverter.artist_triggers
    yield
    PromptConverter.artist_triggers = old


def _write_bom_csv(path, rows, crlf=False):
    eol = "\r\n" if crlf else "\n"
    text = "\ufefftrigger" + eol + eol.join(rows) + eol
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


@pytest.mark.parametrize("crlf", [False, True], ids=["lf", "crlf"])
def test_loads_bom_csv(tmp_path, monkeypatch, restore_triggers, crlf):
    _write_bom_csv(tmp_path / "danbooru_art.csv", ["foo", "bar", "baz"], crlf=crlf)
    monkeypatch.chdir(tmp_path)

    PromptConverter.load_artist_triggers()

    assert PromptConverter.artist_triggers == {"foo", "bar", "baz"}


def test_add_artist_prefix(tmp_path, monkeypatch, restore_triggers):
    _write_bom_csv(tmp_path / "danbooru_art.csv", ["banned artist", "mamimi"])
    monkeypatch.chdir(tmp_path)
    PromptConverter.load_artist_triggers()

    assert PromptConverter.add_artist_prefix("banned artist") == "artist:banned artist"
    assert PromptConverter.add_artist_prefix("Banned Artist") == "artist:Banned Artist"
    assert PromptConverter.add_artist_prefix("artist:x") == "artist:x"
    assert PromptConverter.add_artist_prefix("zzz") == "zzz"


def test_missing_csv_degrades_to_empty(tmp_path, monkeypatch, restore_triggers):
    monkeypatch.chdir(tmp_path)

    PromptConverter.load_artist_triggers()

    assert PromptConverter.artist_triggers == set()
    assert PromptConverter.add_artist_prefix("foo") == "foo"


def test_real_csv_is_fully_loaded(monkeypatch, restore_triggers):
    monkeypatch.chdir(REPO_ROOT)

    PromptConverter.load_artist_triggers()

    assert len(PromptConverter.artist_triggers) > 400000
    assert "banned artist" in {t.lower() for t in PromptConverter.artist_triggers}
