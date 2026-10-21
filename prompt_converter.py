import re
from config import Config
from functools import wraps
from decimal import Decimal, ROUND_HALF_UP

def round_half_up(n: float, decimals: int = 3) -> float:
    """
    对浮点数 n 按四舍五入（half-up）方式保留指定小数位数。
    """
    multiplier = 10 ** decimals
    # 构造格式串 "1.000"（例如3位小数）
    quant = Decimal(f'1.{"0"*decimals}')
    return float(Decimal(n).quantize(quant, rounding=ROUND_HALF_UP))

def handle_escape(func):
    """
    装饰器：处理提示词中的转义字符
    对于 nai_to_sd，我们不再对整个返回结果做替换，而是在生成每个 tag 时自行处理转义。
    """
    @wraps(func)
    def wrapper(prompt: str) -> str:
        if func.__name__ == 'nai_to_sd':
            return func(prompt)
        processed = Config.ESCAPE_PATTERN.sub(r"__ESC_\1__", prompt)
        result = func(processed)
        return re.sub(r"__ESC_([{}()[\]]])__", r"\1", result)
    return wrapper

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

    @staticmethod
    @handle_escape
    def nai_to_sd(prompt: str) -> str:
        """
        将 NAI 格式转换为 SD 格式。
        修改内容：
          1. 临时将 "artist:" 替换为 "artist_"，避免解析时冲突；
          2. 遍历解析出的 tag 时，先调用 add_artist_prefix 判断是否需要添加前缀，
             再调用 escape_inner_parentheses 对 tag 内部括号进行处理，并使用 round_half_up 保留 3 位小数；
          3. 最后恢复 "artist:" 标记，并对最终结果进行清理（替换中文标点、删除多余逗号和空格）。
        """
        if not isinstance(prompt, str):
            return ""
        try:
            # 临时替换 "artist:" 避免在解析时冲突
            prompt = prompt.replace("artist:", "artist_")
            tags, _ = PromptConverter.parse_and_count_brackets(prompt)
            result_tags = []
            for tag, weight in tags:
                # 恢复 artist: 标记后再处理
                tag = tag.replace("artist_", "artist:")
                # 判断是否为艺术家 tag，不含前缀但存在于 CSV 表中则添加前缀
                tag = PromptConverter.add_artist_prefix(tag)
                if abs(weight - 1.0) < 0.001:
                    result_tags.append(tag)
                else:
                    # 对 tag 内部括号进行转义处理
                    escaped_tag = escape_inner_parentheses(tag)
                    result_tags.append(f"({escaped_tag}:{weight:.3f})")
            result = ", ".join(result_tags)
            result = clean_output(result)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    @staticmethod
    @handle_escape
    def sd_to_nai(prompt: str) -> str:
        """
        将 SD 格式转换为 NAI 格式
        （此处保留原实现逻辑，但增加了对标签内括号前插入下划线的处理，
         同时对最终结果进行清理：将中文标点替换为逗号、删除多余的逗号和空格）
        """
        if not isinstance(prompt, str):
            return "Error: Input must be a string"
        try:
            prompt = prompt.strip()
            prompt = re.sub(r',\s*,', ',', prompt)
            prompt = prompt.strip(',')
            pattern = r'\((.*?):([\d.]+)\)'
            tags = []
            last_end = 0
            for match in re.finditer(pattern, prompt):
                if match.start() > last_end:
                    plain_text = prompt[last_end:match.start()].strip(' ,')
                    if plain_text:
                        tags.append((plain_text, 1.0))
                tag = match.group(1).strip()
                # 还原 SD 转换过程中对括号的转义
                tag = tag.replace('\\(', '(').replace('\\)', ')')
                # 如果 tag 中的左括号前没有下划线，则插入下划线
                tag = re.sub(r'(?<!_)[(]', '_(', tag)
                weight = float(match.group(2))
                tags.append((tag, weight))
                last_end = match.end()
            if last_end < len(prompt):
                plain_text = prompt[last_end:].strip(' ,')
                if plain_text:
                    tags.append((plain_text, 1.0))
            result_tags = []
            for tag, weight in tags:
                # 对 tag 进行 artist tag 前缀判断
                tag = PromptConverter.add_artist_prefix(tag)
                if abs(weight - 1.0) < 0.001:
                    result_tags.append(tag)
                else:
                    if weight > 1.0:
                        count = round((weight - 1.0) / Config.WEIGHT_STEP)
                        result_str = '{' * count + tag + '}' * count
                    else:
                        count = round((1.0 - weight) / Config.WEIGHT_STEP)
                        result_str = '[' * count + tag + ']' * count
                    result_tags.append(result_str)
            result = ", ".join(result_tags)
            result = clean_output(result)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    @staticmethod
    def add_artist_prefix(tag: str) -> str:
        """
        根据 CSV 表中加载的 artist trigger 判断 tag 是否需要添加 "artist:" 前缀。
        如果 tag（不包含前缀）正好出现在 PromptConverter.artist_triggers 集合中，
        则返回 "artist:" + tag，否则返回原 tag。
        """
        # 如果还没有加载，则加载 artist trigger 集合
        if not PromptConverter.artist_triggers:
            PromptConverter.load_artist_triggers()
        # 统一比较均转换成小写
        tag_lower = tag.lower()
        # 如果 tag 已经包含前缀，则直接返回
        if tag_lower.startswith("artist:"):
            return tag
        # 将 artist_triggers 集合转换为小写进行比较
        triggers_lower = {trigger.lower() for trigger in PromptConverter.artist_triggers}
        if tag_lower in triggers_lower:
            return "artist:" + tag
        return tag 