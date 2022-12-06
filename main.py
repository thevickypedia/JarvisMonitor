import os
import string
import time
from threading import Thread
from typing import Dict, Union

import jinja2
import psutil
import yaml
from gmailconnector.send_email import SendEmail

from constants import FILE_PATH, DATETIME, LOGGER, ColorCode


def get_data() -> Union[Dict[str, int], None]:
    """Get processes mapping from Jarvis."""
    if not os.path.isfile(FILE_PATH):
        return

    with open(FILE_PATH) as file:
        data = yaml.load(stream=file, Loader=yaml.FullLoader)

    # Remove temporary processes that will stop anyway
    del data['tunneling']
    del data['speech_synthesizer']
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
    if not status:
        status = {"Jarvis": "&#128308;"}
        stat_file = "red.png"
        stat_text = "Unable to fetch the status of Jarvis"
    elif status["Jarvis"] == ColorCode.red:
        stat_file = "red.png"
        stat_text = "Main functionality has been degraded. Manual intervention required."
    elif ColorCode.red in list(status.values()):
        stat_file = "yellow.png"
        stat_text = "Some components are degraded"
    else:
        stat_text = "Jarvis is up and running"
        stat_file = "green.png"
    with open('web_template.html') as web_temp:
        template_data = web_temp.read()
    template = jinja2.Template(template_data)
    content = template.render(result=status, DATETIME=DATETIME, STATUS_FILE=stat_file, STATUS_TEXT=stat_text)
    with open(os.path.join('docs', 'index.html'), 'w') as file:
        file.write(content)


def send_email(status: dict = None):
    """Sends an email notification if Jarvis is down."""
    if os.path.isfile('last_notify'):
        with open('last_notify') as file:
            stamp = float(file.read())
        if int(time.time()) - stamp < 3_600:
            LOGGER.info("Last email was sent within an hour.")
            return
    LOGGER.info("Sending email")
    if not status:
        response = SendEmail().send_email(subject="JARVIS IS NOT RUNNING", sender="JarvisMonitor")
    else:
        with open('email_template.html') as email_temp:
            template_data = email_temp.read()
        template = jinja2.Template(template_data)
        content = template.render(result=status)
        if status["Jarvis"] == ColorCode.red:
            subject = f"Main functionality degraded - {DATETIME}"
        elif ColorCode.red in list(status.values()):
            subject = f"Some components degraded - {DATETIME}"
        else:
            subject = f"Jarvis is up and running - {DATETIME}"
        response = SendEmail().send_email(subject=subject, html_body=content, sender="JarvisMonitor")
    if response.ok:
        LOGGER.info("Status report has been sent.")
        with open('last_notify', 'w') as file:
            file.write(str(time.time()))
    else:
        LOGGER.info("CRITICAL::FAILED TO SEND STATUS REPORT!!")


def main() -> None:
    """Checks the health of all processes in the mapping and actions accordingly."""
    LOGGER.info(f"Monitoring health check at: {DATETIME}")
    status = {}
    notify = False
    data = get_data()
    if not data:
        Thread(target=send_email).start()
        publish_docs()
        return
    for func_name, pid in data.items():
        if psutil.pid_exists(pid) and is_running(pid):
            LOGGER.info(f"{func_name} [{pid}] is HEALTHY")
            func_name = func_name.replace('_', ' ').replace('-', ' ')
            status[string.capwords(func_name)] = ColorCode.green
        else:
            LOGGER.critical(f"{func_name} [{pid}] is NOT HEALTHY")
            func_name = func_name.replace('_', ' ').replace('-', ' ')
            status[string.capwords(func_name)] = ColorCode.red
            notify = True
    if notify:
        Thread(target=send_email, kwargs={"status": status}).start()
    publish_docs(status=status)


if __name__ == '__main__':
    main()
