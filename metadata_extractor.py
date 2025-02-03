import struct
import re
import os
from PIL import Image
from logging_config import setup_logging

logger = setup_logging()

class MetadataExtractor:
    @staticmethod
    def _parse_png_metadata(file_path: str) -> dict:
        """
        解析PNG图片中的元数据
        """
        metadata = {}
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            offset = 8  # PNG header长度
            while offset < len(data) - 4:
                length = struct.unpack('>I', data[offset:offset+4])[0]
                chunk_type = data[offset+4:offset+8].decode('ascii', 'ignore')
                chunk_end = offset + 8 + length + 4
                if chunk_type in ['tEXt', 'iTXt']:
                    content = data[offset+8:chunk_end-4]
                    parts = content.split(b'\x00', 1)
                    if len(parts) == 2:
                        key = parts[0].decode('latin1', 'ignore').lower()
                        value = parts[1].decode('utf-8', 'ignore').strip('\x00')
                        if key in ['prompt', 'description', 'parameters']:
                            metadata[key.capitalize()] = value
                offset = chunk_end
        except Exception as e:
            logger.exception("PNG元数据解析错误")
        return metadata

    @staticmethod
    def _parse_jpeg_metadata(img: Image.Image) -> dict:
        """
        解析JPEG图片中的元数据
        """
        metadata = {}
        try:
            exif_data = img.getexif()
            if exif_data and 37510 in exif_data:
                user_comment = exif_data[37510].decode('utf-8', 'ignore')
                prompt_match = re.search(r"prompt:\s*(.*?)(?=\s|$)", user_comment, re.IGNORECASE | re.DOTALL)
                desc_match = re.search(r"description:\s*(.*?)(?=\s|$)", user_comment, re.IGNORECASE | re.DOTALL)
                if prompt_match:
                    metadata['Prompt'] = prompt_match.group(1).strip()
                if desc_match:
                    metadata['Description'] = desc_match.group(1).strip()
        except Exception as e:
            logger.error(f"JPEG解析异常: {e}")
        return metadata

    @staticmethod
    def extract_metadata(file_path: str) -> dict:
        """
        提取图片元数据，支持PNG和JPEG格式
        """
        if not file_path or not os.path.exists(file_path):
            return {"error": "文件不存在或无效"}
        try:
            with Image.open(file_path) as img:
                metadata = {}
                if img.format == 'PNG':
                    metadata.update(MetadataExtractor._parse_png_metadata(file_path))
                elif img.format in ['JPEG', 'WEBP']:
                    metadata.update(MetadataExtractor._parse_jpeg_metadata(img))
                result = {}
                if "Parameters" in metadata:
                    result["Parameters"] = metadata["Parameters"].strip().replace('\x00', '')
                elif "Prompt" in metadata:
                    result["Prompt"] = metadata["Prompt"]
                elif "Description" in metadata:
                    result["Description"] = metadata["Description"]
                if not result:
                    return {"message": "未找到提示词相关元数据"}
                return result
        except Exception as e:
            logger.exception("元数据解析错误")
            return {"error": f"处理失败: {str(e)}"} 