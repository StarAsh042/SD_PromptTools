//! SD 提示词工具集的 Rust 核心。
//!
//! 这里只放纯计算：括号解析、权重计算、转义与输出清理。
//! 文件读写、CSV 标签表、界面与错误信息仍留在 Python 侧。

use pyo3::prelude::*;

/// 返回扩展模块自身的版本号，用于确认加载的是哪一份构建产物。
#[pyfunction]
fn core_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// 按 half-up 规则保留指定小数位。
///
/// Python 侧用的是 `Decimal(float).quantize(ROUND_HALF_UP)`，它按 double 的
/// **精确十进制展开**舍入；直接写 `(x * 1000.0).round() / 1000.0` 会在
/// 1.1025 这类边界上差一位（乘法先把值挪成 1102.5000000000001）。
/// 所以这里先把 double 打印成足够长的精确小数串，在字符串上做进位，再解析回 f64。
fn round_half_up_value(n: f64, decimals: usize) -> f64 {
    if !n.is_finite() {
        return n;
    }
    let negative = n.is_sign_negative();
    let magnitude = n.abs();
    // f64 的精确十进制展开最长约 1080 位小数，多留余量避免截断影响进位。
    let text = format!("{:.*}", decimals + 1080, magnitude);
    let (int_part, frac_part) = match text.split_once('.') {
        Some(parts) => parts,
        None => return n,
    };
    let frac = frac_part.as_bytes();

    let mut digits: Vec<u8> = Vec::with_capacity(int_part.len() + decimals + 2);
    digits.extend_from_slice(int_part.as_bytes());
    if decimals > 0 {
        digits.push(b'.');
        digits.extend_from_slice(&frac[..decimals]);
    }

    let round_up = matches!(frac.get(decimals), Some(d) if *d >= b'5');
    if round_up {
        let mut i = digits.len();
        let mut carry = true;
        while carry && i > 0 {
            i -= 1;
            match digits[i] {
                b'.' => continue,
                b'9' => digits[i] = b'0',
                other => {
                    digits[i] = other + 1;
                    carry = false;
                }
            }
        }
        if carry {
            digits.insert(0, b'1');
        }
    }

    let value: f64 = std::str::from_utf8(&digits)
        .expect("digits are ascii")
        .parse()
        .expect("digits form a valid float");
    if negative {
        -value
    } else {
        value
    }
}

#[pyfunction]
#[pyo3(signature = (n, decimals = 3))]
fn round_half_up(n: f64, decimals: u32) -> f64 {
    round_half_up_value(n, decimals as usize)
}

/// 逐字符解析 `{}` / `[]` 嵌套，产出 `(tag, weight)` 序列。
///
/// 权重 = 正因子^花括号层数 × 负因子^方括号层数，负因子取正因子的倒数。
/// 闭合括号时先按「尚未减一」的层数结算当前 tag，再减层；层数为 0 的闭合括号
/// 不是语法，会被当作普通字符留在 tag 里（与 Python 实现一致）。
#[pyfunction]
#[pyo3(signature = (text, pos = 0, outer_curly = 0, outer_square = 0, positive_factor = 1.05, precision = 3))]
fn parse_brackets(
    text: &str,
    pos: usize,
    outer_curly: i32,
    outer_square: i32,
    positive_factor: f64,
    precision: u32,
) -> (Vec<(String, f64)>, usize) {
    let chars: Vec<char> = text.chars().collect();
    let negative_factor = 1.0 / positive_factor;
    let mut result: Vec<(String, f64)> = Vec::new();
    let mut current = String::new();
    let mut curly = outer_curly;
    let mut square = outer_square;
    let mut i = pos;  // 与 Python 一致：pos 超出长度时原样返回

    let weight_at = |curly: i32, square: i32| -> f64 {
        let positive = positive_factor.powf(f64::from(curly - outer_curly));
        let negative = negative_factor.powf(f64::from(square - outer_square));
        round_half_up_value(positive * negative, precision as usize)
    };

    while i < chars.len() {
        let c = chars[i];
        match c {
            '{' => curly += 1,
            '[' => square += 1,
            '}' if curly > outer_curly => {
                if !current.is_empty() {
                    result.push((py_trim(&current).to_string(), weight_at(curly, square)));
                    current.clear();
                }
                curly -= 1;
            }
            ']' if square > outer_square => {
                if !current.is_empty() {
                    result.push((py_trim(&current).to_string(), weight_at(curly, square)));
                    current.clear();
                }
                square -= 1;
            }
            ',' => {
                if !current.is_empty() {
                    if curly > outer_curly || square > outer_square {
                        result.push((py_trim(&current).to_string(), weight_at(curly, square)));
                    } else {
                        result.push((py_trim(&current).to_string(), 1.0));
                    }
                    current.clear();
                }
            }
            _ => current.push(c),
        }
        i += 1;
    }

    if !current.is_empty() {
        if curly > outer_curly || square > outer_square {
            result.push((py_trim(&current).to_string(), weight_at(curly, square)));
        } else {
            result.push((py_trim(&current).to_string(), 1.0));
        }
    }

    (result, i)
}

/// Python 的 `\s` 与 `str.strip()` 把 \x1c-\x1f 也算作空白，Rust 的
/// `char::is_whitespace()` 不含这几个控制字符；这里补齐，保证清理与裁剪结果一致。
fn is_py_space(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

fn py_trim(s: &str) -> &str {
    s.trim_matches(is_py_space)
}

/// 转义标签内部的括号，避免被 SD 当成权重语法。
///
/// 规则（与 Python 实现逐字符对齐）：
/// - 未转义的 `(`：前一个字符不是 `\` 或 `_` 时插入 `_`，再补 `\(`；
/// - 前一个字符是 `_` 或位于开头：只补 `\(`；
/// - 未转义的 `)`：补 `\)`。
#[pyfunction]
fn escape_inner_parentheses(text: &str) -> String {
    let chars: Vec<char> = text.chars().collect();
    let mut out = String::with_capacity(text.len() + 8);
    for (i, &c) in chars.iter().enumerate() {
        match c {
            '(' => {
                if i > 0 && chars[i - 1] != '\\' && chars[i - 1] != '_' {
                    out.push_str("_\\(");
                } else {
                    out.push_str("\\(");
                }
            }
            ')' => {
                if i == 0 || chars[i - 1] != '\\' {
                    out.push_str("\\)");
                } else {
                    out.push(')');
                }
            }
            _ => out.push(c),
        }
    }
    out
}

/// 清理输出：中文标点转英文逗号、逗号前后空白去掉、连续逗号合并、去掉首尾逗号。
#[pyfunction]
fn clean_output(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut skip_space = false;
    for ch in text.chars() {
        let c = match ch {
            '。' | '、' => ',',
            other => other,
        };
        if c == ',' {
            while matches!(out.chars().last(), Some(last) if is_py_space(last)) {
                out.pop();
            }
            if !out.is_empty() && !out.ends_with(',') {
                out.push(',');
            }
            skip_space = true;
        } else if is_py_space(c) {
            if !skip_space {
                out.push(c);
            }
        } else {
            skip_space = false;
            out.push(c);
        }
    }
    out.trim_matches(',').to_string()
}

#[pymodule]
fn sdprompt_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(core_version, m)?)?;
    m.add_function(wrap_pyfunction!(round_half_up, m)?)?;
    m.add_function(wrap_pyfunction!(parse_brackets, m)?)?;
    m.add_function(wrap_pyfunction!(escape_inner_parentheses, m)?)?;
    m.add_function(wrap_pyfunction!(clean_output, m)?)?;
    Ok(())
}
