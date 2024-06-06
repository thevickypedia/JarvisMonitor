import base64
import json
import os
import pathlib
from typing import Tuple

import git
import requests

import monitor
from models.constants import LOGGER, env, static

SESSION = requests.Session()
SESSION.headers = {"Authorization": "token " + env.git_token}
repo = pathlib.Path(os.getcwd())
REPOSITORY = git.Repo(repo)
REMOTE_URL_WITH_PAT = (
    f"https://{env.git_user}:{env.git_token}@github.com/{env.git_owner}/{repo.name}.git"
)
origin = REPOSITORY.remote("origin")
origin.config_writer.set("url", REMOTE_URL_WITH_PAT)
origin.config_writer.release()


def head_branch() -> None:
    """Check and create docs branch if not available."""
    REPOSITORY.remotes.origin.fetch(prune=True)
    remote_branches = [ref.name for ref in REPOSITORY.remote("origin").refs]
    if f"origin/{static.DOCS_BRANCH}" in remote_branches:
        LOGGER.info(f"Branch '{static.DOCS_BRANCH}' already exists remotely.")
        return
    if static.DOCS_BRANCH in REPOSITORY.heads:
        LOGGER.info(
            f"Local branch '{static.DOCS_BRANCH}' exists but not on remote. Deleting local branch."
        )
        REPOSITORY.delete_head(static.DOCS_BRANCH, force=True)
    base_branch = REPOSITORY.heads[REPOSITORY.active_branch.name]
    new_branch = REPOSITORY.create_head(static.DOCS_BRANCH, base_branch.commit.hexsha)
    origin = REPOSITORY.remote(name="origin")
    origin.push(new_branch.name)
    LOGGER.info(f"Branch '{static.DOCS_BRANCH}' created and pushed to remote.")


def git_push(sha: str, content: str) -> requests.Response:
    """Performs git push and returns the response object.

    Notes:
        GH API is used to perform git push, since there is no way to push changes to a branch without checking out.
    """
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


def get_origin_file() -> Tuple[bytes, str]:
    """Gets the commit object for the remote branch, and retrieves the file content from commit tree.

    Returns:
        Tuple[bytes, str]:
        Returns a tuple of file content as bytes, and the commit SHA.
    """
    commit = REPOSITORY.commit(f"origin/{static.DOCS_BRANCH}")
    # The / operator is overloaded in GitPython to allow easy traversal of the tree structure
    # The / expression navigates through the tree to find the file located at docs/index.html
    target_file = commit.tree / "docs/index.html"
    file_content = target_file.data_stream.read()
    file_sha = target_file.hexsha
    return base64.b64encode(file_content), file_sha


def push_to_github():
    """Commit and push to GitHub."""
    try:
        with open(static.INDEX_FILE, "rb") as file:
            base64content = base64.b64encode(file.read())
    except FileNotFoundError as error:
        LOGGER.critical(error)
        return
    head_branch()
    local_content = base64content.decode("utf-8")
    try:
        remote_content, sha = get_origin_file()
        LOGGER.info("Fetch successful!")
        # push only when there are changes
        if env.check_existing:
            push = local_content.strip() != remote_content.strip()
        else:
            LOGGER.warning(
                "Check existing is set to False, this will push to origin regardless of changes!"
            )
            push = True
    except KeyError as error:
        LOGGER.warning(error)  # file is missing in docs branch
        LOGGER.warning("Creating a new file in %s branch", static.DOCS_BRANCH)
        sha = None
        push = True
    except git.BadName as warning:
        LOGGER.critical(warning)
        LOGGER.critical(
            "Branch doesn't exist, but it should have been covered by 'head_branch'"
        )
        push = True
        sha = None
    if push:
        push_response = git_push(sha, local_content)
        json_response = push_response.json()
        if push_response.ok:
            LOGGER.info("Updated %s branch with changes", static.DOCS_BRANCH)
            LOGGER.debug(push_response.json())
        else:
            LOGGER.critical("%s - %s", push_response.status_code, json_response)
    else:
        LOGGER.info("Nothing to update")
    # Delete the file since there is no branch checkout happening
    os.remove(static.INDEX_FILE)


if __name__ == "__main__":
    monitor.main()
    push_to_github()
