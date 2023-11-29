import os
import string
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Thread
from typing import Dict, Tuple, List

import jinja2
import psutil
import yaml

from models.conditions import all_pids_are_red, main_process_is_red, some_pids_are_red
from models.constants import FILE_PATH, NOTIFICATION, DATETIME, LOGGER, ColorCode, skip_schedule
from models.helper import check_cpu_util, send_email

STATUS_DICT = {}


def get_data() -> Dict[str, Dict[int, List[str]]]:
    """Get processes mapping from Jarvis."""
    try:
        with open(FILE_PATH) as file:
            return yaml.load(stream=file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        pass


def publish_docs(status: dict = None) -> None:
    """Updates the docs/index.html file."""
    LOGGER.info("Updating index.html")
    t_desc, l_desc = "", ""
    if not status:  # process map is missing
        status = {"Jarvis": [ColorCode.blue, ["Maintenance"]]}
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
            if status[key][0] == ColorCode.red:
                l_desc += f"<b>Impacted by {key.lower()}:</b><br>" \
                          f"<br>&nbsp;&nbsp;&nbsp;&nbsp;{status[key][1][0]}" \
                          f"<ul><li>{'</li><li>'.join(status[key][1][1:])}</li></ul>"
    else:  # all green
        stat_text = "Jarvis is up and running"
        stat_file = "ok.png"
        if len(status) == 1:  # Limited mode
            t_desc = "<b>Description:</b> Jarvis is running in limited mode. " \
                     "All offline communicators and home automations are currently unavailable."
    with open(os.path.join('templates', 'web_template.html')) as web_temp:
        template_data = web_temp.read()
    template = jinja2.Template(template_data)
    content = template.render(result=status, DATETIME=DATETIME, STATUS_FILE=stat_file, STATUS_TEXT=stat_text,
                              TEXT_DESCRIPTION=t_desc, LIST_DESCRIPTION=l_desc)
    with open(os.path.join('docs', 'index.html'), 'w') as file:
        file.write(content)


def classify_processes(data_tuple: Tuple[psutil.Process, List[str]]):
    """Classify all processes into good, bad and evil."""
    process, proc_impact = data_tuple
    func_name = process.func  # noqa
    if psutil.pid_exists(process.pid) and process.status() == psutil.STATUS_RUNNING:
        if issue := check_cpu_util(process=process):
            LOGGER.warning(f"{func_name} [{process.pid}] is INTENSE")
            # combine list of string with list of tuples
            proc_impact.append('\n\n' + ', '.join(f"{key}: {value}" for key, value in issue.items()))
            STATUS_DICT[func_name] = [ColorCode.yellow, proc_impact]
        else:
            LOGGER.info(f"{func_name} [{process.pid}] is HEALTHY")
            STATUS_DICT[func_name] = [ColorCode.green, proc_impact]
    else:
        LOGGER.critical(f"{func_name} [{process.pid}] is NOT HEALTHY")
        STATUS_DICT[func_name] = [ColorCode.red, proc_impact]
        raise Exception  # Only to indicate, notify flag has to be flipped


def extract_proc_info(data: Dict) -> Generator[Tuple[psutil.Process, List[str]]]:
    """Extract process information from PID and yield the process and process impact."""
    for func_name, proc_info in data.items():
        for pid, proc_impact in proc_info.items():
            try:
                process = psutil.Process(pid=pid)
            except psutil.Error as error:
                LOGGER.error(error)
                LOGGER.warning(f"{func_name} [{pid}] is invalid.")
                continue
            else:
                process.func = func_name
            yield process, proc_impact


def main() -> None:
    """Checks the health of all processes in the mapping and actions accordingly."""
    if skip_schedule == datetime.now().strftime("%I:%M %p"):
        LOGGER.info(f"Schedule ignored at {skip_schedule!r}")
        return
    LOGGER.info(f"Monitoring processes health at: {DATETIME}")
    if not (data := get_data()):
        publish_docs()
        return
    notify = False
    futures = {}
    with ThreadPoolExecutor(max_workers=len(data)) as executor:
        for iterator in extract_proc_info(data):
            future = executor.submit(classify_processes, iterator)
            futures[future] = iterator
    for future in as_completed(futures):
        if future.exception():
            LOGGER.error(f'Thread processing for {iterator!r} received an exception: {future.exception()}')
            notify = True
    data_keys = sorted(data.keys())
    stat_keys = sorted(STATUS_DICT.keys())
    if data_keys != stat_keys:
        missing_key = set(data_keys).difference(stat_keys)
        for key in missing_key:
            for pid, impact in data[key].items():
                STATUS_DICT[key] = [ColorCode.red, ["INVALID PROCESS ID\n"] + impact]
                notify = True
    translate = {string.capwords(k.replace('_', ' ')).replace('api', 'API'): v for k, v in STATUS_DICT.items()}
    if notify:
        Thread(target=send_email, kwargs={"status": translate}).start()
    elif os.path.isfile(NOTIFICATION):
        os.remove(NOTIFICATION)
    publish_docs(status=translate)


if __name__ == '__main__':
    main()
