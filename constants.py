import logging
import os
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")


class ColorCode:
    """Color codes for red and green status indicators."""
    red: str = "&#128308;"  # large green circle
    green: str = "&#128994;"  # large red circle
    blue: str = "&#128309;"  # large blue circle
    yellow: str = "&#128993;"  # large yellow circle


if not os.path.isdir('logs'):
    os.mkdir('logs')

DATETIME = datetime.now().strftime("%B %d, %Y - %I:%M %p %Z") + " " + time.strftime("%Z %z")

DEFAULT_LOG_FORMAT = logging.Formatter(
    datefmt='%b-%d-%Y %I:%M:%S %p',
    fmt='%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(funcName)s - %(message)s'
)
FILENAME = datetime.now().strftime(os.path.join('logs', 'jarvis_%d-%m-%Y.log'))

NOTIFICATION = os.path.join(os.getcwd(), 'last_notify.yaml')

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

skip_schedule = os.environ.get("SKIP_SCHEDULE") or \
                os.environ.get("skip_schedule") or \
                ""
try:
    datetime.strptime(skip_schedule, "%I:%M %p")  # Validate datetime format
except ValueError as error:
    LOGGER.error(error)

FILE_PATH = os.environ.get("FILE_PATH") or \
            os.environ.get("file_path") or \
            os.path.join("Jarvis", "fileio", "processes.yaml")
