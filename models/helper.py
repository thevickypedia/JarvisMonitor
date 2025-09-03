import os
import time
from typing import Dict

import gmailconnector
import jinja2
import psutil
import yaml

from models.conditions import all_pids_are_red, main_process_is_red, some_pids_are_red
from models.constants import LOGGER, env, static


def check_performance(process: psutil.Process) -> Dict[str, float | int] | None:
    """Checks performance by monitoring CPU utilization, number of threads and open files.

    Args:
        process: Process object.

    Returns:
        Dict[str, int]:
        Returns a dictionary of metrics and their values as key-value pair.
    """
    name = process.func  # noqa
    cpu = process.cpu_percent(interval=0.5)
    threads = process.num_threads()
    open_files = len(process.open_files())
    info_dict = {"cpu": cpu, "threads": threads, "open_files": open_files}
    LOGGER.info({f"{name} [{process.pid}]": info_dict})
    if cpu > 50 or open_files > 50:  # current threshold for Jarvis
        LOGGER.critical("%s [%d] should be optimized", name, process.pid)
        return info_dict


def send_email(status: dict = None) -> None:
    """Sends an email notification if Jarvis is down.

    Args:
        status: Translated status dictionary.
    """
    if not all((env.gmail_user, env.gmail_pass, env.recipient)):
        LOGGER.warning("Not all env vars are present for sending an email!!")
        return
    if not status:
        LOGGER.warning("Jarvis is in maintenance mode.")
        return
    if all_pids_are_red(status=status):
        state = "issue"
        subject = f"Service disrupted by an external force - {static.DATETIME}"
    elif main_process_is_red(status=status):
        state = "notice"
        subject = f"Main functionality degraded - {static.DATETIME}"
    elif some_pids_are_red(status=status):
        state = "warning"
        subject = f"Some components degraded - {static.DATETIME}"
    else:
        LOGGER.critical(
            "`notify` flag was set to True without any components being affected."
        )
        return
    if os.path.isfile(static.NOTIFICATION):
        with open(static.NOTIFICATION) as file:
            data = yaml.load(stream=file, Loader=yaml.FullLoader)
        if data.get(state) and time.time() - data[state] < 43_200:
            LOGGER.info("Last email was sent within an hour.")
            return
    try:
        email_obj = gmailconnector.SendEmail(
            gmail_user=env.gmail_user, gmail_pass=env.gmail_pass
        )
    except ValueError as error:
        LOGGER.critical(error)
        return
    auth = email_obj.authenticate
    if not auth.ok:
        LOGGER.critical(auth.body)
        return
    LOGGER.info("Sending email")
    with open(static.EMAIL_TEMPLATE) as email_temp:
        template_data = email_temp.read()
    template = jinja2.Template(template_data)
    content = template.render(result=status, webpage=static.webpage)
    response = email_obj.send_email(
        subject=subject,
        html_body=content,
        sender="JarvisMonitor",
        recipient=env.recipient,
    )
    if response.ok:
        LOGGER.info("Status report has been sent.")
        with open(static.NOTIFICATION, "w") as file:
            yaml.dump(data={state: time.time()}, stream=file)
            file.flush()
    else:
        LOGGER.critical("CRITICAL::FAILED TO SEND STATUS REPORT!!")
