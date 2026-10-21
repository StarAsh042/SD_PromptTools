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

#[pymodule]
fn sdprompt_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(core_version, m)?)?;
    Ok(())
}
