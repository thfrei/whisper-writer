import time

from pynput.keyboard import Controller as KeyboardController
import queue, traceback


def typing(transcriptions_queue, status_pipe):
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
