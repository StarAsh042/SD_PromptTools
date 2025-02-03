import logging
from logging.handlers import RotatingFileHandler

def setup_logging() -> logging.Logger:
    """
    配置日志记录，使用 RotatingFileHandler 防止日志文件过大。
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # 文件处理器，单个日志文件最大 1MB，最多保留 5 个备份
    fh = RotatingFileHandler('app.log', maxBytes=1*1024*1024, backupCount=5, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger 