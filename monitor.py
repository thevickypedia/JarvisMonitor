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
from models.helper import check_cpu_util, send_email

STATUS_DICT = {}


def get_data() -> Dict[str, Dict[int, List[str]]]:
    """Get processes mapping from Jarvis."""
    try:
        with open(env.source_map) as file:
            return yaml.load(stream=file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        LOGGER.warning("Feed file is missing, assuming maintenance mode.")


def publish_docs(status: dict = None) -> None:
    """Updates the docs/index.html file."""
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
    with open(os.path.join("templates", "web_template.html")) as web_temp:
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


def classify_processes(process: psutil.Process, proc_impact: List[str]):
    """Classify all processes into good, bad and evil."""
    func_name = process.func  # noqa
    if psutil.pid_exists(process.pid) and process.status() == psutil.STATUS_RUNNING:
        if issue := check_cpu_util(process=process):
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
    """Extract process information from PID and classify the process to update status dictionary."""
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
    if env.skip_schedule == datetime.now().strftime("%I:%M %p"):
        LOGGER.info("Schedule ignored at '%s'", env.skip_schedule)
        return
    # Enforce check_existing flag to False every 1 hour
    if datetime.now().minute == 0:
        env.check_existing = False
    LOGGER.info("Monitoring processes health at: %s", static.DATETIME)
    if not (data := get_data()):
        publish_docs()
        return
    notify = False
    futures = {}
    with ThreadPoolExecutor(max_workers=len(data) * 2) as executor:
        for key, value in data.items():
            future = executor.submit(
                extract_proc_info, **dict(func_name=key, proc_info=value)
            )
            futures[future] = key
    for future in as_completed(futures):
        if future.exception():
            LOGGER.error(
                f"Thread processing for {futures[future]!r} received an exception: {future.exception()}"
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
