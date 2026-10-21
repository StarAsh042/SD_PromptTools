import json

import gradio as gr

import i18n
from config import Config
from prompt_converter import PromptConverter
from metadata_extractor import MetadataExtractor

_HEAD_TEMPLATE = """<script>
(function () {
  var TITLES = __TITLES__;
  window.__sdpSetLocale = function (locale) {
    document.documentElement.lang = locale;
    if (TITLES[locale]) {
      document.title = TITLES[locale];
    }
  };
  window.__sdpSetLocale(__DEFAULT_LOCALE__);
})();
</script>"""


class GradioInterface:
    def __init__(self):
        # (组件, [(属性, 文案 key), ...], 占位符变量)
        self._i18n_targets = []
        self.demo = self._create_interface()

    def _bind(self, component, *specs, **variables):
        """specs 是 (属性, key) 的若干对；同一组件可同时绑定 label 与 placeholder。"""
        self._i18n_targets.append((component, specs, variables))
        return component

    def _translated_updates(self):
        updates = []
        for _component, specs, variables in self._i18n_targets:
            updates.append(gr.update(**{attr: i18n.t(key, **variables) for attr, key in specs}))
        return updates

    def switch_language(self, locale: str):
        """切换界面语言：只更新文案，不重建组件树，也不动用户已输入的内容。"""
        i18n.set_locale(locale)
        return self._translated_updates()

    @staticmethod
    def _head() -> str:
        catalogs = i18n.load_catalogs()
        titles = {locale: catalogs[locale]["app.title"] for locale in i18n.available_locales()}
        return (
            _HEAD_TEMPLATE
            .replace("__TITLES__", json.dumps(titles, ensure_ascii=False))
            .replace("__DEFAULT_LOCALE__", json.dumps(i18n.get_locale()))
        )

    def _create_converter_tab(self):
        """
        创建提示词格式转换器标签页
        """
        with gr.Tab(i18n.t("tabs.converter")) as converter_tab:
            self._bind(converter_tab, ("label", "tabs.converter"))
            self._bind(gr.Markdown(i18n.t("converter.heading")), ("value", "converter.heading"))
            with gr.Row():
                # NAI格式输入区域
                with gr.Column():
                    nai_input = gr.Textbox(
                        label=i18n.t("converter.nai_label"),
                        placeholder=i18n.t("converter.nai_placeholder"),
                        lines=8
                    )
                    self._bind(
                        nai_input,
                        ("label", "converter.nai_label"),
                        ("placeholder", "converter.nai_placeholder"),
                    )
                    with gr.Row():
                        nai_to_sd_btn = self._bind(
                            gr.Button(i18n.t("converter.nai_to_sd")), ("value", "converter.nai_to_sd"))
                        nai_copy_btn = self._bind(
                            gr.Button(i18n.t("common.copy")), ("value", "common.copy"))
                        nai_reset_btn = self._bind(
                            gr.Button(i18n.t("common.reset")), ("value", "common.reset"))
                # SD格式输入区域
                with gr.Column():
                    sd_input = gr.Textbox(
                        label=i18n.t("converter.sd_label"),
                        placeholder=i18n.t("converter.sd_placeholder"),
                        lines=8
                    )
                    self._bind(
                        sd_input,
                        ("label", "converter.sd_label"),
                        ("placeholder", "converter.sd_placeholder"),
                    )
                    with gr.Row():
                        sd_to_nai_btn = self._bind(
                            gr.Button(i18n.t("converter.sd_to_nai")), ("value", "converter.sd_to_nai"))
                        sd_copy_btn = self._bind(
                            gr.Button(i18n.t("common.copy")), ("value", "common.copy"))
                        sd_reset_btn = self._bind(
                            gr.Button(i18n.t("common.reset")), ("value", "common.reset"))

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
        with gr.Tab(i18n.t("tabs.metadata")) as metadata_tab:
            self._bind(metadata_tab, ("label", "tabs.metadata"))
            with gr.Row():
                with gr.Column(scale=1):
                    img_input = gr.Image(
                        label=i18n.t("metadata.upload_label"),
                        height=500,
                        sources=["upload"],
                        type="filepath"
                    )
                    self._bind(img_input, ("label", "metadata.upload_label"))
                with gr.Column(scale=1):
                    # gr.JSON 不支持 height 参数（gradio 4.x 起），传了会在实例化时抛 TypeError
                    meta_output = gr.JSON(label=i18n.t("metadata.output_label"))
                    self._bind(meta_output, ("label", "metadata.output_label"))
                    img_input.change(
                        fn=MetadataExtractor.extract_metadata,
                        inputs=[img_input],
                        outputs=[meta_output]
                    )

    def _create_interface(self) -> gr.Blocks:
        """
        创建Gradio整体界面
        """
        with gr.Blocks(title=i18n.t("app.title"), head=self._head()) as demo:
            language = gr.Dropdown(
                choices=list(i18n.available_locales()),
                value=i18n.get_locale(),
                label=i18n.t("settings.language"),
                interactive=True,
            )
            self._bind(language, ("label", "settings.language"))
            self._bind(gr.Markdown(i18n.t("app.heading")), ("value", "app.heading"))
            with gr.Tabs():
                self._create_converter_tab()
                self._create_metadata_tab()
            footer = gr.Markdown(
                i18n.t("app.footer", version=gr.__version__)
            )
            self._bind(footer, ("value", "app.footer"), version=gr.__version__)

            language.change(
                fn=self.switch_language,
                inputs=[language],
                outputs=[target[0] for target in self._i18n_targets],
                js="(locale) => { window.__sdpSetLocale(locale); return locale; }",
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
