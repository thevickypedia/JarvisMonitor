import base64
import json
from datetime import datetime

import requests

import monitor
from models.constants import LOGGER, Constants


def push_to_github(filename: str, repo: str, branch: str, token: str, commit_message: str):
    """Commit and push to GitHub."""
    url = "https://api.github.com/repos/" + repo + "/contents/" + filename
    base64content = base64.b64encode(open(filename, "rb").read())
    data = requests.get(url + '?ref=' + branch, headers={"Authorization": "token " + token}).json()
    sha = data['sha']
    if base64content.decode('utf-8') + "\n" != data['content']:
        message = json.dumps(
            {
                "message": commit_message,
                "branch": branch,
                "content": base64content.decode("utf-8"),
                "sha": sha
            }
        )
        resp = requests.put(url, data=message,
                            headers={"Content-Type": "application/json", "Authorization": "token " + token})

        assert resp.ok, resp.text
        LOGGER.info(resp.json())
    else:
        LOGGER.info("Nothing to update")


if __name__ == '__main__':
    monitor.main()
    push_to_github("docs/index.html",
                   "thevickypedia/JarvisMonitor",
                   "docs",
                   Constants.GIT_TOKEN,
                   f"Updated as of {datetime.now().strftime('%d/%m/%Y %H:%M:%S %Z %z')}")
