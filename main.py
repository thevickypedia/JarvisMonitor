import os
import string
import time

import jinja2
import psutil
import yaml
from gmailconnector.send_email import SendEmail
from threading import Thread
from typing import Dict, Union

from constants import FILE_PATH, DATETIME, LOGGER, ColorCode


def get_data() -> Union[Dict[str, int], None]:
    """Get processes mapping from Jarvis."""
    if not os.path.isfile(FILE_PATH):
        return

    with open(FILE_PATH) as file:
        data = yaml.load(stream=file, Loader=yaml.FullLoader)

    # Remove temporary processes that will stop anyway
    del data['initiate_tunneling']
    del data['synthesizer']
    return data


def is_running(pid) -> bool:
    """Checks if the process is running."""
    try:
        return psutil.Process(pid=pid).status() == psutil.STATUS_RUNNING
    except psutil.Error as error:
        LOGGER.error(error)


def publish_docs(status: dict = None) -> str:
    """Updates the docs/index.html file and returns the html content to send via email."""
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
    with open('template.html') as temp:
        template_data = temp.read()
    template = jinja2.Template(template_data)
    content = template.render(result=status, DATETIME=DATETIME, STATUS_FILE=stat_file, STATUS_TEXT=stat_text)
    with open(os.path.join('docs', 'index.html'), 'w') as file:
        file.write(content)
    return content


def send_email(content: str, status: dict = None):
    """Sends an email notification if Jarvis is down."""
    if status:
        response = SendEmail().send_email(subject=f"Status report for Jarvis - {DATETIME}",
                                          html_body=content, sender="JarvisMonitor")
    else:
        response = SendEmail().send_email(subject="JARVIS IS NOT RUNNING", sender="JarvisMonitor")
    if response.ok:
        LOGGER.info("Status report has been sent.")
    else:
        LOGGER.info("CRITICAL::FAILED TO SEND STATUS REPORT!!")
    with open('last_notify', 'w') as file:
        file.write(str(time.time()))


def main() -> None:
    """Checks the health of all processes in the mapping and actions accordingly."""
    LOGGER.info(f"Monitoring health check at: {DATETIME}")
    status = {}
    notify = False
    data = get_data()
    if not data:
        content = publish_docs()
        Thread(target=send_email, kwargs={"content": content, "status": None}, daemon=True).start()
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
    content = publish_docs(status=status)
    if notify:
        if os.path.isfile('last_notify'):
            with open('last_notify') as file:
                stamp = float(file.read())
            if int(time.time()) - stamp < 3_600:
                LOGGER.info("Last email was sent within an hour.")
                return
        Thread(target=send_email, kwargs={"status": status, "content": content}, daemon=True).start()


if __name__ == '__main__':
    main()
