import base64
import json
import os

import requests

import monitor
from models.constants import LOGGER, env, static

SESSION = requests.Session()
SESSION.headers = {"Authorization": "token " + env.git_token}


def head_branch() -> bool:
    """Check and create head branch if needed."""
    branch_url = f"{static.BASE_URL}/git/refs/heads/{static.DOCS_BRANCH}"
    resp = SESSION.get(branch_url)
    LOGGER.debug(resp.json())
    if resp.status_code == 404:
        base_branch = SESSION.get(
            f"{static.BASE_URL}/git/refs/heads/{static.DEFAULT_BRANCH}"
        )
        base_branch_sha = base_branch.json()["object"]["sha"]
        data = {"ref": f"refs/heads/{static.DOCS_BRANCH}", "sha": base_branch_sha}
        resp = SESSION.post(f"{static.BASE_URL}/git/refs", json=data)
        if resp.ok:
            LOGGER.info("Branch '%s' created successfully", static.DOCS_BRANCH)
            LOGGER.debug(resp.json())
            return True
        else:
            LOGGER.critical(
                "Failed to create branch '%s': %s", static.DOCS_BRANCH, resp.text
            )
            LOGGER.critical(resp.json())
    elif resp.status_code == 200:
        LOGGER.info("Branch '%s' already exists", static.DOCS_BRANCH)
        return True
    else:
        LOGGER.critical(
            "Failed to check branch '%s': %s", static.DOCS_BRANCH, resp.text
        )
        LOGGER.critical(resp.json())


def git_push(sha: str, content: str) -> requests.Response:
    """Performs git push and returns the response object."""
    LOGGER.info("Pushing changes to GitHub")
    payload = {
        "message": static.COMMIT_MESSAGE,
        "branch": static.DOCS_BRANCH,
        "content": content,
    }
    if sha:
        payload["sha"] = sha
    SESSION.headers["Content-Type"] = "application/json"
    return SESSION.put(static.INDEX_URL, data=json.dumps(payload))


def push_to_github():
    """Commit and push to GitHub."""
    try:
        with open(static.INDEX_FILE, "rb") as file:
            base64content = base64.b64encode(file.read())
    except FileNotFoundError as error:
        LOGGER.critical(error)
        return
    decoded_content = base64content.decode("utf-8")
    # todo: check if there is an alternate to this
    #   instead of checking the index file everytime, can it be cached locally?
    response = SESSION.get(f"{static.INDEX_URL}?ref={static.DOCS_BRANCH}")
    data = response.json()
    if response.ok:
        LOGGER.info("Fetch successful!")
        sha = data["sha"]
        push = decoded_content.strip() != data["content"].replace("\n", "").strip()
    else:
        LOGGER.info("Creating a new file in %s branch", static.DOCS_BRANCH)
        sha = None
        push = True
    if push:
        push_response = git_push(sha, decoded_content)
        json_response = push_response.json()
        if push_response.ok:
            LOGGER.info("Updated %s branch with changes", static.DOCS_BRANCH)
            LOGGER.debug(push_response.json())
        elif (
            push_response.status_code == 404
            and json_response["message"].lower()
            == f"branch {static.DOCS_BRANCH} not found"
        ):
            if head_branch():
                retry_response = git_push(sha, decoded_content)
                if retry_response.ok:
                    LOGGER.info("Updated %s branch with changes", static.DOCS_BRANCH)
                    LOGGER.debug(push_response.json())
                else:
                    LOGGER.critical("%s - %s", push_response.status_code, json_response)
        else:
            LOGGER.critical("%s - %s", push_response.status_code, json_response)
    else:
        LOGGER.info("Nothing to update")
    # Delete the file since there is no branch checkout happening
    os.remove(static.INDEX_FILE)


if __name__ == "__main__":
    monitor.main()
    push_to_github()
