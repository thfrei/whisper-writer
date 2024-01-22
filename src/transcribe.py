import queue, traceback
import openai
import os
import time

from dotenv import load_dotenv
from faster_whisper import WhisperModel

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


def transcribe_audio(config, files_queue, transcriptions_queue, status_pipe):
    method = 'OpenAI\'s API' if config['use_api'] else 'a local model'
    local_model = None
    print(f'Script activated. Whisper is set to run using {method}. To change this, modify the "use_api" value in the src\\config.json file.')
    if not config['use_api']:
        print('Creating local model...')
        local_model = create_local_model(config)
        print('Local model created.')

    while True:
        try:
            # Transcribing saved audio file
            file_path = files_queue.get()
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
                # status_pipe.put(('error', 'Error'))

            print('Transcription:', result.strip()) if config['print_to_terminal'] else ''
            # status_pipe.put(('idle', ''))

            text = process_transcription(result.strip(), config) if result else ''
            transcriptions_queue.put(text)
        except queue.Empty:
            #print('...transcription queue empty')
            time.sleep(0.2)
        except Exception as e:
            print(f"An error occurred during transcription: {e}")
            traceback.print_exc()
            return