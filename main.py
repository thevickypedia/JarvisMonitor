import os
import string
import time

import jinja2
import psutil
import yaml
from gmailconnector.send_email import SendEmail
from threading import Thread

from constants import FILE_PATH, DATETIME, LOGGER


def get_data():
    if not os.path.isfile(FILE_PATH):
        return

    with open(FILE_PATH) as file:
        data = yaml.load(stream=file, Loader=yaml.FullLoader)

    # Remove temporary processes that will stop anyway
    del data['initiate_tunneling']
    del data['synthesizer']
    return data


def is_running(pid):
    try:
        return psutil.Process(pid=pid).status() == psutil.STATUS_RUNNING
    except psutil.Error as error:
        LOGGER.error(error)


def publish_docs(status: dict = None):
    # Defaults to working condition
    if status:
        with open('template.html') as temp:
            template_data = temp.read()
        template = jinja2.Template(template_data)
        content = template.render(result=status, DATETIME=DATETIME, STATUS_FILE="green.png",
                                  STATUS_TEXT="Jarvis is up and running")
        with open(os.path.join('docs', 'index.html'), 'w') as file:
            file.write(content)
        return content


def send_email(content, status: dict = None):
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


def main():
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
            status[string.capwords(func_name)] = "&#128994;"  # large green circle
        else:
            LOGGER.critical(f"{func_name} [{pid}] is NOT HEALTHY")
            func_name = func_name.replace('_', ' ').replace('-', ' ')
            status[string.capwords(func_name)] = "&#128308;"  # large red circle
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
