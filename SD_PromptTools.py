import gradio as gr
from PIL import Image
import struct
import logging
from typing import Dict, List, Optional
import re

# ----------------------
# 日志配置
# ----------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------
# 提示词转换核心逻辑
# ----------------------
def _calculate_weight_modifier(char: str, current_weight: float) -> float:
    """精确到三位小数的权重计算"""
    return {
        '(': 1.05,
        ')': 1 / 1.05,
        '{': 1.05,
        '}': 1 / 1.05,
        '[': 0.95,
        ']': 1 / 0.95
    }.get(char, 1.0)

def nai_to_sd(prompt: str) -> str:
    """NAI→SD"""
    try:
        tags = []
        current_tag = []
        weight_stack = [1.0]
        bracket_stack = []
        escape_next = False  # 新增转义标记

        for char in prompt:
            if escape_next:
                current_tag.append(char)
                escape_next = False
                continue

            if char == '\\':  # 处理转义字符
                escape_next = True
                continue

            if char in '{[(':
                if current_tag:
                    tags.append((''.join(current_tag).strip(), weight_stack[-1]))
                    current_tag = []
                weight_stack.append(round(weight_stack[-1] * _calculate_weight_modifier(char, weight_stack[-1]), 5))
                bracket_stack.append(char)
            elif char in '}])':
                if current_tag:
                    tags.append((''.join(current_tag).strip(), weight_stack[-1]))
                    current_tag = []
                if bracket_stack:
                    weight_stack.pop()
                    bracket_stack.pop()
            else:
                current_tag.append(char)

        if current_tag:
            tags.append((''.join(current_tag).strip(), weight_stack[-1]))

        formatted = []
        for tag, weight in tags:
            weight = round(weight, 3)  # 保留三位小数
            if abs(weight - 1.0) < 0.001:
                formatted.append(tag)
            else:
                # 处理转义括号
                formatted_tag = tag.replace('(', '\\(').replace(')', '\\)')
                formatted.append(f"({formatted_tag}:{weight:.3f})")

        return ' '.join(formatted)

def sd_to_nai(prompt: str) -> str:
    """SD→NAI"""
    try:
        tags = []
        current_tag = []
        weight_stack = [1.0]
        bracket_stack = []
        in_escape = False  # 转义状态标记

        for char in prompt:
            if in_escape:
                current_tag.append(char)
                in_escape = False
                continue

            if char == '\\':  # 处理转义字符
                in_escape = True
                continue

            if char == '(':
                if current_tag:
                    tags.append((''.join(current_tag).strip(), weight_stack[-1]))
                    current_tag = []
                weight_stack.append(round(weight_stack[-1] * 1.05, 5))
                bracket_stack.append(char)
            elif char == ')':
                if current_tag:
                    tags.append((''.join(current_tag).strip(), weight_stack[-1]))
                    current_tag = []
                if bracket_stack:
                    weight_stack.pop()
                    bracket_stack.pop()
            else:
                current_tag.append(char)

        if current_tag:
            tags.append((''.join(current_tag).strip(), weight_stack[-1]))

        result = []
        for tag, weight in tags:
            weight = round(weight, 3)
            # 恢复转义括号为普通括号
            clean_tag = tag.replace('\\', '')
            layers = round((weight - 1.0) / 0.05)
            if layers > 0:
                result.append('{' * layers + clean_tag + '}' * layers)
            elif layers < 0:
                result.append('[' * abs(layers) + clean_tag + ']' * abs(layers))
            else:
                result.append(clean_tag)

        return ' '.join(result)

# ----------------------
# 图片元数据解析
# ----------------------
def _parse_png_metadata(file_path: str) -> Dict:
    """解析PNG格式元数据"""
    metadata = {}
    try:
        with open(file_path, 'rb') as f:
            while True:
                try:
                    length_bytes = f.read(4)
                    if not length_bytes:
                        break
                    length = struct.unpack('>I', length_bytes)[0]
                    chunk_type = f.read(4).decode('ascii', 'ignore')
                    data = f.read(length)
                    f.read(4)  # CRC

                    if chunk_type in ['tEXt', 'iTXt']:
                        parts = data.split(b'\x00', 1)
                        if len(parts) < 2:
                            continue
                        key = parts[0].decode('latin1', 'ignore')
                        value = parts[1].decode('utf-8', 'ignore').strip('\x00')
                        metadata[key] = value
                except (struct.error, UnicodeDecodeError):
                    continue
    except Exception as e:
        logger.error(f"PNG解析失败: {str(e)}")
    return metadata

