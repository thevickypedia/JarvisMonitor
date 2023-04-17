import os
import time
from typing import Dict

import gmailconnector
import jinja2
import psutil
import yaml

from models.conditions import all_pids_are_red, some_pids_are_red, main_process_is_red
from models.constants import NOTIFICATION, DATETIME, LOGGER, webpage


def check_cpu_util(process: psutil.Process) -> Dict:
    """Check CPU utilization, number of threads and open files."""
    name = process.func  # noqa
    cpu = process.cpu_percent(interval=3)
    threads = process.num_threads()
    open_files = len(process.open_files())
    info_dict = {'cpu': cpu, 'threads': threads, 'open_files': open_files}
    LOGGER.info({f"{name} [{process.pid}]": info_dict})
    if cpu > 10 or threads > 25 or open_files > 50:
        LOGGER.critical(f"{name} [{process.pid}] should be optimized")
        # with db.connection:
        #     cursor = db.connection.cursor()
        #     cursor.execute("INSERT or REPLACE INTO restart (flag, caller) VALUES (?,?);", (True, name))
        #     cursor.connection.commit()
        return info_dict


def send_email(status: dict = None) -> None:
    """Sends an email notification if Jarvis is down."""
    if not status:
        LOGGER.warning("Jarvis is in maintenance mode.")
        return
    if all_pids_are_red(status=status):
        state = 'issue'
        subject = f"Service disrupted by an external force - {DATETIME}"
    elif main_process_is_red(status=status):
        state = 'notice'
        subject = f"Main functionality degraded - {DATETIME}"
    elif some_pids_are_red(status=status):
        state = 'warning'
        subject = f"Some components degraded - {DATETIME}"
    else:
        LOGGER.critical("`notify` flag was set to True without any components being affected.")
        return
    if os.path.isfile(NOTIFICATION):
        with open(NOTIFICATION) as file:
            data = yaml.load(stream=file, Loader=yaml.FullLoader)
        if data.get(state) and time.time() - data[state] < 3_600:
            LOGGER.info("Last email was sent within an hour.")
            return
    try:
        email_obj = gmailconnector.SendEmail()
    except ValueError as error:
        LOGGER.critical(error)
        return
    auth = email_obj.authenticate
    if not auth.ok:
        LOGGER.critical(auth.body)
        return
    LOGGER.info("Sending email")
    with open(os.path.join('templates', 'email_template.html')) as email_temp:
        template_data = email_temp.read()
    template = jinja2.Template(template_data)
    content = template.render(result=status, webpage=webpage)
    response = email_obj.send_email(subject=subject, html_body=content, sender="JarvisMonitor")
    if response.ok:
        LOGGER.info("Status report has been sent.")
        with open(NOTIFICATION, 'w') as file:
            yaml.dump(data={state: time.time()}, stream=file)
    else:
        LOGGER.critical("CRITICAL::FAILED TO SEND STATUS REPORT!!")
