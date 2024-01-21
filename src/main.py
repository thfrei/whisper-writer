import os
import queue
import time
import keyboard
from pynput.keyboard import Controller
from transcription import record_and_transcribe_batch
from status_window import StatusWindow

from pynput import keyboard

batching_state = 'idle'

def clear_status_queue():
    while not status_queue.empty():
        try:
            status_queue.get_nowait()
        except queue.Empty:
            break

def on_shortcut():
    global batching_state

    if batching_state == 'idle':
        print('Shortcut pressed. Starting batchmode recording.')
        batching_state = 'batching'
        record_and_transcribe_batch()
    elif batching_state == 'batching':
        print('Shortcut pressed. Finishing batching.')
        batching_thread.stop()
    else:
        print('Shortcut pressed, ignoring - recording is already finishing.')

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
            on_shortcut()

def on_release(key):
    try:
        current_keys.remove(key)
    except KeyError:
        pass  # Key was not in the set of pressed keys, ignore

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
