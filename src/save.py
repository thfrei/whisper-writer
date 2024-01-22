import queue, traceback
import tempfile
import wave
import time

def save_audio(config, recordings_queue, files_queue, status_pipe):
    sample_rate = config['sample_rate'] if config else 16000  # 16kHz, supported values: 8kHz, 16kHz, 32kHz, 48kHz, 96kHz
    while True:
        try:
            audio_data = recordings_queue.get()
            print('Recording detected. Saving...')
            # Save the recorded audio as a temporary WAV file on disk
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
                with wave.open(temp_audio_file.name, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 2 bytes (16 bits) per sample
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_data.tobytes())
            files_queue.put(temp_audio_file.name)
            print(f'Recording saved to: {temp_audio_file.name}')
        except queue.Empty:
            # print('...save audio queue empty')
            time.sleep(0.2)
        except Exception as e:
            print(f"An error occurred during transcription: {e}")
            traceback.print_exc()