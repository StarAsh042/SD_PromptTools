import gradio as gr
from config import Config
from prompt_converter import PromptConverter
from metadata_extractor import MetadataExtractor

class GradioInterface:
    def __init__(self):
        self.demo = self._create_interface()

    def _create_converter_tab(self):
        """
        创建提示词格式转换器标签页
        """
        with gr.Tab("提示词格式转换器"):
            gr.Markdown("## 🔄 双向格式转换引擎")
            with gr.Row():
                # NAI格式输入区域
                with gr.Column():
                    nai_input = gr.Textbox(
                        label="NAI格式",
                        placeholder="输入NAI格式的提示词...",
                        lines=8
                    )
                    with gr.Row():
                        nai_to_sd_btn = gr.Button("转换为SD格式 →")
                        nai_copy_btn = gr.Button("📋 复制")
                        nai_reset_btn = gr.Button("🔄 重置")
                # SD格式输入区域
                with gr.Column():
                    sd_input = gr.Textbox(
                        label="SD格式",
                        placeholder="输入SD格式的提示词...",
                        lines=8
                    )
                    with gr.Row():
                        sd_to_nai_btn = gr.Button("← 转换为NAI格式")
                        sd_copy_btn = gr.Button("📋 复制")
                        sd_reset_btn = gr.Button("🔄 重置")
                
                # 绑定转换按钮事件
                nai_to_sd_btn.click(
                    fn=PromptConverter.nai_to_sd,
                    inputs=[nai_input],
                    outputs=[sd_input]
                )
                sd_to_nai_btn.click(
                    fn=PromptConverter.sd_to_nai,
                    inputs=[sd_input],
                    outputs=[nai_input]
                )
                
                # 绑定复制按钮事件（前端使用JS写入剪贴板）
                nai_copy_btn.click(
                    fn=lambda x: x,
                    inputs=[nai_input],
                    outputs=[nai_input],
                    api_name=False,
                    js="async (x) => { await navigator.clipboard.writeText(x); return x }"
                )
                sd_copy_btn.click(
                    fn=lambda x: x,
                    inputs=[sd_input],
                    outputs=[sd_input],
                    api_name=False,
                    js="async (x) => { await navigator.clipboard.writeText(x); return x }"
                )
                
                # 绑定重置按钮事件
                nai_reset_btn.click(fn=lambda: "", outputs=[nai_input])
                sd_reset_btn.click(fn=lambda: "", outputs=[sd_input])

    def _create_metadata_tab(self):
        """
        创建图片元数据探测器标签页
        """
        with gr.Tab("元数据探测器"):
            with gr.Row():
                with gr.Column(scale=1):
                    img_input = gr.Image(
                        label="上传图片",
                        height=500,
                        sources=["upload"],
                        type="filepath"
                    )
                with gr.Column(scale=1):
                    meta_output = gr.JSON(
                        label="元数据",
                        height=500
                    )
                    img_input.change(
                        fn=MetadataExtractor.extract_metadata,
                        inputs=[img_input],
                        outputs=[meta_output]
                    )

    def _create_interface(self) -> gr.Blocks:
        """
        创建Gradio整体界面
        """
        with gr.Blocks(title="SD提示词工具集") as demo:
            gr.Markdown("# 🚀 SD提示词工具集")
            with gr.Tabs():
                self._create_converter_tab()
                self._create_metadata_tab()
            gr.Markdown(
                f"<div style='text-align: center; margin-top: 20px;'>"
                f"Powered by <a href='https://github.com/StarAsh042' target='_blank'>StarAsh042</a> | "
                f"Gradio {gr.__version__}</div>"
            )
        return demo

    def launch(self):
        """
        启动Gradio界面
        """
        self.demo.launch(
            server_port=Config.DEFAULT_PORT,
            server_name="127.0.0.1",
            show_error=True,
            share=False,
            inbrowser=True,
            max_threads=Config.MAX_THREADS
        ) 