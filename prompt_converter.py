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

class PromptConverter:
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

