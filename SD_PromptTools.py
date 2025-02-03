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
/* 标签样式 */
#sd_input label, #nai_input label, #img_input label,
#sd_output label, #nai_output label, #meta_output label {
    font-size: 16px !important;
    font-weight: 600 !important;
    color: #2c3e50 !important;
}

/* 冷色调按钮 */
.primary-btn {
    background: linear-gradient(45deg, #4a90e2, #5fa3ec) !important;
    border-color: #4a90e2 !important;
    color: white !important;
}

.primary-btn:hover {
    background: linear-gradient(45deg, #3b7cb1, #4e8ac4) !important;
}

/* 辅助样式 */
.warning-msg {
    color: #e74c3c !important;
    font-weight: 500 !important;
}
"""

# ----------------------
# 提示词转换核心逻辑
# ----------------------
def round_to_step(number: float, step: float = 0.05) -> float:
    """精确到指定步长的四舍五入"""
    return round(number / step) * step

def parse_brackets(text: str) -> List[Tuple[str, float]]:
    """解析嵌套括号结构（支持最大8层嵌套）"""
    stack = []
    current_tag = ""
    weight_stack = [1.0]
    depth = 0
    max_depth = 8
    
    for char in text:
        if char == '{':
            if depth >= max_depth:
                continue
            weight_stack.append(weight_stack[-1] * 1.05)
            depth += 1
        elif char == '[':
            if depth >= max_depth:
                continue
            weight_stack.append(weight_stack[-1] * 0.95)
            depth += 1
        elif char in '}]':
            if depth == 0:
                continue
            if current_tag:
                stack.append((current_tag.strip(), round_to_step(weight_stack[-1])))
                current_tag = ""
            weight_stack.pop()
            depth = max(0, depth-1)
        else:
            current_tag += char
            
    if current_tag:
        stack.append((current_tag.strip(), round_to_step(weight_stack[-1])))
    return stack

def sd_to_nai(prompt: str) -> str:
    """SD转NAI提示词转换"""
    try:
        # 处理特殊标记
        prompt = re.sub(r'\b(artist|style|camera):', lambda m: f"{m.group(1)}_", prompt)
        
        # 解析带权重的标签
        tags_with_weights = parse_brackets(prompt)
        
        # 转换格式
        result = []
        for tag, weight in tags_with_weights:
            if abs(weight - 1.0) < 0.001:
                result.append(tag)
            else:
                count = round((weight - 1.0) / 0.05)
                if count > 0:
                    replacement = '{'*count + tag + '}'*count
                else:
                    replacement = '['*abs(count) + tag + ']'*abs(count)
                result.append(replacement)
        
        # 后处理
        return ' '.join(result).replace('_', ' ')
    
    except Exception as e:
        return f"转换错误: {str(e)}"

def novel_to_comfy(prompt: str) -> str:
    """NAI转SD提示词转换"""
    try:
        # 解析嵌套结构
        tags = parse_brackets(prompt)
        
        # 转换为SD格式
        result = []
        for tag, weight in tags:
            if abs(weight - 1.0) < 0.001:
                result.append(tag)
            else:
                result.append(f"({tag}:{weight:.2f})")
        
        return ', '.join(result)
    
    except Exception as e:
        return f"转换错误: {str(e)}"

# ----------------------
# 图片元数据解析
# ----------------------
def parse_webui_metadata(text: str) -> Dict:
    """解析WebUI格式元数据"""
    result = {}
    parts = text.split('Negative prompt: ')
    result['prompt'] = parts[0].strip()
    
    if len(parts) > 1:
        other_params = parts[1].split('Steps: ')
        result['negative_prompt'] = other_params[0].strip()
        if len(other_params) > 1:
            result['parameters'] = 'Steps: ' + other_params[1]
    return result

def extract_metadata(file_path: str) -> Dict:
    """增强版元数据解析"""
    try:
        img = Image.open(file_path)
        metadata = {}
        
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
                                key = data.split(b'\x00', 1)[0].decode('latin1')
                                value = data.split(b'\x00', 1)[1].decode('utf-8', 'ignore')
                                metadata[key] = value
                            except:
                                continue
                    except struct.error:
                        break

        elif img.format in ['JPEG', 'WEBP']:
            exif = img.getexif()
            if exif and 37510 in exif:  # UserComment
                try:
                    user_comment = exif[37510].decode('utf-8').replace('\x00', '')[7:]
                    metadata.update(parse_webui_metadata(user_comment))
                except:
                    pass

        # 结构化处理
        if 'parameters' in metadata:
            return parse_webui_metadata(metadata['parameters'])
        return metadata if metadata else {"warning": "未检测到有效元数据"}
    
    except Exception as e:
        return {"error": f'元数据解析失败: {str(e)}'}

# ----------------------
# Gradio界面
# ----------------------
def gradio_interface():
    with gr.Blocks(title="SD Prompt工具集", css=custom_css) as demo:
        with gr.Tabs():
            # 提示词转换界面
            with gr.TabItem("提示词转换器"):
                gr.Markdown("## 🔄 双向提示词格式转换")
                with gr.Row():
                    with gr.Column():
                        sd_input = gr.Textbox(
                            lines=6,
                            placeholder="输入SD格式提示词...",
                            label="Stable Diffusion 格式",
                            elem_id="sd_input"
                        )
                        convert_sd_btn = gr.Button(
                            "转换为 NovelAI 格式 →",
                            variant="primary",
                            elem_classes="primary-btn"
                        )
                        nai_output = gr.Textbox(
                            lines=6,
                            label="NovelAI 格式输出",
                            interactive=False,
                            elem_id="nai_output"
                        )
                    
                    with gr.Column():
                        nai_input = gr.Textbox(
                            lines=6,
                            placeholder="输入NovelAI格式提示词...",
                            label="NovelAI 格式",
                            elem_id="nai_input"
                        )
                        convert_nai_btn = gr.Button(
                            "转换为 SD 格式 →",
                            variant="primary",
                            elem_classes="primary-btn"
                        )
                        sd_output = gr.Textbox(
                            lines=6,
                            label="Stable Diffusion 格式输出",
                            interactive=False,
                            elem_id="sd_output"
                        )
                
                # 绑定事件
                convert_sd_btn.click(
                    fn=sd_to_nai,
                    inputs=sd_input,
                    outputs=nai_output
                )
                convert_nai_btn.click(
                    fn=novel_to_comfy,
                    inputs=nai_input,
                    outputs=sd_output
                )

            # 图片元数据界面
            with gr.TabItem("图片信息解析"):
                gr.Markdown("## 📷 支持PNG/JPEG/WEBP格式解析")
                with gr.Row():
                    img_input = gr.Image(
                        type="filepath",
                        label="上传图片文件",
                        elem_id="img_input"
                    )
                    meta_output = gr.JSON(
                        label="解析结果",
                        elem_id="meta_output",
                        value={"status": "等待上传图片..."}
                    )
                
                parse_btn = gr.Button(
                    "解析元数据",
                    variant="primary",
                    elem_classes="primary-btn"
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