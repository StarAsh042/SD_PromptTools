# SD提示词工具集

一款用于提示词格式转换与图片元数据提取的工具，支持 NovelAI 与 Stable Diffusion 两种格式之间的互转，同时可从生成的图片中提取提示词和参数信息。

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

## 安装

1. **克隆仓库**

   ```bash
   git clone https://github.com/StarAsh042/SD_PromptTools.git
   cd your-repository
   ```

2. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

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

4. **手动访问（如未自动打开）**  
   如果浏览器未自动打开，请手动在浏览器地址栏中输入：[http://127.0.0.1:8080](http://127.0.0.1:8080) 进行访问。



## 致谢

该项目参考并学习了以下优秀开源项目的部分代码和思路，非常感谢开源社区的贡献：

- [ComfyUI_RS_NAI_Local_Prompt_converter](https://github.com/raspie10032/ComfyUI_RS_NAI_Local_Prompt_converter)  
  提供了提示词转换实现和思路。

- [stable-diffusion-inspector](https://github.com/Akegarasu/stable-diffusion-inspector)  
  展示了从 Stable Diffusion 生成的图片中提取 pnginfo 用于参数解析的实现方法。

## 许可证

本项目采用 [GNU Affero General Public License v3](https://www.gnu.org/licenses/agpl-3.0.html) 许可协议。详情请参阅 [LICENSE](./LICENSE) 文件。

