import sys
from pathlib import Path

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from main import bot
import utils.settings as settings
import logging

if __name__ == '__main__':
    from utils.errorhandling import STARTUP_CHECK
    logging.info(bytes.fromhex(STARTUP_CHECK).decode())
    bot.run(settings.bot_token)
