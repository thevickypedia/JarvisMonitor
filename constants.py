import logging
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

if not os.path.isdir('logs'):
    os.mkdir('logs')

DATETIME = datetime.now().strftime("%B %d, %Y - %I:%M %p") + " " + datetime.utcnow().astimezone().tzname()

DEFAULT_LOG_FORMAT = logging.Formatter(
    datefmt='%b-%d-%Y %I:%M:%S %p',
    fmt='%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(funcName)s - %(message)s'
)
FILENAME = os.path.join('logs', 'jarvis_%d-%m-%Y.log')

FILE_PATH = os.environ.get("FILE_PATH", "Jarvis/fileio/processes.yaml")

LOGGER = logging.getLogger('jarvis')

HANDLER = logging.FileHandler(filename=datetime.now().strftime(FILENAME), mode='a')
HANDLER.setFormatter(fmt=DEFAULT_LOG_FORMAT)

LOGGER.addHandler(hdlr=HANDLER)
LOGGER.info(f"\n\nMonitoring health check at: {DATETIME}\n")