def _parse_jpeg_metadata(img: Image.Image) -> Dict:
    """解析JPEG/WEBP格式元数据"""
    metadata = {}
    try:
        exif_data = img.getexif()
        if exif_data and 37510 in exif_data:  # UserComment
            user_comment = exif_data[37510].decode('utf-8', 'ignore')
            if user_comment.startswith('UNICODE'):
                parts = user_comment[7:].split('Negative prompt:')
                if len(parts) > 0:
                    metadata['Prompt'] = parts[0].strip()
                if len(parts) > 1:
                    negative_parts = parts[1].split('Steps:')
                    metadata['Negative Prompt'] = negative_parts[0].strip()
                    if len(negative_parts) > 1:
                        metadata['Parameters'] = 'Steps:' + negative_parts[1]
    except Exception as e:
        logger.error(f"JPEG解析失败: {str(e)}")
    return metadata

def extract_metadata(file_path: str) -> Dict:
    """增强版元数据解析"""
    try:
        img = Image.open(file_path)
        metadata = {}

        if img.format == 'PNG':
            metadata.update(_parse_png_metadata(file_path))
        elif img.format in ['JPEG', 'WEBP']:
            metadata.update(_parse_jpeg_metadata(img))

        if not metadata:
            return {"status": "未检测到有效元数据"}
        
        # 结构化输出
        structured_meta = {
            "Prompt": metadata.get("Prompt", "未找到"),
            "Negative Prompt": metadata.get("Negative Prompt", "未找到"),
            "Parameters": metadata.get("Parameters", "未找到"),
            "其他元数据": {k: v for k, v in metadata.items() if k not in ['Prompt', 'Negative Prompt', 'Parameters']}
        }
        return structured_meta

    except Exception as e:
        logger.error(f"元数据解析失败: {str(e)}")
        return {"error": f"解析失败: {str(e)}"}

# ----------------------
# Gradio界面
# ----------------------
def gradio_interface():
    with gr.Blocks(title="SD提示词工具集", css=".gradio-container {max-width: 800px !important}") as demo:
        gr.Markdown("# 🛠️ Stable Diffusion 实用工具集")
        
        with gr.Tabs():
            # 提示词转换器
            with gr.TabItem("提示词转换"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("## SD ↔ NAI 双向转换")
                        with gr.Group():
                            sd_input = gr.Textbox(
                                lines=4,
                                placeholder="输入SD格式提示词，例如: (cat:1.2)...",
                                label="SD输入"
                            )
                            nai_output = gr.Textbox(
                                lines=4,
                                label="NAI输出",
                                interactive=False
                            )
                            gr.Button("→ SD → NAI 转换 →", variant="primary").click(
                                sd_to_nai,
                                inputs=sd_input,
                                outputs=nai_output
                            )
                        
                        gr.Markdown("---")
                        
                        with gr.Group():
                            nai_input = gr.Textbox(
                                lines=4,
                                placeholder="输入NAI格式提示词，例如: {{cat}}...",
                                label="NAI输入"
                            )
                            sd_output = gr.Textbox(
                                lines=4,
                                label="SD输出",
                                interactive=False
                            )
                            gr.Button("→ NAI → SD 转换 →", variant="primary").click(
                                nai_to_sd,
                                inputs=nai_input,
                                outputs=sd_output
                            )

            # 图片元数据解析
            with gr.TabItem("图片解析"):
                with gr.Row():
                    with gr.Column(scale=1):
                        img_input = gr.Image(
                            type="filepath",
                            label="上传图片（支持PNG/JPEG/WEBP）",
                            height=300
                        )
                        gr.Examples(
                            examples=[["example.png"], ["example.jpg"]],
                            inputs=img_input,
                            label="示例图片"
                        )
                    with gr.Column(scale=2):
                        gr.Markdown("### 解析结果")
                        meta_output = gr.JSON(
                            label="结构化元数据",
                            show_label=False
                        )
                        parse_btn = gr.Button("开始解析", variant="primary")
                        parse_btn.click(
                            extract_metadata,
                            inputs=img_input,
                            outputs=meta_output
                        )

    return demo

if __name__ == "__main__":
    demo = gradio_interface()
    demo.launch(
        server_port=8080,
        show_error=True,
        favicon_path="https://huggingface.co/front/assets/huggingface_logo.svg"
    )
