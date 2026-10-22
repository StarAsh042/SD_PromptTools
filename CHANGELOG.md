# 更新日志

本文件记录 SD 提示词工具集的所有重要变更。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [2.1.0] - 2026-10-22

从 2.0.0 起的可用性修复：先让它能起来，再让它能被看懂。

### 新增

- **一键启动 `start.bat` / `start.py`**：检查 Python 版本、运行依赖、Rust 扩展，缺什么补什么；8080 被占用时自动顺延端口并打印实际地址。
- **界面语言选择器**收进左上角工具条，不再独占一行。

### 修复

- **装了系统代理就启动失败**：Gradio 打开浏览器前会 `httpx` 探活 `127.0.0.1`，请求被系统代理绕到外网后超时。
- **端口被占用直接崩溃**：改为从 8080 往后找空端口。
- **英文界面残留中文**：输入框 placeholder、浏览器标题、`<html lang>`、标签页名称、页脚「通过 API 使用 / 使用 Gradio 构建」、Gradio 内置的上传框文案。
- **元数据面板误报**：未选择图片时显示「文件不存在或无效」；错误文案改为稳定 code，随语言切换。
- **拖拽图片会让页面跳走**：现在阻止浏览器默认打开文件，并支持整个左列接收拖放。
- **上传拖放热区只有按钮大小**：CSS 与拖放转发双管齐下。
- **同一条日志打印多遍**：`setup_logging()` 改成幂等。
- **CI 构建失败**：`rust-toolchain.toml` 声明的 clippy 组件与 runner 预装版本冲突。
- **全新安装 `import gradio` 失败**：`huggingface_hub` 1.0 移除了 `HfFolder`，已锁定 `<1.0`。

### 变更

- 新增 `envsetup.py`：启动前把回环地址并入 `NO_PROXY`，并默认关闭 Gradio 遥测。
- 依赖：`huggingface_hub>=0.19.3,<1.0`。
- 版本号升至 2.1.0（Cargo / pyproject）。

### 已知限制

- 框架内置文案的本地化依赖 DOM 文本替换，Gradio 大版本升级后可能需要更新映射表。
- 真实浏览器里的布局与拖放效果仍靠人工验收。
- 未接入依赖漏洞扫描（pip-audit / gitleaks）。

## [2.0.0] - 2026-10-21

核心运算下沉到 Rust，并补上中英双语界面。转换结果与 1.0.0 逐字节一致（两个既有缺陷修复除外）。

### 新增

- **Rust 核心 `sdprompt_core`**：括号解析、权重计算、half-up 取整、括号转义与输出清理由 `src/lib.rs` 实现，经 PyO3 / maturin 编译成扩展模块。
- **等价性门禁**：1200 条语料（嵌套、转义、中英标点、空白边界）与 6 档小数位的取整结果，与迁移前的 Python 实现逐字节比对。
- **国际化**：`locales/zh-CN.json` 与 `locales/en-US.json`，界面顶部下拉框实时切换；缺 key 回退中文并记录，不静默显示空白。
- **自动化测试**：107 个 pytest 用例，覆盖特征测试、等价性、标签表加载、i18n 门禁与界面装配。

### 变更

- CI 拆成 `lint` / `test` / `build` 三个 job，并由聚合 job `ci` 作为唯一必过检查；构建走 `maturin build --locked`。
- `gradio` 锁定为 `4.19.2`；`rust-toolchain.toml` 锁定 `1.99.0`。

### 修复

- `artist:` 前缀在 LF 行尾的检出下静默失效：标签表带 BOM 且只有一列，`csv.Sniffer` 判定不出分隔符后异常被吞成空集合。改为 `utf-8-sig` + 显式表头判断。
- 界面无法实例化：`gr.JSON` 从 gradio 4.x 起没有 `height` 参数。

### 破坏性变更

- 运行前必须编译 Rust 扩展（`pip install .` 或 `maturin develop --release`），不能再直接 `python main.py`。
- 依赖版本收窄到 `gradio==4.19.2`。

### 已知限制

- 只验证了行为等价，**没有做性能基准对比**，不声称比 1.0.0 更快。
- 界面 `<html lang>` 未随语言切换更新（Gradio 未暴露该能力），已记录为未覆盖项。
- 转换函数返回的错误信息仍是原始英文/异常文本，未做错误码 + 本地化文案。
- 未接入依赖漏洞扫描（pip-audit / gitleaks）。

## [1.0.0] - 2026-10-21

首个稳定版本：由仓库原始上传历史重排整理，代码内容与重排前完全一致。

### 新增

- NAI 与 SD 提示词的**双向格式转换**，支持 `{}` / `[]` 嵌套层级与 0.05 步长换算。
- 权重按 half-up 规则保留三位小数，避免浮点边界误差。
- 标签内部括号自动转义，`artist:` 前缀依据 danbooru 艺术家标签表自动补全。
- 图片元数据探测：PNG 的 tEXt/iTXt 文本块、JPEG/WEBP 的 Exif UserComment。
- Gradio 双标签页界面，附带复制与重置按钮。

### 已知限制

- 项目暂无自动化测试，验证方式为模块导入与针对性输入对照。
- `image_processor.py` 为图片处理链路预留，尚未接入界面。
- `danbooru_art.csv` 带 BOM，在 LF 行尾的检出下 `csv.Sniffer` 会误判表头，导致 `artist:` 前缀不生效（Windows 默认 CRLF 检出正常）。计划在 2.0.0 修复。
