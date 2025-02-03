import re

class Config:
    # 权重规则
    BRACKET_RULES = {
        '(': (1.05, ')'),
        '{': (1.05, '}'),
        '[': (0.95, ']')
    }
    WEIGHT_PRECISION = 3
    WEIGHT_STEP = 0.05
    ESCAPE_PATTERN = re.compile(r"\\([{}()[\]]])")
    
    # 特殊标签配置
    SPECIAL_TAGS = ['artist:', 'camera:', 'quality:', 'style:', 'subject:']
    
    # 表情符号模式
    EMOJI_PATTERNS = [
        r':3\b',
        r':8[DPOo\-]',
        r':-[DPOo\)\(]',
        r':[;][-]?[DPOo\)\(]',
        r':[DPOo]',
        r':[)(<>\]\[\{\}]',
        r':[\'\"]',
        r':ㅅ',
        r':ㅇ',
        r':ㅎ'
    ]
    
    # 图片解析相关
    PNG_HEADER_LENGTH = 8
    CHUNK_LENGTH_SIZE = 4
    SUPPORTED_FORMATS = {'PNG', 'JPEG', 'JPG', 'WEBP'}
    
    # 界面相关
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    DEFAULT_PORT = 8080
    MAX_THREADS = 4 