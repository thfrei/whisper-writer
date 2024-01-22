# Standard library imports
import os
import queue
import tempfile
import threading
import time
import traceback
import wave
from multiprocessing import Pipe, Process, Queue

# Third-party imports
import numpy as np
import openai
import sounddevice as sd
import webrtcvad
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from pynput import keyboard
from pynput.keyboard import Controller

# Local application/library-specific imports
from record import record_audio
from save import save_audio
from status_window import StatusWindow
from transcribe import transcribe_audio
from type import typing
from utils import load_config_with_defaults
from constants import Recording, State

###
recordings_queue = Queue()
files_queue = Queue()
transcriptions_queue = Queue()

control_recording_parent, control_recording_child = Pipe()
status_pipe_parent, status_pipe_child = Pipe()

config = load_config_with_defaults()

# Define the activation key combination
COMBINATION = {keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.Key.space}

###
# variables
app_state = State.IDLE
# The currently active modifiers
current_keys = set()

def on_shortcut():
    global app_state, control_recording_parent

    if app_state == State.IDLE:
        print('Shortcut pressed. Starting batchmode recording.')
        control_recording_parent.send(Recording.START)
        app_state = State.RECORDING
    elif app_state == State.RECORDING:
        print('Shortcut pressed. Stop recording.')
        control_recording_parent.send(Recording.STOP)
        app_state = State.IDLE
    else:
        print('Shortcut pressed, ignoring - recording is already finishing.')

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

if __name__ == "__main__":
    # start and handle subprocesses
    try:
        # Creating and starting the threads
        recording_process = Process(target=record_audio, args=(config, recordings_queue, control_recording_child, status_pipe_child,))
        saving_process = Process(target=save_audio, args=(config, recordings_queue, files_queue, status_pipe_child,))
        transcription_process = Process(target=transcribe_audio, args=(config, files_queue, transcriptions_queue, status_pipe_child,))
        typing_process = Process(target=typing, args=(transcriptions_queue, status_pipe_child,))

        recording_process.start()
        print(f"PID: {recording_process.pid} - recording")
        saving_process.start()
        print(f"PID: {saving_process.pid} - saving")
        transcription_process.start()
        print(f"PID: {transcription_process.pid} - transcription")
        typing_process.start()
        print(f"PID: {typing_process.pid} - typing")

    except KeyboardInterrupt:
        print("\nCaught KeyboardInterrupt, terminating processes...")
        recording_process.terminate()
        saving_process.terminate()
        transcription_process.terminate()
        typing_process.terminate()

        recording_process.join()
        saving_process.join()
        transcription_process.join()
        typing_process.join()

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
