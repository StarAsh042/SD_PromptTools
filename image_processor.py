from pathlib import Path
from PIL import Image
import tempfile
import os
from logging_config import setup_logging

logger = setup_logging()

class ImageProcessor:
    @staticmethod
    def validate_image(image: any) -> bool:
        """
        验证图片输入是否合法
        """
        if image is None:
            return False
        if isinstance(image, (str, Path)):
            return Path(image).exists()
        return True

    @staticmethod
    def create_temp_image(image_data: any) -> str:
        """
        创建临时图片文件，保存为 PNG 格式
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                if isinstance(image_data, (str, Path)):
                    return str(image_data)
                img = Image.fromarray(image_data)
                img.save(tmp.name)
                return tmp.name
        except Exception as e:
            logger.error(f"创建临时图片失败: {e}")
            return None 