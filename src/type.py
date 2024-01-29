import time
import queue, traceback

from pynput.keyboard import Controller as KeyboardController


def typing(transcriptions_queue, status_pipe, init_worker):
    init_worker()

    keyboard = KeyboardController()
    while True:
        try:
            transcription = transcriptions_queue.get_nowait()
            print('Typing: ')
            for char in transcription:
                print(char, end="")
                keyboard.press(char)
                keyboard.release(char)
                time.sleep(0.005)
        except queue.Empty:
            time.sleep(0.2)
