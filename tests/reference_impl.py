# -*- coding: utf-8 -*-
"""1.0.0 的纯计算参考实现（由工具从 645b5ba:prompt_converter.py 抽取，请勿手改）。

用途：Rust 迁移期间作为「行为基准」，逐字节对比两边结果。
迁移完成后仍保留，作为可独立验证的算法说明。
"""
import re
from decimal import Decimal, ROUND_HALF_UP

BRACKET_RULES = {'(': (1.05, ')'), '{': (1.05, '}'), '[': (0.95, ']')}
WEIGHT_PRECISION = 3


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


@staticmethod
def parse_and_count_brackets(text: str, pos: int = 0, outer_curly: int = 0, outer_square: int = 0) -> tuple[list, int]:
    """
    递归解析括号并计算标签权重。
    修改权重计算公式：
      - 正权重（大括号）：权重因子 = BRACKET_RULES 中 "{" 的数值
      - 负权重（方括号）：采用 1/正权重因子
    最后采用 round_half_up 保留 3 位小数。
    """
    # 从配置中获取正权重因子（例如1.05）；负权重使用其倒数
    positive_factor = BRACKET_RULES.get('{', (1.05, '}'))[0]
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
                weight = round_half_up(weight, WEIGHT_PRECISION)
                result.append((current_tag.strip(), weight))
                current_tag = ""
            curly_count -= 1
        elif char == ']' and square_count > outer_square:
            if current_tag:
                weight = (positive_factor ** (curly_count - outer_curly)) * (negative_factor ** (square_count - outer_square))
                weight = round_half_up(weight, WEIGHT_PRECISION)
                result.append((current_tag.strip(), weight))
                current_tag = ""
            square_count -= 1
        elif char == ',':
            if current_tag:
                if curly_count > outer_curly or square_count > outer_square:
                    weight = (positive_factor ** (curly_count - outer_curly)) * (negative_factor ** (square_count - outer_square))
                    weight = round_half_up(weight, WEIGHT_PRECISION)
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
            weight = round_half_up(weight, WEIGHT_PRECISION)
            result.append((current_tag.strip(), weight))
        else:
            result.append((current_tag.strip(), 1.0))
    return result, pos

