import os
import string
import time
from datetime import datetime
from threading import Thread
from typing import Dict, Union

import jinja2
import psutil
import yaml
from gmailconnector.send_email import SendEmail

from constants import FILE_PATH, NOTIFICATION, DATETIME, LOGGER, ColorCode, skip_schedule

impact_lib = {}
if os.path.isfile(os.path.join('docs', 'CNAME')):
    with open(os.path.join('docs', 'CNAME')) as f:
        webpage = f.read()
else:
    webpage = None


def get_data() -> Union[Dict[str, int], None]:
    """Get processes mapping from Jarvis."""
    if os.path.isfile(FILE_PATH):
        with open(FILE_PATH) as file:
            data = yaml.load(stream=file, Loader=yaml.FullLoader) or {}
        return data


def is_running(pid) -> bool:
    """Checks if the process is running."""
    try:
        return psutil.Process(pid=pid).status() == psutil.STATUS_RUNNING
    except psutil.Error as error:
        LOGGER.error(error)


def publish_docs(status: dict = None):
    """Updates the docs/index.html file."""
    LOGGER.info("Updating index.html")
    t_desc, l_desc = "", ""
    if not status:  # process map is missing
        status = {"Jarvis": ColorCode.blue}
        stat_file = "maintenance.png"
        stat_text = "Process Map Unreachable"
        t_desc = "<b>Description:</b> Source feed is missing, Jarvis has been stopped for maintenance."
    elif len(set(list(status.values()))) == 1 and set(list(status.values())) == {ColorCode.red}:  # all pids are red
        stat_file = "issue.png"
        stat_text = "Service disrupted by an external factor"
        t_desc = "<b>Description:</b> Source feed is present but all processes have been terminated abruptly."
    elif status["Jarvis"] == ColorCode.red:  # main process is red
        stat_file = "notice.png"
        stat_text = "Main functionality has been degraded"
        t_desc = "<b>Description:</b> Main process has degraded, making child processes rouge <i>yet active.</i>"
    elif ColorCode.red in list(status.values()):  # one or more subprocess is red
        stat_file = "warning.png"
        stat_text = "Some components are degraded"
        for key in status.keys():
            if status[key] == ColorCode.red:
                l_desc += f"<b>Impacted by {key.lower()}:</b><br><ul><li>{'</li><li>'.join(impact_lib[key])}</li></ul>"
    else:  # all green
        stat_text = "Jarvis is up and running"
        stat_file = "ok.png"
        if len(status) == 1:  # Limited mode
            t_desc = "<b>Description:</b> Jarvis is running in limited mode. " \
                     "All offline communicators and home automations are currently unavailable."
    with open('web_template.html') as web_temp:
        template_data = web_temp.read()
    template = jinja2.Template(template_data)
    content = template.render(result=status, DATETIME=DATETIME, STATUS_FILE=stat_file, STATUS_TEXT=stat_text,
                              TEXT_DESCRIPTION=t_desc, LIST_DESCRIPTION=l_desc)
    with open(os.path.join('docs', 'index.html'), 'w') as file:
        file.write(content)


def send_email(status: dict = None):
    """Sends an email notification if Jarvis is down."""
    if not status:
        LOGGER.warning("Jarvis is in maintenance mode.")
        return
    if len(set(list(status.values()))) == 1 and set(list(status.values())) == {ColorCode.red}:
        state = 'issue'
    elif status["Jarvis"] == ColorCode.red:
        state = 'notice'
    elif ColorCode.red in list(status.values()):
        state = 'warning'
    else:
        state = 'ok'
    if os.path.isfile(NOTIFICATION):
        with open(NOTIFICATION) as file:
            data = yaml.load(stream=file, Loader=yaml.FullLoader)
        if data.get(state) and time.time() - data[state] < 3_600:
            LOGGER.info("Last email was sent within an hour.")
            return
    try:
        email_obj = SendEmail()
    except ValueError as error:
        LOGGER.critical(error)
        return
    auth = email_obj.authenticate
    if not auth.ok:
        LOGGER.critical(auth.body)
        return
    LOGGER.info("Sending email")
    with open('email_template.html') as email_temp:
        template_data = email_temp.read()
    template = jinja2.Template(template_data)
    content = template.render(result=status, webpage=webpage)
    if len(set(list(status.values()))) == 1 and set(list(status.values())) == {ColorCode.red}:  # all pids are red
        subject = f"Service disrupted by an external force - {DATETIME}"
    elif status["Jarvis"] == ColorCode.red:  # main process is red
        subject = f"Main functionality degraded - {DATETIME}"
    elif ColorCode.red in list(status.values()):  # one or more subprocess is red
        subject = f"Some components degraded - {DATETIME}"
    else:
        # should never get here
        LOGGER.critical("`notify` flag was set to True without any components being affected.")
        return
    response = email_obj.send_email(subject=subject, html_body=content, sender="JarvisMonitor")
    if response.ok:
        LOGGER.info("Status report has been sent.")
        with open(NOTIFICATION, 'w') as file:
            yaml.dump(data={state: time.time()}, stream=file)
    else:
        LOGGER.critical("CRITICAL::FAILED TO SEND STATUS REPORT!!")


def main() -> None:
    """Checks the health of all processes in the mapping and actions accordingly."""
    if skip_schedule == datetime.now().strftime("%I:%M %p"):
        LOGGER.info(f"Schedule ignored at {skip_schedule!r}")
        return
    LOGGER.info(f"Monitoring health check at: {DATETIME}")
    status = {}
    notify = False
    data = get_data()
    if not data:
        Thread(target=send_email).start()
        publish_docs()
        return
    for func_name, proc_info in data.items():
        pid, proc_impact = proc_info
        if not isinstance(pid, int):
            LOGGER.warning(f"{func_name} [{pid}] is invalid.")
            continue
        if psutil.pid_exists(pid) and is_running(pid):
            LOGGER.info(f"{func_name} [{pid}] is HEALTHY")
            func_name = string.capwords(func_name.replace('_', ' ')).replace('api', 'API')
            status[func_name] = ColorCode.green
        else:
            LOGGER.critical(f"{func_name} [{pid}] is NOT HEALTHY")
            func_name = string.capwords(func_name.replace('_', ' ')).replace('api', 'API')
            status[func_name] = ColorCode.red
            notify = True
        impact_lib[func_name] = proc_impact
    if notify:
        Thread(target=send_email, kwargs={"status": status}).start()
    elif os.path.isfile(NOTIFICATION):
        os.remove(NOTIFICATION)
    publish_docs(status=status)


if __name__ == '__main__':
    main()
