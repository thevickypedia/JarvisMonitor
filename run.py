import base64
import json
import os
from datetime import datetime

import requests

import monitor
from models.constants import LOGGER, static

SESSION = requests.Session()
SESSION.headers = {"Authorization": "token " + static.GIT_TOKEN}
URL = (
    "https://api.github.com/repos/thevickypedia/JarvisMonitor/contents/docs/index.html"
)
DOCS_BRANCH = "docs"
COMMIT_MESSAGE = f"Updated as of {datetime.now().strftime('%d/%m/%Y %H:%M:%S %Z %z')}"


def push_to_github():
    """Commit and push to GitHub."""
    try:
        with open(static.INDEX_FILE, "rb") as file:
            base64content = base64.b64encode(file.read())
    except FileNotFoundError as error:
        LOGGER.critical(error)
        return
    decoded_content = base64content.decode("utf-8")
    response = SESSION.get(f"{URL}?ref={DOCS_BRANCH}")
    data = response.json()
    if response.ok:
        LOGGER.info("Fetch successful!")
        sha = data["sha"]
        push = decoded_content.strip() != data["content"].strip()
    else:
        LOGGER.info("Creating a new file in %s branch", DOCS_BRANCH)
        sha = None
        push = True
    if push:
        LOGGER.info("Pushing changes to GitHub")
        payload = {
            "message": COMMIT_MESSAGE,
            "branch": DOCS_BRANCH,
            "content": decoded_content,
        }
        if sha:
            payload["sha"] = sha
        SESSION.headers["Content-Type"] = "application/json"
        resp = SESSION.put(URL, data=json.dumps(payload))
        assert resp.ok, resp.text
        LOGGER.info(resp.json())
    else:
        LOGGER.info("Nothing to update")
    # Delete the file since there is no branch checkout happening
    os.remove(static.INDEX_FILE)


if __name__ == "__main__":
    monitor.main()
    push_to_github()
