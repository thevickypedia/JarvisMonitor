from models.constants import ColorCode


def all_pids_are_red(status: dict) -> bool:
    """Checks condition for all PIDs being red and returns a boolean flag."""
    return len(set(list(zip(*status.values()))[0])) == 1 and set(
        list(zip(*status.values()))[0]
    ) == {ColorCode.red}


def main_process_is_red(status: dict) -> bool:
    """Checks condition for main process being red and returns a boolean flag."""
    return status["Jarvis"][0] == ColorCode.red


def some_pids_are_red(status: dict) -> bool:
    """Checks condition for one or more sub-processes being red and returns a boolean flag."""
    return ColorCode.red in list(zip(*status.values()))[0]
