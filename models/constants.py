import logging
import os
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.environ.get('env_file', os.environ.get('ENV_FILE', ".env")))

LOGGER = logging.getLogger("jarvis")
DEFAULT_LOG_FORMAT = logging.Formatter(
    datefmt='%b-%d-%Y %I:%M:%S %p',
    fmt='%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(funcName)s - %(message)s'
)
FILENAME = datetime.now().strftime(os.path.join('logs', 'jarvis_%d-%m-%Y.log'))
HANDLER = logging.FileHandler(filename=FILENAME, mode='a')
HANDLER.setFormatter(fmt=DEFAULT_LOG_FORMAT)

LOGGER.addHandler(hdlr=HANDLER)
LOGGER.setLevel(level=logging.INFO)


class ColorCode:
    """Color codes for red and green status indicators."""
    red: str = "&#128308;"  # large green circle
    green: str = "&#128994;"  # large red circle
    blue: str = "&#128309;"  # large blue circle
    yellow: str = "&#128993;"  # large yellow circle


if not os.path.isdir('logs'):
    os.mkdir('logs')


def getenv(key: str, default: str) -> str:
    """Get env vars with both lower case or upper case."""
    return os.environ.get(key.lower()) or os.environ.get(key.upper()) or default


class Constants:
    TIMEZONE = time.strftime("%Z %z")
    DATETIME = datetime.now().strftime("%B %d, %Y - %I:%M %p") + " " + TIMEZONE
    NOTIFICATION = os.path.join(os.getcwd(), 'last_notify.yaml')
    GIT_TOKEN = getenv("git_token", "")

    write = ''.join(['*' for _ in range(120)])
    with open(FILENAME, 'a+') as file:
        file.seek(0)
        if not file.read():
            file.write(f"{write}\n")
        else:
            file.write(f"\n{write}\n")

    skip_schedule = getenv("skip_schedule", "")
    try:
        datetime.strptime(skip_schedule, "%I:%M %p")  # Validate datetime format
    except ValueError as error:
        LOGGER.error(error)

    FILE_PATH = getenv("file_path", os.path.join("Jarvis", "fileio", "processes.yaml"))

    if os.path.isfile(os.path.join('docs', 'CNAME')):
        with open(os.path.join('docs', 'CNAME')) as f:
            webpage = f.read()
    else:
        webpage = None

    recipient = getenv("recipient", "")
