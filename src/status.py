import time
import queue, traceback
from status_window import StatusWindow

def status(status_queue, init_worker):
    init_worker()

    while True:
        try:
            status_window = StatusWindow(status_queue)
            status_window.start()
        except queue.Empty:
            time.sleep(0.2)
