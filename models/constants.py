import logging
import os
import time
from datetime import datetime
from typing import Union

from pydantic import BaseModel, EmailStr, FilePath, HttpUrl, NewPath
from pydantic_settings import BaseSettings

LOGGER = logging.getLogger("jarvis")
DEFAULT_LOG_FORMAT = logging.Formatter(
    datefmt="%b-%d-%Y %I:%M:%S %p",
    fmt="%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(funcName)s - %(message)s",
)
LOG_FILE: str = datetime.now().strftime(os.path.join("logs", "jarvis_%d-%m-%Y.log"))
HANDLER = logging.FileHandler(filename=LOG_FILE, mode="a")
HANDLER.setFormatter(fmt=DEFAULT_LOG_FORMAT)
LOGGER.addHandler(hdlr=HANDLER)

if not os.path.isdir("logs"):
    os.mkdir("logs")


class EnvConfig(BaseSettings):
    """Settings to load and validate environment variables.

    >>> EnvConfig

    """

    source_map: Union[FilePath, NewPath]
    git_token: str

    debug: bool = False
    gmail_user: Union[EmailStr, None] = None
    gmail_pass: Union[str, None] = None
    recipient: Union[EmailStr, None] = None
    skip_schedule: str = None
    check_existing: bool = True

    class Config:
        """Environment variables configuration."""

        env_prefix = ""
        env_file = os.environ.get("env_file", os.environ.get("ENV_FILE", ".env"))
        extra = "allow"


env = EnvConfig()


class ColorCode(BaseModel):
    """Color codes for red and green status indicators."""

    red: str = "&#128308;"  # large green circle
    green: str = "&#128994;"  # large red circle
    blue: str = "&#128309;"  # large blue circle
    yellow: str = "&#128993;"  # large yellow circle


if env.debug:
    LOGGER.setLevel(level=logging.DEBUG)
else:
    LOGGER.setLevel(level=logging.INFO)

if env.skip_schedule:
    try:
        datetime.strptime(env.skip_schedule, "%I:%M %p")  # Validate datetime format
    except ValueError as error:
        LOGGER.warning(error)


def get_webpage() -> Union[str, None]:
    """Tries to get the hosted webpage from CNAME file if available in docs directory."""
    try:
        with open(os.path.join("docs", "CNAME")) as f:
            return f.read().strip()
    except FileNotFoundError:
        return


class Constants(BaseModel):
    """Static variables loaded into an object.

    >>> Constants

    """

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

write: str = "".join(["*" for _ in range(120)])
with open(LOG_FILE, "a+") as file:
    file.seek(0)
    if not file.read():
        file.write(f"{write}\n")
    else:
        file.write(f"\n{write}\n")
    file.flush()
