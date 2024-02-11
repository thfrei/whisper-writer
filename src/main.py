import os
from multiprocessing import Pipe, Process, Queue, Event
import signal # for proper handling of keyboard interrupt

from pynput import keyboard

from record import record_audio
from save import save_audio
# from status_window import StatusWindow
from transcribe import transcribe_audio
from type import typing
from status import status
from utils import load_config_with_defaults_from_env
from constants import State
from keyboard_key_parser import parse_key_combination

recordings_queue = Queue()
files_queue = Queue()
transcriptions_queue = Queue()
status_queue = Queue()

stop_recording = Event()
stop_recording.set()

config = load_config_with_defaults_from_env()

# Define the activation key combination
# todo use a wrapper function
COMBINATION = parse_key_combination(config['activation_key'])
COMBINATION_PTT = parse_key_combination(config['push_to_talk'])

###
# variables
app_state = State.IDLE
# The currently active modifiers
current_keys = set()
current_keys_ptt = set()

###
# handle multi-key shortcut
def on_shortcut():
    global app_state, control_recording_parent

    if app_state == State.IDLE:
        print('Shortcut pressed. Starting batchmode recording.')
        app_state = State.RECORDING
        stop_recording.clear()
    elif app_state == State.RECORDING:
        print('Shortcut pressed. Stop recording.')
        app_state = State.IDLE
        stop_recording.set()
    else:
        print('Shortcut pressed, ignoring - recording is already finishing.')

def on_press(key):
    if key in COMBINATION:
        current_keys.add(key)
        if all(k in current_keys for k in COMBINATION):
            # All required keys are currently pressed, so trigger the shortcut function
            on_shortcut()
    # if key in COMBINATION_PTT:
    #     current_keys_ptt.add(key)
    #     if all(k in current_keys for k in COMBINATION_PTT):
    #         # All required keys are currently pressed, so trigger the shortcut function
    #         on_shortcut()

def on_release(key):
    try:
        current_keys.remove(key)
    except KeyError:
        pass  # Key was not in the set of pressed keys, ignore


# shortcut push to talk (ptt)
def on_press_ptt(key):
    if key in COMBINATION:
        current_keys.add(key)
        if all(k in current_keys for k in COMBINATION):
            # All required keys are currently pressed, so trigger the shortcut function
            global app_state, control_recording_parent
            if app_state == State.IDLE:
                print('PTT Shortcut pressed. Starting recording.')
                app_state = State.RECORDING
                stop_recording.clear()

def on_release_ptt(key):
    try:
        current_keys.remove(key)
        global app_state
        print('PTT Shortcut Released. Stop recording.')
        app_state = State.IDLE
        stop_recording.set()
    except KeyError:
        pass  # Key was not in the set of pressed keys, ignore Why isn't nothing being recorded?

def init_worker():
    # signal.signal(signal.SIGINT, signal.SIG_IGN)
    print("") # noop

if __name__ == "__main__":
    try:
        # signal.signal(signal.SIGINT, signal.sig_)
        # Creating and starting the threads
        recording_process = Process(target=record_audio, args=(config, recordings_queue, stop_recording, status_queue, init_worker,))
        saving_process = Process(target=save_audio, args=(config, recordings_queue, files_queue, status_queue, init_worker,))
        transcription_process = Process(target=transcribe_audio, args=(config, files_queue, transcriptions_queue, status_queue, init_worker,))
        typing_process = Process(target=typing, args=(transcriptions_queue, status_queue, init_worker,))
        status_process = Process(target=status, args=(status_queue, init_worker, ))

        recording_process.start()
        print(f"PID: {recording_process.pid} - recording")
        saving_process.start()
        print(f"PID: {saving_process.pid} - saving")
        transcription_process.start()
        print(f"PID: {transcription_process.pid} - transcription")
        typing_process.start()
        print(f"PID: {typing_process.pid} - typing")
        status_process.start()
        print(f"PID: {status_process.pid} - status window")

    except KeyboardInterrupt:
        print("\nCaught KeyboardInterrupt, terminating processes...")
        recording_process.terminate()
        saving_process.terminate()
        transcription_process.terminate()
        typing_process.terminate()
        status_process.terminate()

        recording_process.join()
        saving_process.join()
        transcription_process.join()
        typing_process.join()
        status_process.join()
        print('\nExiting the script...')
        os.system('exit')

    print(f'Press shortcut {config["activation_key"]} to start recording and transcribing. \nPress Ctrl+C on the terminal window to quit.')
    try:
        # keyboard.wait()  # Keep the script running to listen for the shortcut
        # Set up the listener
        with keyboard.Listener(
                on_press=on_press,
                on_release=on_release) as listener: 
            listener.join()
    except KeyboardInterrupt:
        print('\nExiting the script...')
        # os.system('exit')
