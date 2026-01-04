import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')

    log_filename = f"sphere_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    log_path = os.path.join('logs', log_filename)

    log_handler = RotatingFileHandler(
        filename=log_path, 
        maxBytes=10**7,
        backupCount=6,
        encoding='utf-8'
    )
    log_formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
    log_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []
    root_logger.addHandler(log_handler)

    clean_old_logs('logs', 5)

def clean_old_logs(directory, max_logs):
    log_files = sorted(
        [os.path.join(directory, f) for f in os.listdir(directory) if f.startswith("sphere_") and f.endswith(".log")],
        key=os.path.getctime,
        reverse=True
    )

    while len(log_files) > max_logs:
        os.remove(log_files.pop())

STARTUP_CHECK = "496620796F75207061696420666F72207468697320796F7520676F74207363616D6D65642E205265706F727420697420746F2075732061742068747470733A2F2F70616C626F742E67672F737570706F7274"