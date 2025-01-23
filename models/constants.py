import logging
import os
import pathlib
import sys
import time
from datetime import datetime, timedelta
from threading import Thread
from typing import List, Union

from pydantic import BaseModel, DirectoryPath, EmailStr, FilePath, HttpUrl, NewPath
from pydantic_settings import BaseSettings

if sys.version_info.minor > 10:
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Override for python 3.10 due to lack of StrEnum."""


REPOSITORY = pathlib.Path(__file__).parent.parent


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
    log_retention: int = 3

    class Config:
        """Environment variables configuration."""

        env_prefix = ""
        env_file = (
            os.getenv("env_file")
            or os.getenv("ENV_FILE")
            or os.path.join(REPOSITORY, ".env")
        )
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


def add_spacing(log_file: str) -> None:
    """Add a unique line in between, to indicate new log timestamp.

    Args:
        log_file: Name of the log file.
    """
    write: str = "".join(["*" for _ in range(120)])
    with open(log_file, "a+") as file:
        file.seek(0)
        if not file.read():
            file.write(f"{write}\n")
        else:
            file.write(f"\n{write}\n")
        file.flush()


def cleanup_logs(directory: str, filename: str) -> None:
    """Deletes previous days' log file as per the log retention period.

    Args:
        directory: Directory where logs are stored.
        filename: Filename format for the log files.
    """
    retain = [
        (datetime.now() - timedelta(days=i)).strftime(os.path.join(directory, filename))
        for i in range(env.log_retention)
    ]
    for file in os.listdir(directory):
        file = os.path.join(directory, file)
        if file not in retain:
            os.remove(file)


def get_logger(
    name: str, log_directory: Union[DirectoryPath, NewPath]
) -> logging.Logger:
    """Customize logger as per the environment variables set.

    Args:
        name: Name of the logger.
        log_directory: Directory to store logs.

    Returns:
        logging.Logger:
        Returns the customized logger.
    """
    logger = logging.getLogger(name)
    log_filename = "jarvis_%d-%m-%Y.log"
    log_file = datetime.now().strftime(os.path.join(log_directory, log_filename))
    if env.log == LogOptions.file:
        if os.path.isdir(log_directory):
            Thread(
                target=cleanup_logs,
                kwargs=dict(directory=log_directory, filename=log_filename),
                daemon=True,
            ).start()
            add_spacing(log_file)
        else:
            os.mkdir(log_directory)
        handler = logging.FileHandler(filename=log_file, mode="a")
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
        with open(os.path.join(REPOSITORY, "docs", "CNAME")) as f:
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
        REPOSITORY, "last_notify.yaml"
    )
    EMAIL_TEMPLATE: Union[FilePath, NewPath] = os.path.join(
        REPOSITORY, "templates", "email_template.html"
    )
    WEB_TEMPLATE: Union[FilePath, NewPath] = os.path.join(
        REPOSITORY, "templates", "web_template.html"
    )
    LOG_DIRECTORY: Union[DirectoryPath, NewPath] = os.path.join(REPOSITORY, "logs")
    INDEX_FILE: Union[FilePath, NewPath] = os.path.join(
        REPOSITORY, "docs", "index.html"
    )
    BASE_URL: HttpUrl = "https://api.github.com/repos/thevickypedia/JarvisMonitor"
    DOCS_BRANCH: str = "docs"
    INDEX_URL: str = f"{BASE_URL}/contents/docs/index.html"
    DEFAULT_BRANCH: str = "main"
    COMMIT_MESSAGE: str = f"Updated as of {DATETIME}"
    webpage: Union[str, None] = get_webpage()


static = Constants()
color_codes = ColorCode()
LOGGER = get_logger("jarvis", static.LOG_DIRECTORY)

if env.skip_schedule:
    try:
        # Validate datetime format
        datetime.strptime(env.skip_schedule, static.SKIPPER_FORMAT)
    except ValueError as error:
        LOGGER.warning(error)
