# -*- coding: utf-8 -*-
"""元数据解析的返回契约：只给 code，不拼用户可见文案。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, PngImagePlugin

from metadata_extractor import MetadataExtractor


def test_empty_input_returns_empty_dict():
    assert MetadataExtractor.extract_metadata(None) == {}
    assert MetadataExtractor.extract_metadata("") == {}


def test_missing_file_returns_error_code(tmp_path):
    result = MetadataExtractor.extract_metadata(str(tmp_path / "nope.png"))

    assert result == {"error_code": "metadata.file_missing"}


def test_png_with_parameters(tmp_path):
    path = tmp_path / "with_text.png"
    info = PngImagePlugin.PngInfo()
    info.add_text("parameters", "masterpiece" + chr(10) + "Steps: 20")
    Image.new("RGB", (8, 8), "white").save(path, pnginfo=info)

    assert MetadataExtractor.extract_metadata(str(path)) == {
        "Parameters": "masterpiece" + chr(10) + "Steps: 20"
    }


def test_png_without_metadata_returns_message_code(tmp_path):
    path = tmp_path / "plain.png"
    Image.new("RGB", (8, 8), "white").save(path)

    assert MetadataExtractor.extract_metadata(str(path)) == {"message_code": "metadata.not_found"}


def test_corrupt_file_returns_parse_failed(tmp_path):
    path = tmp_path / "broken.png"
    path.write_bytes(b"this is not an image")

    result = MetadataExtractor.extract_metadata(str(path))

    assert result["error_code"] == "metadata.parse_failed"
    assert result["detail"]
