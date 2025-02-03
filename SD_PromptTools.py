# SD_PromptTools.py
import gradio as gr
from PIL import Image
import piexif
import re
import json
from typing import List, Dict, Tuple
import struct

# ----------------------
# 样式配置
# ----------------------
custom_css = """
/* 增强样式 */
.container {
    max-width: 800px !important;
}
.label-lg {
    font-size: 16px !important;
    font-weight: 600 !important;
    color: #2c3e50 !important;
}
.vert-container {
    display: flex !important;
    flex-direction: column !important;
    gap: 12px !important;
}
.centered-buttons {
    margin: 20px 0 !important;
    justify-content: center !important;
}
.primary-btn {
    background: linear-gradient(45deg, #4a90e2, #5fa3ec) !important;
    border: none !important;
    color: white !important;
    min-width: 180px !important;
}
.meta-section {
    border: 1px solid #e0e0e0 !important;
    border-radius: 8px !important;
    padding: 20px !important;
}
"""

# ----------------------
# 提示词转换核心逻辑（拆分版本）
# ----------------------
def sd_to_nai(prompt: str) -> str:
    """SD转NAI专用转换"""
    try:
        # 处理特殊标记
        prompt = re.sub(r'\b(artist|style|camera):', lambda m: f"{m.group(1)}_", prompt)
        
        # 解析权重结构
        tags = []
        current_tag = ""
        weight_stack = [1.0]
        depth = 0
        
        for char in prompt:
            if char == '(':
                if current_tag:
                    tags.append((current_tag.strip(), weight_stack[-1]))
                    current_tag = ""
                weight_stack.append(weight_stack[-1] * 1.05)
                depth += 1
            elif char == ')':
                if current_tag:
                    tags.append((current_tag.strip(), weight_stack[-1]))
                    current_tag = ""
                if depth > 0:
                    weight_stack.pop()
                    depth = max(0, depth-1)
            else:
                current_tag += char
        
        if current_tag:
            tags.append((current_tag.strip(), weight_stack[-1]))
            
        # 转换格式
        result = []
        for tag, weight in tags:
            weight = round(weight, 2)
            if abs(weight - 1.0) < 0.01:
                result.append(tag)
            else:
                count = round((weight - 1.0) / 0.05)
                if count > 0:
                    result.append('{'*count + tag + '}'*count)
                else:
                    result.append('['*abs(count) + tag + ']'*abs(count))
        
        return ' '.join(result).replace('_', ' ')
    
    except Exception as e:
        return f"SD→NAI转换错误: {str(e)}"

def nai_to_sd(prompt: str) -> str:
    """NAI转SD专用转换"""
    try:
        # 解析嵌套结构
        tags = []
        current_tag = ""
        weight_stack = [1.0]
        depth = 0
        
        for char in prompt:
            if char == '{':
                weight_stack.append(weight_stack[-1] * 1.05)
                depth += 1
            elif char == '[':
                weight_stack.append(weight_stack[-1] * 0.95)
                depth += 1
            elif char in '}]':
                if current_tag:
                    tags.append((current_tag.strip(), round(weight_stack[-1], 2)))
                    current_tag = ""
                if depth > 0:
                    weight_stack.pop()
                    depth = max(0, depth-1)
            else:
                current_tag += char
                
        if current_tag:
            tags.append((current_tag.strip(), round(weight_stack[-1], 2)))
            
        # 生成SD格式
        formatted = []
        for tag, weight in tags:
            if abs(weight - 1.0) < 0.01:
                formatted.append(tag)
            else:
                formatted.append(f"({tag}:{weight:.2f})")
        
        # 去除多余逗号
        return ', '.join([x for x in formatted if x.strip()])
    
    except Exception as e:
        return f"NAI→SD转换错误: {str(e)}"

