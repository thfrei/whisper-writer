import queue, traceback
import numpy as np
import openai
import os
import sounddevice as sd
import tempfile
import wave
import webrtcvad
import threading
import time
from multiprocessing import Queue, Process
from pynput.keyboard import Controller as KeyboardController
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from utils import load_config_with_defaults

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
