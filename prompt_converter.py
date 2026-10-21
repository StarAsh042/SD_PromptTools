import re
from config import Config
from decimal import Decimal, ROUND_HALF_UP

def round_half_up(n: float, decimals: int = 3) -> float:
    """
    对浮点数 n 按四舍五入（half-up）方式保留指定小数位数。
    """
    multiplier = 10 ** decimals
    # 构造格式串 "1.000"（例如3位小数）
    quant = Decimal(f'1.{"0"*decimals}')
    return float(Decimal(n).quantize(quant, rounding=ROUND_HALF_UP))

def escape_inner_parentheses(text: str) -> str:
    """
    转义文本中的内部括号：
    - 对未被转义的 "("，如果前面没有下划线，则在其前插入下划线后再添加反斜杠；
    - 如果 "(" 前已有下划线，则仅在前面加反斜杠；
    - 对未被转义的 ")" 添加反斜杠。
    例如："mamimi(mamamimi)" 会转换为 "mamimi_\(mamamimi\)"
    """
    result = []
    i = 0
    while i < len(text):
        if text[i] == '(':
            if i > 0 and text[i-1] not in ['\\', '_']:
                result.append('_\\(')
            elif i > 0 and text[i-1] == '_':
                result.append('\\(')
            else:
                result.append('\\(')
            i += 1
        elif text[i] == ')':
            # 如果未被转义，则添加反斜杠
            if i == 0 or text[i-1] != '\\':
                result.append('\\)')
            else:
                result.append(')')
            i += 1
        else:
            result.append(text[i])
            i += 1
    return ''.join(result)

def clean_output(text: str) -> str:
    """
    清理转换结果中的多余标点和空格：
    1. 将句号（。）和顿号（、）转换为逗号；
    2. 删除连续多余的逗号，合并为一个；
    3. 删除逗号前后多余的空格。
    """
    # 替换中文标点为英文逗号
    text = text.replace('。', ',').replace('、', ',')
    # 删除逗号前后多余的空格，并用单个逗号连接
    text = re.sub(r'\s*,\s*', ',', text)
    # 将连续逗号替换为单个逗号
    text = re.sub(r',+', ',', text)
    # 去除首尾多余的逗号
    return text.strip(',')

class PromptConverter:
    # 新增类属性，用于存储 CSV 表中加载的艺术家 tag（来自 danbooru_art.csv）
    artist_triggers = set()

class PromptConverter:
    # 新增类属性，用于存储 CSV 表中加载的艺术家 tag（来自 danbooru_art.csv）
    artist_triggers = set()

    @staticmethod
    def load_artist_triggers():
        """
        从同目录下的 CSV 文件 danbooru_art.csv 中加载艺术家 tag，
        文件要求有一列 "trigger"（不区分大小写）。
        
        如果 CSV 文件只有一行数据（没有表头）或只有 header 一行，
        则会尝试将这一行内容作为 trigger 进行加载。
        """
        import csv
        try:
            with open("danbooru_art.csv", "r", encoding="utf-8", newline="") as csvfile:
                # 读取前 1024 个字节用于判断是否有表头
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                has_header = sniffer.has_header(sample)
                if has_header:
                    reader = csv.DictReader(csvfile)
                    # 正常情况：根据 "trigger" 列获取所有数据行的内容
                    triggers = {
                        row["trigger"].strip() for row in reader
                        if row.get("trigger") and row["trigger"].strip()
                    }
                    # 如果没有读取到数据，但 fieldnames 存在，可能 CSV 文件仅有一行，
                    # 如果唯一的 fieldnames 不是 "trigger"，则认为该字段名就是 trigger 数据
                    if not triggers and reader.fieldnames:
                        if len(reader.fieldnames) == 1 and reader.fieldnames[0].lower() != "trigger":
                            triggers = {reader.fieldnames[0].strip()}
                else:
                    # CSV 没有表头，使用 csv.reader 直接读取第一列作为 trigger
                    reader = csv.reader(csvfile)
                    triggers = {row[0].strip() for row in reader if row and row[0].strip()}
                PromptConverter.artist_triggers = triggers
        except Exception as e:
            # 出现异常则置为空集合
            PromptConverter.artist_triggers = set()

    @staticmethod
    def round_to_step(number: float, step: float = Config.WEIGHT_STEP) -> float:
        """
        已废弃原先按步长舍入的方式，此处保留接口（如有其他需求可修改）
        """
        return round_half_up(number, 3)

    @staticmethod
    def parse_and_count_brackets(text: str, pos: int = 0, outer_curly: int = 0, outer_square: int = 0) -> tuple[list, int]:
        """
        递归解析括号并计算标签权重。
        修改权重计算公式：
          - 正权重（大括号）：权重因子 = Config.BRACKET_RULES 中 "{" 的数值
          - 负权重（方括号）：采用 1/正权重因子
        最后采用 round_half_up 保留 3 位小数。
        """
        # 从配置中获取正权重因子（例如1.05）；负权重使用其倒数
        positive_factor = Config.BRACKET_RULES.get('{', (1.05, '}'))[0]
        negative_factor = 1 / positive_factor

        result = []
        current_tag = ""
        curly_count = outer_curly
        square_count = outer_square

        while pos < len(text):
            char = text[pos]
            if char == '{':
                curly_count += 1
            elif char == '[':
                square_count += 1
            elif char == '}' and curly_count > outer_curly:
                if current_tag:
                    weight = (positive_factor ** (curly_count - outer_curly)) * (negative_factor ** (square_count - outer_square))
                    weight = round_half_up(weight, Config.WEIGHT_PRECISION)
                    result.append((current_tag.strip(), weight))
                    current_tag = ""
                curly_count -= 1
            elif char == ']' and square_count > outer_square:
                if current_tag:
                    weight = (positive_factor ** (curly_count - outer_curly)) * (negative_factor ** (square_count - outer_square))
                    weight = round_half_up(weight, Config.WEIGHT_PRECISION)
                    result.append((current_tag.strip(), weight))
                    current_tag = ""
                square_count -= 1
            elif char == ',':
                if current_tag:
                    if curly_count > outer_curly or square_count > outer_square:
                        weight = (positive_factor ** (curly_count - outer_curly)) * (negative_factor ** (square_count - outer_square))
                        weight = round_half_up(weight, Config.WEIGHT_PRECISION)
                        result.append((current_tag.strip(), weight))
                    else:
                        result.append((current_tag.strip(), 1.0))
                    current_tag = ""
            else:
                current_tag += char
            pos += 1

        if current_tag:
            if curly_count > outer_curly or square_count > outer_square:
                weight = (positive_factor ** (curly_count - outer_curly)) * (negative_factor ** (square_count - outer_square))
                weight = round_half_up(weight, Config.WEIGHT_PRECISION)
                result.append((current_tag.strip(), weight))
            else:
                result.append((current_tag.strip(), 1.0))
        return result, pos

