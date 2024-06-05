import base64
import json
import os
from datetime import datetime

import requests

import monitor
from models.constants import LOGGER, Constants

SESSION = requests.Session()
SESSION.headers = {"Authorization": "token " + Constants.GIT_TOKEN}
URL = "https://api.github.com/repos/thevickypedia/JarvisMonitor/contents/docs/index.html"
DOCS_BRANCH = "docs"
INDEX_FILE = os.path.join("docs", "index.html")
COMMIT_MESSAGE = f"Updated as of {datetime.now().strftime('%d/%m/%Y %H:%M:%S %Z %z')}"


def push_to_github():
    """Commit and push to GitHub."""
    with open(INDEX_FILE, "rb") as file:
        base64content = base64.b64encode(file.read())
    decoded_content = base64content.decode('utf-8')
    response = SESSION.get(f'{URL}?ref={DOCS_BRANCH}')
    assert response.ok, response.text
    response.raise_for_status()
    data = response.json()
    sha = data['sha']
    if decoded_content.strip() != data['content'].strip():
        payload = {
            "message": COMMIT_MESSAGE,
            "branch": DOCS_BRANCH,
            "content": decoded_content,
            "sha": sha
        }
        SESSION.headers["Content-Type"] = "application/json"
        resp = SESSION.put(URL, data=json.dumps(payload))
        assert resp.ok, resp.text
        LOGGER.info(resp.json())
    else:
        LOGGER.info("Nothing to update")


if __name__ == '__main__':
    monitor.main()
    push_to_github()
    # Delete the file since there is no branch checkout happening
    os.remove(INDEX_FILE)
