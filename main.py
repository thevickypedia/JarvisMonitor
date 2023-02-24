import os
import string
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Thread
from typing import Dict, Union, NoReturn, Tuple, List

import jinja2
import psutil
import yaml

from models.conditions import all_pids_are_red, main_process_is_red, some_pids_are_red
from models.constants import FILE_PATH, NOTIFICATION, DATETIME, LOGGER, ColorCode, skip_schedule
from models.helper import check_cpu_util, send_email

STATUS_DICT = {}


def get_data() -> Union[Dict[str, int], None]:
    """Get processes mapping from Jarvis."""
    if os.path.isfile(FILE_PATH):
        with open(FILE_PATH) as file:
            data = yaml.load(stream=file, Loader=yaml.FullLoader) or {}
        return data


def publish_docs(status: dict = None) -> NoReturn:
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
                l_desc += f"<b>Impacted by {key.lower()}:</b><br><ul><li>{'</li><li>'.join(status[key][1])}</li></ul>"
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
            func_name = string.capwords(func_name.replace('_', ' ')).replace('api', 'API')
            STATUS_DICT[func_name] = [ColorCode.yellow, proc_impact + list(issue.items())]
        else:
            LOGGER.info(f"{func_name} [{process.pid}] is HEALTHY")
            func_name = string.capwords(func_name.replace('_', ' ')).replace('api', 'API')
            STATUS_DICT[func_name] = [ColorCode.green, proc_impact]
    else:
        LOGGER.critical(f"{func_name} [{process.pid}] is NOT HEALTHY")
        func_name = string.capwords(func_name.replace('_', ' ')).replace('api', 'API')
        STATUS_DICT[func_name] = [ColorCode.red, proc_impact]
        raise Exception  # Only to indicate, notify flag has to be flipped


def extract_proc_info(data: Dict) -> Generator[psutil.Process, List[str]]:
    """Extract process information from PID and yield the process and process impact."""
    for func_name, proc_info in data.items():
        pid, proc_impact = proc_info
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
    LOGGER.info(f"Monitoring health check at: {DATETIME}")
    if not (data := get_data()):
        publish_docs()
        return
    notify = False
    data_tup = list(extract_proc_info(data=data))
    futures = {}
    executor = ThreadPoolExecutor(max_workers=len(data_tup))
    with executor:
        for iterator in data_tup:
            future = executor.submit(classify_processes, iterator)
            futures[future] = iterator
    for future in as_completed(futures):
        if future.exception():
            LOGGER.error(f'Thread processing for {iterator!r} received an exception: {future.exception()}')
            notify = True
    if notify:
        Thread(target=send_email, kwargs={"status": STATUS_DICT}).start()
    elif os.path.isfile(NOTIFICATION):
        os.remove(NOTIFICATION)
    publish_docs(status=STATUS_DICT)


if __name__ == '__main__':
    main()
