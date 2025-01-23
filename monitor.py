import os
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Thread
from typing import Dict, List

import jinja2
import psutil
import yaml

from models.conditions import all_pids_are_red, main_process_is_red, some_pids_are_red
from models.constants import LOGGER, color_codes, env, static
from models.helper import check_performance, send_email

STATUS_DICT = {}


def get_data() -> Dict[str, Dict[int, List[str]]]:
    """Get processes mapping from Jarvis."""
    try:
        with open(env.source_map) as file:
            return yaml.load(stream=file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        LOGGER.warning("Feed file is missing, assuming maintenance mode.")


def publish_docs(status: dict = None) -> None:
    """Updates the docs/index.html file.

    Args:
        status: Translated status dictionary.
    """
    LOGGER.info("Updating index.html")
    t_desc, l_desc = "", ""
    if not status:  # process map is missing
        status = {"Jarvis": [color_codes.blue, ["Maintenance"]]}
        stat_file = "maintenance.png"
        stat_text = "Process Map Unreachable"
        t_desc = "<b>Description:</b> Source feed is missing, Jarvis has been stopped for maintenance."
    elif all_pids_are_red(status=status):
        stat_file = "issue.png"
        stat_text = "Service disrupted by an external factor"
        t_desc = "<b>Description:</b> Source feed is present but all processes have been terminated abruptly."
    elif main_process_is_red(status=status):
        stat_file = "notice.png"
        stat_text = "Main functionality has been degraded"
        t_desc = "<b>Description:</b> Main process has degraded, making child processes rouge <i>yet active.</i>"
    elif some_pids_are_red(status=status):
        stat_file = "warning.png"
        stat_text = "Some components are degraded"
        for key in status.keys():
            if status[key][0] == color_codes.red:
                l_desc += (
                    f"<b>Impacted by {key.lower()}:</b><br>"
                    f"<br>&nbsp;&nbsp;&nbsp;&nbsp;{status[key][1][0]}"
                    f"<ul><li>{'</li><li>'.join(status[key][1][1:])}</li></ul>"
                )
    else:  # all green
        stat_text = "Jarvis is up and running"
        stat_file = "ok.png"
        if len(status) == 1:  # Limited mode
            t_desc = (
                "<b>Description:</b> Jarvis is running in limited mode. "
                "All offline communicators and home automations are currently unavailable."
            )
    with open(static.WEB_TEMPLATE) as web_temp:
        template_data = web_temp.read()
    template = jinja2.Template(template_data)
    content = template.render(
        result=status,
        STATUS_FILE=stat_file,
        STATUS_TEXT=stat_text,
        TEXT_DESCRIPTION=t_desc,
        LIST_DESCRIPTION=l_desc,
        TIMEZONE=static.TIMEZONE,
    )
    with open(static.INDEX_FILE, "w") as file:
        file.write(content)
        file.flush()


def classify_processes(process: psutil.Process, proc_impact: List[str]) -> None:
    """Classify all processes into good (green - all ok), bad (yellow - degraded performance) and evil (red - bad PID).

    Args:
        process: Process object.
        proc_impact: Impact because of the process.

    Raises:
        Exception:
        Raises a bare exception to notify the worker, that the thread has failed.
    """
    func_name = process.func  # noqa
    if psutil.pid_exists(process.pid) and process.status() == psutil.STATUS_RUNNING:
        if issue := check_performance(process=process):
            LOGGER.info("%s [%d] is INTENSE", func_name, process.pid)
            # combine list of string with list of tuples
            proc_impact.append(
                "\n\n" + ", ".join(f"{key}: {value}" for key, value in issue.items())
            )
            STATUS_DICT[func_name] = [color_codes.yellow, proc_impact]
        else:
            LOGGER.info("%s [%d] is HEALTHY", func_name, process.pid)
            STATUS_DICT[func_name] = [color_codes.green, proc_impact]
    else:
        LOGGER.critical("%s [%d] is NOT HEALTHY", func_name, process.pid)
        STATUS_DICT[func_name] = [color_codes.red, proc_impact]
        raise Exception  # Only to indicate, notify flag has to be flipped


def extract_proc_info(func_name: str, proc_info: Dict[int, List[str]]):
    """Validates the process ID and calls the classifier function.

    Args:
        func_name: Function name.
        proc_info: Process information as a dictionary.

    Raises:
        Exception:
        Raises a bare exception to notify the worker, that the thread has failed.
    """
    for pid, impact in proc_info.items():
        try:
            process = psutil.Process(pid=pid)
        except psutil.Error as error:
            LOGGER.error(error)
            LOGGER.warning("%s [%d] is invalid.", func_name, pid)
            raise Exception  # Only to indicate, notify flag
        else:
            process.func = func_name
        classify_processes(process, sorted(impact, key=len))


def main() -> None:
    """Checks the health of all processes in the mapping and actions accordingly."""
    if datetime.now().minute in env.override_check:
        env.check_existing = False
    LOGGER.info("Monitoring processes health at: %s", static.DATETIME)
    if not (data := get_data()):
        publish_docs()
        return
    notify = False
    futures = {}
    with ThreadPoolExecutor(max_workers=len(data)) as executor:
        for key, value in data.items():
            future = executor.submit(
                extract_proc_info, **dict(func_name=key, proc_info=value)
            )
            futures[future] = key
    for future in as_completed(futures):
        if future.exception():
            LOGGER.error(
                "Thread processing for '%s' received an exception: %s",
                futures[future],
                future.exception(),
            )
            notify = True
    data_keys = sorted(data.keys())
    stat_keys = sorted(STATUS_DICT.keys())
    if data_keys != stat_keys:
        missing_key = set(data_keys).difference(stat_keys)
        for key in missing_key:
            for pid, impact in data[key].items():
                STATUS_DICT[key] = [color_codes.red, ["INVALID PROCESS ID\n"] + impact]
                notify = True
    translate = {
        string.capwords(str(k).replace("_", " ")).replace("Api", "API"): STATUS_DICT[k]
        for k in sorted(STATUS_DICT, key=len)
    }
    if notify:
        Thread(target=send_email, kwargs={"status": translate}).start()
    elif os.path.isfile(static.NOTIFICATION):
        os.remove(static.NOTIFICATION)
    publish_docs(status=translate)
