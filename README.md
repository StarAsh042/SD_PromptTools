# SD提示词工具集

一款用于提示词格式转换与图片元数据提取的工具，支持 NovelAI 与 Stable Diffusion 两种格式之间的互转，同时可从生成的图片中提取提示词和参数信息。
![01](https://github.com/user-attachments/assets/f944f237-f875-4fc3-9f5f-bfb0feeb8788)
![02](https://github.com/user-attachments/assets/698cb4b0-ab0c-4bfa-bf1e-db4aa480459c)

## 功能

- **提示词格式转换器**  
  - **双向转换**：  
    - NovelAI 格式 → Stable Diffusion 格式  
      将 NovelAI 的括号标记（如 `{tag}`、`[tag]`、`{{tag}}`、`[[tag]]`）转换为 SD 格式的权重表示（如 `(tag:1.05)`）。
    - Stable Diffusion 格式 → NovelAI 格式  
      将 SD 格式的权重表示转换为 NovelAI 的括号标记格式。
  - **标签处理**：  
    - 自动判断并添加 `artist:` 前缀（读取 CSV 表中指定的艺术家标签）。
    - 对标签中括号进行转义处理，确保转换结果的准确性。
    
- **图片元数据探测器**  
  - 支持从 PNG 和 JPEG（以及 WEBP）格式的图片中提取生成参数信息，如提示词、负提示词、种子、步数、采样器、CFG比例等。
  - 通过 Gradio 前端界面上传图片后，可自动解析并显示图片嵌入的元数据。

- **友好的前端界面**  
  - 使用 Gradio 构建，提供"提示词格式转换器"与"元数据探测器"两个标签页。
  - 提供复制、重置等便捷按钮，方便用户日常使用。
  - 界面支持中文 / English 实时切换，文案放在 `locales/` 下，缺翻译会回退中文并在日志里留痕。

## 项目结构

- **main.py**  
  程序入口，负责初始化并启动 Gradio 界面。

- **gradio_interface.py**  
  构建 Gradio 前端界面，分为提示词转换与图片元数据探测两个标签页。

- **prompt_converter.py**  
  实现了 NovelAI 与 Stable Diffusion 提示词格式之间的双向转换逻辑。

- **metadata_extractor.py**  
  利用 PIL 库解析图片文件中的元数据，支持 PNG 和 JPEG 格式。

- **config.py**  
  配置文件，定义了权重规则、特殊标签、界面参数等设置。

- **logging_config.py**  
  日志配置模块，采用 RotatingFileHandler 管理日志文件，防止日志文件过大。

- **image_processor.py**  
  图片处理相关功能，包括图片验证和临时图片保存。

- **src/lib.rs**（Rust 核心）  
  括号解析、权重计算、half-up 取整、括号转义与输出清理；编译成 `sdprompt_core` 扩展模块供 Python 调用。

- **i18n.py + locales/**  
  极简国际化：`zh-CN.json` / `en-US.json` 两个 catalog，缺 key 回退默认语言并记录。

## 安装

1. **克隆仓库**

   ```bash
   git clone https://github.com/StarAsh042/SD_PromptTools.git
   cd your-repository
   ```

2. **准备 Rust 工具链**（核心运算由 Rust 提供，必须先能编译）

   ```bash
   rustup toolchain install 1.99.0   # 版本写在 rust-toolchain.toml
   ```

   Windows 还需要 MSVC 生成工具；Linux / macOS 需要 C 编译器。

3. **安装依赖并编译扩展**

   ```bash
   pip install -r requirements.txt
   pip install .
   ```

   开发时也可以用 `pip install maturin && maturin develop --release`，
   改完 Rust 代码后重新执行一次即可生效。

## 使用

请按照以下步骤操作，确保你能顺利启动程序：

1. **安装 Python 与依赖**  
   请确保你已经安装了 Python 3.7 以上版本，并已按照 [安装](#安装) 部分中的步骤安装所有依赖库。

2. **打开命令提示符/终端**  
   进入项目所在的文件夹。例如，如果项目在桌面上的 `SDPromptTool` 文件夹中，请执行：
   ```bash
   cd ~/Desktop/SDPromptTool
   ```

3. **运行程序**  
   在命令行中输入以下命令启动程序：
   ```bash
   python main.py
   ```
   程序会启动一个 Gradio 界面服务，并自动在浏览器中打开显示界面。

4. **切换界面语言**  
   页面顶部的"界面语言"下拉框可选 `zh-CN` / `en-US`，切换只改文案，不会清空已输入的提示词。

5. **手动访问（如未自动打开）**  
   如果浏览器未自动打开，请手动在浏览器地址栏中输入：[http://127.0.0.1:8080](http://127.0.0.1:8080) 进行访问。

6. **跑测试**

   ```bash
   pip install -r requirements-dev.txt
   python -m pytest -q
   ```



## 参与开发

> **给外部贡献者的重要说明**
>
> `main` 分支受保护，且仅维护者可直接推送。
> **请向 `dev` 分支提交 Pull Request；直接向 `main` 提交的 PR 大概率不会受理。**

推荐流程：

1. Fork 本仓库到你自己账号
2. 从 `dev` 分支切出特性分支（`git checkout -b feature/xxx`）
3. 提交改动并推送到你的 Fork
4. 向本仓库的 **`dev` 分支**开 Pull Request，等待 CI 通过与合并

分支流向：`feature/xxx` → `dev`（日常集成）→ `main`（发布版本）

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：
`feat(converter): ...`、`fix(ui): ...`、`docs: ...`。

所有 PR 必须通过 `ci` 检查（ruff、字节码编译、Rust 扩展构建、pytest）。

改 Rust 核心时请保留 `tests/reference_impl.py` 的等价性测试：

```bash
maturin develop --release
python -m pytest tests/test_core_equivalence.py -q
```

加界面文案时，`locales/zh-CN.json` 与 `locales/en-US.json` 必须同时加同一个 key，
`tests/test_i18n.py` 会检查 key 与占位符是否对齐。

## 许可
[MIT License](LICENSE)

