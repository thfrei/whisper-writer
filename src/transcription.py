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

recordings = Queue()
files = Queue()
transcriptions = Queue()
stop_recording = threading.Event()
stop_saving = threading.Event()
stop_transcribing = threading.Event()
stop_typing = threading.Event()

if load_dotenv():
    openai.api_key = os.getenv('OPENAI_API_KEY')

def process_transcription(transcription, config=None):
    if config:
        if config['remove_trailing_period'] and transcription.endswith('.'):
            transcription = transcription[
                :-1]
        if config['add_trailing_space']:
            transcription += ' '
        if config['remove_capitalization']:
            transcription = transcription.lower()
    
    return transcription

def create_local_model(config):
    model = WhisperModel(config['local_model_options']['model'],
                         device=config['local_model_options']['device'],
                         compute_type=config['local_model_options']['compute_type'],)
    return model

"""
=====================================================================
=====================================================================
"""

def record_audio(config, recordings):
    sound_device = config['sound_device'] if config else None
    sample_rate = config['sample_rate'] if config else 16000  # 16kHz, supported values: 8kHz, 16kHz, 32kHz, 48kHz, 96kHz
    frame_duration = 30  # 30ms, supported values: 10, 20, 30
    buffer_duration = 300  # 300ms
    silence_duration = config['silence_duration'] if config else 900  # 900ms

    vad = webrtcvad.Vad(2)  # Aggressiveness mode: 3 (highest)
    buffer = []
    recording = []
    num_silent_frames = 0
    num_buffer_frames = buffer_duration // frame_duration
    num_silence_frames = silence_duration // frame_duration
    exit_reason = "Unknown"

    while True:
        try:
            with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=sample_rate * frame_duration // 1000,
                                device=sound_device, callback=lambda indata, frames, time, status: buffer.extend(indata[:, 0])) as stream:
                device_info = sd.query_devices(stream.device)
                print('Recording with sound device:', device_info['name']) if config['print_to_terminal'] else ''
                while True:
                    if len(buffer) < sample_rate * frame_duration // 1000:
                        continue

                    frame = buffer[:sample_rate * frame_duration // 1000]
                    buffer = buffer[sample_rate * frame_duration // 1000:]

                    is_speech = vad.is_speech(np.array(frame).tobytes(), sample_rate)
                    if is_speech:
                        recording.extend(frame)
                        num_silent_frames = 0
                    else:
                        if len(recording) > 0:
                            num_silent_frames += 1

                    # if num_silent_frames >= num_silence_frames or cancel_flag():
                    if num_silent_frames >= num_silence_frames:
                        if len(recording) < sample_rate:  # If <1 sec of audio recorded, continue
                            continue  
                        # if cancel_flag():
                        #     exit_reason= "Hotkey pressed"
                        if num_silent_frames >= num_silence_frames:
                            exit_reason = "Silence"
                            break
                        break

            audio_data = np.array(recording, dtype=np.int16)
            recordings.put(audio_data)
            print(f'Recording finished: {exit_reason}. Size:', audio_data.size) if config['print_to_terminal'] else ''

            # restart audio
            exit_reason = "Unknown"
            buffer = []
            recording = []
            num_silent_frames = 0
            num_buffer_frames = buffer_duration // frame_duration
            num_silence_frames = silence_duration // frame_duration
        except sd.PortAudioError as e:
            print(f"An error occurred while opening the audio input stream: {e}")
            if config['print_to_terminal']:
                print("Please check your sound device settings and try again.")
            return
            # status_queue.put(('error', 'Error'))

def save_audio(config, recordings, files):
    sample_rate = config['sample_rate'] if config else 16000  # 16kHz, supported values: 8kHz, 16kHz, 32kHz, 48kHz, 96kHz
    while not stop_saving.is_set():
        try:
            audio_data = recordings.get()
            print('Recording detected. Saving...')
            # Save the recorded audio as a temporary WAV file on disk
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
                with wave.open(temp_audio_file.name, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 2 bytes (16 bits) per sample
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_data.tobytes())
            files.put(temp_audio_file.name)
            print(f'Recording saved to: {temp_audio_file.name}')
        except queue.Empty:
            # print('...save audio queue empty')
            time.sleep(0.2)
        except Exception as e:
            print(f"An error occurred during transcription: {e}")
            traceback.print_exc()
        except Exception as e:
            traceback.print_exc()
            # status_queue.put(('error', 'Error'))

def transcribe_audio(config, files, transcriptions):
    method = 'OpenAI\'s API' if config['use_api'] else 'a local model'
    local_model = None
    print(f'Script activated. Whisper is set to run using {method}. To change this, modify the "use_api" value in the src\\config.json file.')
    if not config['use_api']:
        print('Creating local model...')
        local_model = create_local_model(config)
        print('Local model created.')

    while not stop_transcribing.is_set():
        try:
            # Transcribing saved audio file
            file_path = files.get()
            print("Starting transcription for file:", file_path)                     
            if not os.path.exists(file_path):                                                               
                print(f"File not found: {file_path}")                                                       
                continue                       
            print("Transcribing audio file:", file_path)
            
            # If configured, transcribe the temporary audio file using the OpenAI API
            if config['use_api']:
                api_options = config['api_options']
                with open(file_path, 'rb') as audio_file:
                    response = openai.Audio.transcribe(model=api_options['model'], 
                                                    file=audio_file,
                                                    language=api_options['language'],
                                                    prompt=api_options['initial_prompt'],
                                                    temperature=api_options['temperature'],)
                result = response.get('text')
            # Otherwise, transcribe the temporary audio file using a local model
            elif not config['use_api']:
                print("Using local model to transcribe.")
                model_options = config['local_model_options']
                start_time = time.time()
                response = local_model.transcribe(audio=file_path,
                                                language=model_options['language'],
                                                initial_prompt=model_options['initial_prompt'],
                                                condition_on_previous_text=model_options['condition_on_previous_text'],
                                                temperature=model_options['temperature'],
                                                vad_filter=model_options['vad_filter'],)
                end_time = time.time()
                print(f"Transcription completed in {end_time - start_time} seconds.")
                result = ''.join([segment.text for segment in list(response[0])])
            
            # Remove the temporary audio file
            try:
                os.remove(file_path)
            except Exception as e:
                traceback.print_exc()
                # status_queue.put(('error', 'Error'))

            print('Transcription:', result.strip()) if config['print_to_terminal'] else ''
            # status_queue.put(('idle', ''))

            
            text = process_transcription(result.strip(), config) if result else ''
            transcriptions.put(text)
        except queue.Empty:
            #print('...transcription queue empty')
            time.sleep(0.2)
        except Exception as e:
            print(f"An error occurred during transcription: {e}")
            traceback.print_exc()
            return

def typing(transcriptions, interval=0.005):
    keyboard = KeyboardController()
    while not stop_typing.is_set():
        try:
            transcription = transcriptions.get_nowait()
            print('Typing: ')
            for char in transcription:
                print(char, end="")
                keyboard.press(char)
                keyboard.release(char)
                time.sleep(interval)
        except queue.Empty:
            time.sleep(0.2)

def record_and_transcribe_batch():
    try:
        # Creating and starting the threads
        config = load_config_with_defaults()
        recording_thread = Process(target=record_audio, args=(config, recordings,))
        saving_thread = Process(target=save_audio, args=(config, recordings, files,))
        transcription_thread = Process(target=transcribe_audio, args=(config, files, transcriptions,))
        typing_thread = Process(target=typing, args=(transcriptions,))

        print(f"Recording thread PID: {recording_thread.pid}")
        print(f"Saving thread PID: {saving_thread.pid}")
        print(f"Transcription thread PID: {transcription_thread.pid}")
        print(f"Typing thread PID: {typing_thread.pid}")

        recording_thread.start()
        print(f"Recording thread started with PID: {recording_thread.pid}")
        saving_thread.start()
        print(f"Saving thread started with PID: {saving_thread.pid}")
        transcription_thread.start()
        print(f"Transcription thread started with PID: {transcription_thread.pid}")
        typing_thread.start()
        
        print(f"Typing thread started with PID: {typing_thread.pid}")

    except KeyboardInterrupt:
        # Interrupting the threads and waiting for them to finish
        recording_thread.join()
        saving_thread.join()
        transcription_thread.join()
        typing_thread.join()
