# SD_PromptTools.py
import gradio as gr
from PIL import Image
import re
import struct
from typing import List, Dict, Tuple

# ----------------------
# 提示词转换核心逻辑（简化版）
# ----------------------
def sd_to_nai(prompt: str) -> str:
    """SD转NAI专用转换"""
    try:
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
        
        return ' '.join(result)
    
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
        
        return ' '.join(formatted)
    
    except Exception as e:
        return f"NAI→SD转换错误: {str(e)}"

# ----------------------
# 图片元数据解析
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
                            except:
                                continue
                    except struct.error:
                        break

        # JPEG/WEBP格式处理
        elif img.format in ['JPEG', 'WEBP']:
            exif_data = img.getexif()
            if exif_data and 37510 in exif_data:  # UserComment
                try:
                    user_comment = exif_data[37510].decode('utf-8', 'ignore')
                    if user_comment.startswith('UNICODE'):
                        params = user_comment[7:].split('Negative prompt:')
                        if len(params) > 1:
                            metadata['Prompt'] = params[0].strip()
                            metadata['Negative Prompt'] = params[1].split('Steps:')[0].strip()
                            metadata['Parameters'] = 'Steps:' + params[1].split('Steps:')[1]
                except:
                    pass

        return metadata if metadata else {"status": "未检测到有效元数据"}
    
    except Exception as e:
        return {"error": f"解析失败: {str(e)}"}

# ----------------------
# Gradio界面（优化布局）
# ----------------------
def gradio_interface():
    with gr.Blocks(title="SD工具集") as demo:
        gr.Markdown("# 🛠️ Stable Diffusion 实用工具集")
        
        with gr.Tabs():
            # 提示词转换器
            with gr.TabItem("提示词转换"):
                with gr.Column():
                    # SD转NAI
                    with gr.Row():
                        with gr.Column():
                            sd_input = gr.Textbox(
                                lines=3,
                                placeholder="输入SD格式提示词...",
                                label="SD输入"
                            )
                        with gr.Column():
                            nai_output = gr.Textbox(
                                lines=3,
                                label="NAI输出",
                                interactive=False
                            )
                    gr.Button("SD → NAI 转换").click(
                        fn=sd_to_nai,
                        inputs=sd_input,
                        outputs=nai_output
                    )
                    
                    gr.Markdown("---")
                    
                    # NAI转SD
                    with gr.Row():
                        with gr.Column():
                            nai_input = gr.Textbox(
                                lines=3,
                                placeholder="输入NAI格式提示词...",
                                label="NAI输入"
                            )
                        with gr.Column():
                            sd_output = gr.Textbox(
                                lines=3,
                                label="SD输出",
                                interactive=False
                            )
                    gr.Button("NAI → SD 转换").click(
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
                            height=400
                        )
                    with gr.Column(scale=2):
                        gr.Markdown("### 元数据解析结果")
                        with gr.Row():
                            parse_btn = gr.Button("解析元数据")
                        meta_output = gr.JSON(
                            label="解析结果",
                            show_label=False,
                            value={"status": "等待上传图片..."}
                        )
                
                parse_btn.click(
                    fn=extract_metadata,
                    inputs=img_input,
                    outputs=meta_output
                )

    return demo

if __name__ == "__main__":
    demo = gradio_interface()
    demo.launch(server_port=8080)
