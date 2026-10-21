from decimal import Decimal, ROUND_HALF_UP

def round_half_up(n: float, decimals: int = 3) -> float:
    """
    对浮点数 n 按四舍五入（half-up）方式保留指定小数位数。
    """
    multiplier = 10 ** decimals
    # 构造格式串 "1.000"（例如3位小数）
    quant = Decimal(f'1.{"0"*decimals}')
    return float(Decimal(n).quantize(quant, rounding=ROUND_HALF_UP))

