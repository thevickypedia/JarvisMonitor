import logging
import os
import sys
import time
from datetime import datetime
from typing import List, Union

from pydantic import BaseModel, EmailStr, FilePath, HttpUrl, NewPath
from pydantic_settings import BaseSettings

if sys.version_info.minor > 10:
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Override for python 3.10 due to lack of StrEnum."""


class LogOptions(StrEnum):
    """Logging options.

    >>> LogOptions

    """

    file: str = "file"
    stdout: str = "stdout"


class EnvConfig(BaseSettings):
    """Settings to load and validate environment variables.

    >>> EnvConfig

    """

    source_map: Union[FilePath, NewPath]
    git_user: str
    git_token: str
    git_owner: str = "thevickypedia"

    log: LogOptions = LogOptions.file
    debug: bool = False
    gmail_user: Union[EmailStr, None] = None
    gmail_pass: Union[str, None] = None
    recipient: Union[EmailStr, None] = None
    skip_schedule: Union[str, None] = None
    check_existing: bool = True
    override_check: List[int] = [0]

    class Config:
        """Environment variables configuration."""

        env_prefix = ""
        env_file = os.environ.get("env_file", os.environ.get("ENV_FILE", ".env"))
        extra = "allow"


env = EnvConfig()


class ColorCode(BaseModel):
    """Color codes for red and green status indicators.

    >>> ColorCode

    """

    red: str = "&#128308;"  # large green circle
    green: str = "&#128994;"  # large red circle
    blue: str = "&#128309;"  # large blue circle
    yellow: str = "&#128993;"  # large yellow circle


def get_logger(name: str) -> logging.Logger:
    """Customize logger as per the environment variables set.

    Args:
        name: Name of the logger.

    Returns:
        logging.Logger:
        Returns the customized logger.
    """
    logger = logging.getLogger(name)
    log_file = datetime.now().strftime(os.path.join("logs", "jarvis_%d-%m-%Y.log"))
    if env.log == LogOptions.file:
        if not os.path.isdir("logs"):
            os.mkdir("logs")
        handler = logging.FileHandler(filename=log_file, mode="a")
        write: str = "".join(["*" for _ in range(120)])
        with open(log_file, "a+") as file:
            file.seek(0)
            if not file.read():
                file.write(f"{write}\n")
            else:
                file.write(f"\n{write}\n")
            file.flush()
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(
        fmt=logging.Formatter(
            datefmt="%b-%d-%Y %I:%M:%S %p",
            fmt="%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(funcName)s - %(message)s",
        )
    )
    logger.addHandler(hdlr=handler)
    if env.debug:
        logger.setLevel(level=logging.DEBUG)
    else:
        logger.setLevel(level=logging.INFO)
    return logger


def get_webpage() -> Union[str, None]:
    """Tries to get the hosted webpage from CNAME file if available in docs directory.

    Returns:
        str:
        Returns the website mentioned in the CNAME file.
    """
    try:
        with open(os.path.join("docs", "CNAME")) as f:
            return f.read().strip()
    except FileNotFoundError:
        return


class Constants(BaseModel):
    """Static variables loaded into an object.

    >>> Constants

    """

    SKIPPER_FORMAT: str = "%H:%M"
    TIMEZONE: str = time.strftime("%Z %z")
    DATETIME: str = datetime.now().strftime("%B %d, %Y - %I:%M %p") + " " + TIMEZONE
    NOTIFICATION: Union[FilePath, NewPath] = os.path.join(
        os.getcwd(), "last_notify.yaml"
    )
    INDEX_FILE: Union[FilePath, NewPath] = os.path.join("docs", "index.html")
    BASE_URL: HttpUrl = "https://api.github.com/repos/thevickypedia/JarvisMonitor"
    DOCS_BRANCH: str = "docs"
    INDEX_URL: str = f"{BASE_URL}/contents/docs/index.html"
    DEFAULT_BRANCH: str = "main"
    COMMIT_MESSAGE: str = f"Updated as of {DATETIME}"
    webpage: Union[str, None] = get_webpage()


static = Constants()
color_codes = ColorCode()
LOGGER = get_logger("jarvis")

if env.skip_schedule:
    try:
        # Validate datetime format
        datetime.strptime(env.skip_schedule, static.SKIPPER_FORMAT)
    except ValueError as error:
        LOGGER.warning(error)
