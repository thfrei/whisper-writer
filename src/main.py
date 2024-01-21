import json
import os
import sys
import queue
import threading
import time
import keyboard
from pynput.keyboard import Controller
from transcription import create_local_model, record_and_transcribe_batch
from status_window import StatusWindow

from pynput import keyboard


recording_thread = None
recording_state = 'idle'  # Possible states: 'idle', 'recording', 'finishing'
batching_thread = None
batching_state = 'idle'  # Possible states: 'idle', 'batching', 'finishing'
pyinput_keyboard = None

class ResultThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(ResultThread, self).__init__(*args, **kwargs)
        self.result = None
        self.stop_transcription = False

    def run(self):
        self.result = self._target(*self._args, cancel_flag=lambda: self.stop_transcription, **self._kwargs)

    def stop(self):
        global recording_state
        recording_state = 'finishing'
        self.stop_transcription = True

def clear_status_queue():
    while not status_queue.empty():
        try:
            status_queue.get_nowait()
        except queue.Empty:
            break

def start_recording_batching():
    # global batching_thread, batching_state
    # batching_state = 'batching'
    # clear_status_queue()
    # status_queue.put(('batching', 'Batching: Recording->Transcribing--Recording...'))
    # batching_thread = threading.Thread(target=record_and_transcribe_batch, 
    #                                 args=(status_queue,),
    #                                 kwargs={'config': config,
    #                                         'local_model': local_model if local_model and not config['use_api'] else None,
    #                                         },)
    # status_window = StatusWindow(status_queue)
    # status_window.recording_thread = recording_thread
    # status_window.start()
    # batching_thread.start()
    record_and_transcribe_batch()

def on_shortcut_batching():
    global batching_thread, batching_state

    if batching_state == 'idle':
        print('Shortcut pressed. Starting batchmode recording.')
        start_recording_batching()
    elif batching_state == 'batching':
        print('Shortcut pressed. Finishing batching.')
        # batching_thread.stop()
    else:
        print('Shortcut pressed, ignoring - recording is already finishing.')

def format_keystrokes(key_string):
    return '+'.join(word.capitalize() for word in key_string.split('+'))

def typewrite(text, interval):
    print(f'{text}')
    keyboard = Controller()

    for letter in text:
        keyboard.press(letter)
        keyboard.release(letter)
        time.sleep(interval)

status_queue = queue.Queue()

# Define the activation key combination
COMBINATION = {keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.Key.space}

# The currently active modifiers
current_keys = set()

def on_press(key):
    if key in COMBINATION:
        current_keys.add(key)
        if all(k in current_keys for k in COMBINATION):
            # All required keys are currently pressed, so trigger the shortcut function
            on_shortcut_batching()

def on_release(key):
    try:
        current_keys.remove(key)
    except KeyError:
        pass  # Key was not in the set of pressed keys, ignore


# just start for debug
print('starting')
start_recording_batching()
    

print(f'Press to start recording and transcribing. Press Ctrl+C on the terminal window to quit.')
try:
    # keyboard.wait()  # Keep the script running to listen for the shortcut
    # Set up the listener
    with keyboard.Listener(
            on_press=on_press,
            on_release=on_release) as listener: 
        listener.join()
except KeyboardInterrupt:
    print('\nExiting the script...')
    os.system('exit')
