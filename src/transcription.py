import traceback
import numpy as np
import openai
import os
import sounddevice as sd
import tempfile
import wave
import webrtcvad
import keyboard
import threading
import time
from multiprocessing import Queue
import multiprocessing
from pynput.keyboard import Controller
from dotenv import load_dotenv
from faster_whisper import WhisperModel

recordings = Queue()
files = Queue()
transcriptions = Queue()
stop_recording = threading.Event()
stop_saving = threading.Event()
stop_transcribing = threading.Event()
stop_typing = threading.Event()
stop_threads = False


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
Record audio from the microphone and transcribe it using the Whisper model.
Recording stops when the user stops speaking.
"""
def record_and_transcribe(status_queue, cancel_flag, config, local_model=None, recording_thread=None):
    sound_device = config['sound_device'] if config else None
    sample_rate = config['sample_rate'] if config else 16000  # 16kHz, supported values: 8kHz, 16kHz, 32kHz, 48kHz, 96kHz
    frame_duration = 30  # 30ms, supported values: 10, 20, 30
    buffer_duration = 300  # 300ms
    silence_duration = config['silence_duration'] if config else 900  # 900ms

    vad = webrtcvad.Vad(3)  # Aggressiveness mode: 3 (highest)
    buffer = []
    recording = []
    num_silent_frames = 0
    num_buffer_frames = buffer_duration // frame_duration
    num_silence_frames = silence_duration // frame_duration
    exit_reason = "Unknown"
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

                if num_silent_frames >= num_silence_frames or cancel_flag():
                    if len(recording) < sample_rate:  # If <1 sec of audio recorded, continue
                        continue  
                    if cancel_flag():
                        exit_reason= "Hotkey pressed"
                    if num_silent_frames >= num_silence_frames:
                        if recording_thread:
                            recording_thread.stop()
                        exit_reason = "Silence"
                    break

#            if cancel_flag():
#                status_queue.put(('cancel', ''))
#                return ''
        
        audio_data = np.array(recording, dtype=np.int16)
        print(f'Recording finished: {exit_reason}. Size:', audio_data.size) if config['print_to_terminal'] else ''
        
        # Save the recorded audio as a temporary WAV file on disk
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
            with wave.open(temp_audio_file.name, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 2 bytes (16 bits) per sample
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data.tobytes())

        status_queue.put(('transcribing', 'Transcribing...'))
        print('Transcribing audio file...') if config['print_to_terminal'] else ''
        
        # If configured, transcribe the temporary audio file using the OpenAI API
        if config['use_api']:
            api_options = config['api_options']
            with open(temp_audio_file.name, 'rb') as audio_file:
                response = openai.Audio.transcribe(model=api_options['model'], 
                                                   file=audio_file,
                                                   language=api_options['language'],
                                                   prompt=api_options['initial_prompt'],
                                                   temperature=api_options['temperature'],)
            result = response.get('text')
        # Otherwise, transcribe the temporary audio file using a local model
        elif not config['use_api']:
            if not local_model:
                print('Creating local model...') if config['print_to_terminal'] else ''
                local_model = create_local_model(config)
                print('Local model created.') if config['print_to_terminal'] else ''
            model_options = config['local_model_options']
            response = local_model.transcribe(audio=temp_audio_file.name,
                                              language=model_options['language'],
                                              initial_prompt=model_options['initial_prompt'],
                                              condition_on_previous_text=model_options['condition_on_previous_text'],
                                              temperature=model_options['temperature'],
                                              vad_filter=model_options['vad_filter'],)
            result = ''.join([segment.text for segment in list(response[0])])

        # Remove the temporary audio file
        os.remove(temp_audio_file.name)
        
#        if cancel_flag():
#            status_queue.put(('cancel', ''))
#            return ''

        print('Transcription:', result.strip()) if config['print_to_terminal'] else ''
        status_queue.put(('idle', ''))
        
        return process_transcription(result.strip(), config) if result else ''

    except Exception as e:
        traceback.print_exc()
        status_queue.put(('error', 'Error'))

"""
=====================================================================
=====================================================================
"""

def record_audio(status_queue, cancel_flag, config):
    sound_device = config['sound_device'] if config else None
    sample_rate = config['sample_rate'] if config else 16000  # 16kHz, supported values: 8kHz, 16kHz, 32kHz, 48kHz, 96kHz
    frame_duration = 30  # 30ms, supported values: 10, 20, 30
    buffer_duration = 300  # 300ms
    silence_duration = config['silence_duration'] if config else 900  # 900ms

    vad = webrtcvad.Vad(1)  # Aggressiveness mode: 3 (highest)
    buffer = []
    recording = []
    num_silent_frames = 0
    num_buffer_frames = buffer_duration // frame_duration
    num_silence_frames = silence_duration // frame_duration
    exit_reason = "Unknown"
    while not stop_recording.is_set():
        try:
            with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=sample_rate * frame_duration // 1000,
                                device=sound_device, callback=lambda indata, frames, time, status: buffer.extend(indata[:, 0])) as stream:
                device_info = sd.query_devices(stream.device)
                print('Recording with sound device:', device_info['name']) if config['print_to_terminal'] else ''
                while True:
                    # print(".", end="")
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

                    if num_silent_frames >= num_silence_frames or cancel_flag():
                        if len(recording) < sample_rate:  # If <1 sec of audio recorded, continue
                            continue  
                        if cancel_flag():
                            exit_reason= "Hotkey pressed"
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
        except Exception as e:
            traceback.print_exc()
            status_queue.put(('error', 'Error'))

def save_audio(status_queue, cancel_flag, config):
    sample_rate = config['sample_rate'] if config else 16000  # 16kHz, supported values: 8kHz, 16kHz, 32kHz, 48kHz, 96kHz
    while not stop_saving.is_set():
        try:
            # print("Recording queue:")
            # print(list(recordings.queue))
            audio_data = recordings.get_nowait()
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
            recordings.task_done()
        except queue.Empty:
            # print('...save audio queue empty')
            time.sleep(0.2)
        except Exception as e:
            traceback.print_exc()
            status_queue.put(('error', 'Error'))

def transcribe_audio(status_queue, cancel_flag, config, local_model=None):
    while not stop_transcribing.is_set():
        try:
            print("Files queue:")
            print(list(files.queue))
            # Transcribing saved audio file
            file_path = files.get_nowait()
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
                if not local_model:
                    print('Creating local model...') if config['print_to_terminal'] else ''
                    local_model = create_local_model(config)
                    print('Local model created.') if config['print_to_terminal'] else ''
                model_options = config['local_model_options']
                response = local_model.transcribe(audio=file_path,
                                                language=model_options['language'],
                                                initial_prompt=model_options['initial_prompt'],
                                                condition_on_previous_text=model_options['condition_on_previous_text'],
                                                temperature=model_options['temperature'],
                                                vad_filter=model_options['vad_filter'],)
                result = ''.join([segment.text for segment in list(response[0])])

            # Remove the temporary audio file
            try:
                os.remove(file_path)
            except Exception as e:
                traceback.print_exc()
                status_queue.put(('error', 'Error'))

            print('Transcription:', result.strip()) if config['print_to_terminal'] else ''
            status_queue.put(('idle', ''))
            
            text = process_transcription(result.strip(), config) if result else ''
            transcriptions.put(text)
            files.task_done()
        except queue.Empty:
            #print('...transcription queue empty')
            time.sleep(0.2)

def typing():
    # try:
        while not stop_typing.is_set():
            try:
                transcription = transcriptions.get_nowait()
                print('Typing: ')
                print(transcription)
                transcriptions.task_done()
            except queue.Empty:
                time.sleep(1)
    # except KeyboardInterrupt:
    #     print("typing(): Keyboard Interrupt detected, stopping thread")
    # finally:
    #     stop_typing.set()
        
            



def record_and_transcribe_batch(status_queue, cancel_flag, config, local_model=None, recording_thread2=None):
    exit_reason = "Unknown"
    stop_threads = False

    try:
        # Creating and starting the threads
        recording_thread = multiprocessing.Process(target=record_audio, args=(status_queue, cancel_flag, config))
        saving_thread = multiprocessing.Process(target=save_audio, args=(status_queue, cancel_flag, config))
        transcription_thread = multiprocessing.Process(target=transcribe_audio, args=(status_queue, cancel_flag, config, local_model))
        typing_thread = multiprocessing.Process(target=typing)
        
        recording_thread.start()
        saving_thread.start()
        transcription_thread.start()
        typing_thread.start()
        
        # Waiting for keyboard interrupt to end the script
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        # Signal threads to stop
        stop_threads = True
        
        # Interrupting the threads and waiting for them to finish
        recording_thread.join()
        saving_thread.join()
        transcription_thread.join()
        typing_thread.join()