# ----------------------
# 图片元数据解析（增强版）
# ----------------------
def extract_metadata(file_path: str) -> Dict:
    """支持多格式的元数据解析"""
    try:
        img = Image.open(file_path)
        metadata = {}
        
        # PNG格式处理
        if img.format == 'PNG':
            with open(file_path, 'rb') as f:
                while True:
                    try:
                        length_bytes = f.read(4)
                        if not length_bytes: break
                        length = struct.unpack('>I', length_bytes)[0]
                        chunk_type = f.read(4).decode('ascii')
                        data = f.read(length)
                        f.read(4)  # CRC
                        
                        if chunk_type in ['tEXt', 'iTXt']:
                            try:
                                key_part = data.split(b'\x00', 1)[0]
                                key = key_part.decode('latin1', 'ignore')
                                value = data[len(key_part)+1:].decode('utf-8', 'ignore')
                                metadata[key] = value.strip('\x00')
                            except Exception as e:
                                continue
                    except struct.error:
                        break

        # JPEG/WEBP格式处理
        elif img.format in ['JPEG', 'WEBP']:
            exif_data = img.getexif()
            if exif_data:
                # 处理UserComment (37510)
                if 37510 in exif_data:
                    try:
                        user_comment = exif_data[37510].decode('utf-8', 'ignore')
                        if user_comment.startswith('UNICODE'):
                            params = user_comment[7:].split('Negative prompt:')
                            if len(params) > 1:
                                metadata['Prompt'] = params[0].strip()
                                metadata['Negative Prompt'] = params[1].split('Steps:')[0].strip()
                                metadata['Parameters'] = 'Steps:' + params[1].split('Steps:')[1]
                    except Exception as e:
                        pass

        # 结构化处理
        if not metadata:
            return {"status": "未检测到有效元数据"}
            
        # 合并WebUI格式
        if 'parameters' in metadata:
            try:
                params = metadata['parameters'].split('Negative prompt:')
                metadata['Prompt'] = params[0].strip()
                if len(params) > 1:
                    neg_parts = params[1].split('Steps:')
                    metadata['Negative Prompt'] = neg_parts[0].strip()
                    metadata['Parameters'] = 'Steps:' + neg_parts[1] if len(neg_parts)>1 else ''
            except:
                pass
            
        return metadata
    
    except Exception as e:
        return {"error": f"解析失败: {str(e)}"}

# ----------------------
# Gradio界面（优化布局）
# ----------------------
def gradio_interface():
    with gr.Blocks(title="SD工具集", css=custom_css) as demo:
        gr.Markdown("# 🛠️ Stable Diffusion 实用工具集")
        
        with gr.Tabs():
            # 提示词转换器
            with gr.TabItem("提示词转换"):
                with gr.Column(elem_classes="vert-container"):
                    gr.Markdown("### SD ↔ NAI 双向转换")
                    
                    # SD转NAI
                    with gr.Column():
                        sd_input = gr.Textbox(
                            lines=3,
                            placeholder="输入SD格式提示词...",
                            label="SD输入",
                            elem_classes="label-lg"
                        )
                    with gr.Row(elem_classes="centered-buttons"):
                        sd_to_nai_btn = gr.Button("SD → NAI 转换", elem_classes="primary-btn")
                    with gr.Column():
                        nai_output = gr.Textbox(
                            lines=3,
                            label="NAI输出",
                            interactive=False,
                            elem_classes="label-lg"
                        )
                    
                    # 分隔线
                    gr.Markdown("---")
                    
                    # NAI转SD
                    with gr.Column():
                        nai_input = gr.Textbox(
                            lines=3,
                            placeholder="输入NAI格式提示词...",
                            label="NAI输入",
                            elem_classes="label-lg"
                        )
                    with gr.Row(elem_classes="centered-buttons"):
                        nai_to_sd_btn = gr.Button("NAI → SD 转换", elem_classes="primary-btn")
                    with gr.Column():
                        sd_output = gr.Textbox(
                            lines=3,
                            label="SD输出",
                            interactive=False,
                            elem_classes="label-lg"
                        )
                
                # 绑定事件
                sd_to_nai_btn.click(
                    fn=sd_to_nai,
                    inputs=sd_input,
                    outputs=nai_output
                )
                nai_to_sd_btn.click(
                    fn=nai_to_sd,
                    inputs=nai_input,
                    outputs=sd_output
                )

            # 图片元数据解析
            with gr.TabItem("图片解析"):
                with gr.Row():
                    with gr.Column(scale=1):
                        img_input = gr.Image(
                            type="filepath",
                            label="上传图片",
                            elem_classes="label-lg",
                            height=400
                        )
                    with gr.Column(scale=2, elem_classes="meta-section"):
                        with gr.Column():
                            gr.Markdown("### 元数据解析结果")
                            parse_btn = gr.Button("解析元数据", elem_classes="primary-btn")
                            meta_output = gr.JSON(
                                label="解析结果",
                                show_label=False,
                                value={"status": "等待上传图片..."}
                            )
                
                # 事件绑定
                parse_btn.click(
                    fn=extract_metadata,
                    inputs=img_input,
                    outputs=meta_output
                )

    return demo

if __name__ == "__main__":
    demo = gradio_interface()
    demo.launch(server_port=8080)
