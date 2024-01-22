import time

import numpy as np
import sounddevice as sd
import webrtcvad

def record_audio(config, recordings_queue, stop_recording, status_pipe):
    sound_device = config['sound_device'] if config else None
    sample_rate = config['sample_rate'] if config else 16000  # 16kHz, supported values: 8kHz, 16kHz, 32kHz, 48kHz, 96kHz
    frame_duration = 30  # 30ms, supported values: 10, 20, 30
    buffer_duration = 300  # 300ms
    silence_duration = config['silence_duration'] if config else 900  # 900ms

    vad = webrtcvad.Vad(config['vad'])  # Aggressiveness mode: 3 (highest)
    buffer = []
    recording = []
    num_silent_frames = 0
    num_buffer_frames = buffer_duration // frame_duration
    num_silence_frames = silence_duration // frame_duration
    exit_reason = "Unknown"

    while True:
        if not stop_recording.is_set():
            try:
                # find out device: `python -m sounddevice`
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
                            if stop_recording.is_set():
                                 exit_reason= "Hotkey pressed - stop in rec"
                            if num_silent_frames >= num_silence_frames:
                                exit_reason = "Silence"
                                break
                            break

                audio_data = np.array(recording, dtype=np.int16)
                recordings_queue.put(audio_data)
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
                # status_pipe.put(('error', 'Error'))
        else:
            time.sleep(0.2)