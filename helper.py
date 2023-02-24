import psutil

from constants import LOGGER


def check_cpu_util(process: psutil.Process):
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
