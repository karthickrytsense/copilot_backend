import logging
import os

log_file_name = './log/copilot_chatbot.log'
os.makedirs(os.path.dirname(log_file_name), exist_ok=True)

logging.basicConfig(
    filename = log_file_name,
    level = logging.INFO,
    filemode = 'a',
    format = '%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.propagate = False
logger.handlers.clear()

main_handler = logging.FileHandler(log_file_name, mode='a', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
main_handler.setFormatter(formatter)
logger.addHandler(main_handler)