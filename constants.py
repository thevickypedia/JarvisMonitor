import logging
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")


class ColorCode:
    """Color codes for red and green status indicators."""
    red: str = "&#128308;"  # large green circle
    green: str = "&#128994;"  # large red circle
    blue: str = "&#128309;"  # large blue circle


if not os.path.isdir('logs'):
    os.mkdir('logs')

DATETIME = datetime.now().strftime("%B %d, %Y - %I:%M %p") + " " + datetime.utcnow().astimezone().tzname()

DEFAULT_LOG_FORMAT = logging.Formatter(
    datefmt='%b-%d-%Y %I:%M:%S %p',
    fmt='%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(funcName)s - %(message)s'
)
FILENAME = datetime.now().strftime(os.path.join('logs', 'jarvis_%d-%m-%Y.log'))

FILE_PATH = os.environ.get("FILE_PATH", os.path.join("Jarvis", "fileio", "processes.yaml"))

LOGGER = logging.getLogger("jarvis")

HANDLER = logging.FileHandler(filename=FILENAME, mode='a')
HANDLER.setFormatter(fmt=DEFAULT_LOG_FORMAT)

LOGGER.addHandler(hdlr=HANDLER)
LOGGER.setLevel(level=logging.INFO)

write = ''.join(['*' for _ in range(120)])
with open(FILENAME, 'a+') as file:
    file.seek(0)
    if not file.read():
        file.write(f"{write}\n")
    else:
        file.write(f"\n{write}\n")
