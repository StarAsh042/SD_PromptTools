import envsetup

# 必须在 import gradio 之前：本地回环绕过代理、关闭遥测
envsetup.prepare()

from gradio_interface import GradioInterface  # noqa: E402
from logging_config import setup_logging  # noqa: E402

logger = setup_logging()


def main():
    try:
        interface = GradioInterface()
        interface.launch()
    except Exception:
        logger.exception("程序启动失败")
        raise


if __name__ == "__main__":
    main()
