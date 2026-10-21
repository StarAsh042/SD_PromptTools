from gradio_interface import GradioInterface
from logging_config import setup_logging

logger = setup_logging()

def main():
    try:
        interface = GradioInterface()
        interface.launch()
    except Exception as e:
        logger.exception("程序启动失败")
        raise

if __name__ == "__main__":
    main() 