import base64
import json
import os
from datetime import datetime

import requests

import monitor
from models.constants import LOGGER, static

SESSION = requests.Session()
SESSION.headers = {"Authorization": "token " + static.GIT_TOKEN}
BASE_URL = "https://api.github.com/repos/thevickypedia/JarvisMonitor"
INDEX_URL = f"{BASE_URL}/contents/docs/index.html"
DOCS_BRANCH = "docs"
DEFAULT_BRANCH = "main"
COMMIT_MESSAGE = f"Updated as of {datetime.now().strftime('%d/%m/%Y %H:%M:%S %Z %z')}"


def head_branch() -> bool:
    """Check and create head branch if needed."""
    branch_url = f"{BASE_URL}/git/refs/heads/{DOCS_BRANCH}"
    resp = SESSION.get(branch_url)
    if resp.status_code == 404:
        base_branch = SESSION.get(f"{BASE_URL}/git/refs/heads/{DEFAULT_BRANCH}")
        base_branch_sha = base_branch.json()["object"]["sha"]
        data = {"ref": f"refs/heads/{DOCS_BRANCH}", "sha": base_branch_sha}
        resp = SESSION.post(f"{BASE_URL}/git/refs", json=data)
        if resp.ok:
            LOGGER.info("Branch %s created successfully", DOCS_BRANCH)
            return True
        else:
            LOGGER.error("Failed to create branch %s: %s", DOCS_BRANCH, resp.text)
    elif resp.status_code == 200:
        LOGGER.info("Branch %s already exists", DOCS_BRANCH)
        return True
    else:
        LOGGER.error("Failed to check branch '%s': %s", DOCS_BRANCH, resp.text)


def push_to_github():
    """Commit and push to GitHub."""
    try:
        with open(static.INDEX_FILE, "rb") as file:
            base64content = base64.b64encode(file.read())
    except FileNotFoundError as error:
        LOGGER.critical(error)
        return
    if not head_branch():
        return
    decoded_content = base64content.decode("utf-8")
    response = SESSION.get(f"{INDEX_URL}?ref={DOCS_BRANCH}")
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
        resp = SESSION.put(INDEX_URL, data=json.dumps(payload))
        if resp.ok:
            LOGGER.info(resp.json())
        else:
            LOGGER.error("%s - %s", resp.status_code, resp.json())
    else:
        LOGGER.info("Nothing to update")
    # Delete the file since there is no branch checkout happening
    os.remove(static.INDEX_FILE)


if __name__ == "__main__":
    monitor.main()
    push_to_github()
