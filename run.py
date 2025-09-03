import base64
import json
import os
from datetime import datetime
from typing import Tuple

import git
import requests

import monitor
from models.constants import LOGGER, REPOSITORY, env, static


def get_index_file() -> bytes | None:
    """Reads the index file and returns the data as bytes."""
    try:
        with open(static.INDEX_FILE, "rb") as file:
            return base64.b64encode(file.read())
    except FileNotFoundError as error:
        LOGGER.critical(error)


class GitHub:
    """GitHub's operations including GitPython and GH API.

    >>> GitHub

    """

    def __init__(self):
        """Instantiates a session with GitHub API and authenticates GitPython."""
        self.session = requests.Session()
        self.session.headers = {
            "Authorization": "token " + env.git_token,
            "Content-Type": "application/json",
        }
        self.repository = git.Repo(REPOSITORY)
        self.origin = self.repository.remote(name="origin")
        self.origin.config_writer.set(
            "url",
            f"https://{env.git_user}:{env.git_token}@github.com/{env.git_owner}/{REPOSITORY.name}.git",
        )
        self.origin.config_writer.release()

    def head_branch(self) -> None:
        """Check and create docs branch if not available."""
        self.repository.remotes.origin.fetch(prune=True)
        remote_branches = [ref.name for ref in self.repository.remote("origin").refs]
        if f"origin/{static.DOCS_BRANCH}" in remote_branches:
            LOGGER.debug("Branch '%s' already exists remotely.", static.DOCS_BRANCH)
            return
        if static.DOCS_BRANCH in self.repository.heads:
            LOGGER.info(
                "Branch '%s' exists locally, but not on remote. Deleting local branch.",
                static.DOCS_BRANCH,
            )
            self.repository.delete_head(static.DOCS_BRANCH, force=True)
        base_branch = self.repository.heads[self.repository.active_branch.name]
        new_branch = self.repository.create_head(
            static.DOCS_BRANCH, base_branch.commit.hexsha
        )
        self.origin.push(new_branch.name)
        LOGGER.info("Branch '%s' created and pushed to remote.", static.DOCS_BRANCH)

    def git_push(self, sha: str, content: str) -> requests.Response:
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
        return self.session.put(static.INDEX_URL, data=json.dumps(payload))

    def get_origin_file(self) -> Tuple[bytes, str]:
        """Gets the commit object for the remote branch, and retrieves the file content from commit tree.

        Returns:
            Tuple[bytes, str]:
            Returns a tuple of file content as bytes, and the commit SHA.
        """
        commit = self.repository.commit(f"origin/{static.DOCS_BRANCH}")
        # The / operator is overloaded in GitPython to allow easy traversal of the tree structure
        # The / expression navigates through the tree to find the file located at docs/index.html
        target_file = commit.tree / "docs/index.html"
        file_content = target_file.data_stream.read()
        file_sha = target_file.hexsha
        return base64.b64encode(file_content), file_sha

    def push_to_github(self):
        """Commit and push to GitHub."""
        if local_content := get_index_file():
            self.head_branch()
        else:
            return
        try:
            remote_content, sha = self.get_origin_file()
            # push only when there are changes
            if env.check_existing:
                push = local_content != remote_content
            else:
                push = True
                if datetime.now().minute not in env.override_check:
                    LOGGER.warning(
                        "Check existing is set to False, this will push to origin regardless of changes!"
                    )
        except KeyError as error:
            # File is missing in docs branch, perhaps newly created head branch
            LOGGER.warning(error)
            LOGGER.warning("Creating a new file in %s branch", static.DOCS_BRANCH)
            sha = None
            push = True
        except git.BadName as warning:
            LOGGER.critical(warning)
            LOGGER.critical(
                "Branch '%s' doesn't exist, but it should have been covered by '%s'",
                static.DOCS_BRANCH,
                self.head_branch.__name__,
            )
            push = True
            sha = None
        if push:
            push_response = self.git_push(sha, local_content.decode("utf-8"))
            json_response = push_response.json()
            if push_response.ok:
                LOGGER.info("Updated %s branch with changes", static.DOCS_BRANCH)
                LOGGER.debug(push_response.json())
            else:
                LOGGER.critical("%s - %s", push_response.status_code, json_response)
        else:
            LOGGER.info("Nothing to push")
        # Delete the file since there is no branch checkout happening
        os.remove(static.INDEX_FILE)


def entrypoint():
    """Entrypoint for the monitor."""
    if env.skip_schedule == datetime.now().strftime(static.SKIPPER_FORMAT):
        LOGGER.info("Schedule ignored at '%s'", env.skip_schedule)
    else:
        monitor.main()
        github = GitHub()
        github.push_to_github()


if __name__ == "__main__":
    entrypoint()
