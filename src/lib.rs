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

#[pymodule]
fn sdprompt_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(core_version, m)?)?;
    m.add_function(wrap_pyfunction!(round_half_up, m)?)?;
    Ok(())
}
