import re
from config import Config
from functools import wraps

import sdprompt_core as _core


def round_half_up(n: float, decimals: int = 3) -> float:
    """
    对浮点数 n 按四舍五入（half-up）方式保留指定小数位数。
    实现在 Rust 核心 sdprompt_core.round_half_up：按 double 的精确十进制展开舍入。
    """
    return _core.round_half_up(n, decimals)

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
    转义文本中的内部括号，避免被 SD 当成权重语法。
    实现在 Rust 核心 sdprompt_core.escape_inner_parentheses。
    """
    return _core.escape_inner_parentheses(text)

def clean_output(text: str) -> str:
    """
    清理转换结果：中文标点转逗号、去掉逗号周边空白、合并连续逗号、去掉首尾逗号。
    实现在 Rust 核心 sdprompt_core.clean_output。
    """
    return _core.clean_output(text)


class PromptConverter:
    # 新增类属性，用于存储 CSV 表中加载的艺术家 tag（来自 danbooru_art.csv）
    artist_triggers = set()

    @staticmethod
    def load_artist_triggers():
        """
        从同目录下的 CSV 文件 danbooru_art.csv 中加载艺术家 tag，
        文件要求有一列 "trigger"（不区分大小写）。

        读取规则改为显式判断表头，不再依赖 csv.Sniffer：
          - 用 utf-8-sig 打开，吃掉 Windows 导出时留下的 BOM；
          - 第一行若含 trigger 列，则按该列取值，否则第一行也算数据；
          - 单列文件没有分隔符，Sniffer 会直接抛 "Could not determine delimiter"，
            而该异常会被外层捕获成空集合，表现为 artist: 前缀静默失效。
        """
        import csv
        triggers = set()
        try:
            with open("danbooru_art.csv", "r", encoding="utf-8-sig", newline="") as csvfile:
                reader = csv.reader(csvfile)
                first = next(reader, None)
                if first is not None:
                    header = [cell.strip().lower() for cell in first]
                    if "trigger" in header:
                        index = header.index("trigger")
                    else:
                        index = 0
                        if first[0].strip():
                            triggers.add(first[0].strip())
                    for row in reader:
                        if len(row) > index and row[index].strip():
                            triggers.add(row[index].strip())
        except Exception:
            # 读取失败时退化为空集合，保证转换主流程不中断
            triggers = set()
        PromptConverter.artist_triggers = triggers

    @staticmethod
    def round_to_step(number: float, step: float = Config.WEIGHT_STEP) -> float:
        """
        已废弃原先按步长舍入的方式，此处保留接口（如有其他需求可修改）
        """
        return round_half_up(number, 3)

    @staticmethod
    def parse_and_count_brackets(text: str, pos: int = 0, outer_curly: int = 0, outer_square: int = 0) -> tuple[list, int]:
        """
        解析括号嵌套并计算标签权重，返回 ([(tag, weight), ...], 结束位置)。
        实现在 Rust 核心 sdprompt_core.parse_brackets：
          - 正权重（大括号）因子取 Config.BRACKET_RULES["{"]
          - 负权重（方括号）因子取其倒数
          - 权重按 Config.WEIGHT_PRECISION 位小数 half-up 取整
        """
        positive_factor = Config.BRACKET_RULES.get('{', (1.05, '}'))[0]
        return _core.parse_brackets(
            text, pos, outer_curly, outer_square,
            positive_factor, Config.WEIGHT_PRECISION,
        )

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