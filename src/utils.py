from dotenv import load_dotenv
import os

def load_config_with_defaults_from_env():
    load_dotenv()  # Load environment variables from a .env file
    config = {
        'use_api': os.getenv('USE_API', 'False').lower() in ('true', '1', 't'),
        'api_options': {
            'model': os.getenv('API_MODEL', 'whisper-1'),
            'language': os.getenv('API_LANGUAGE'),
            'temperature': float(os.getenv('API_TEMPERATURE', '0.0')),
            'initial_prompt': os.getenv('API_INITIAL_PROMPT'),
        },
        'local_model_options': {
            'model': os.getenv('LOCAL_MODEL', 'base'),
            # cpu, cuda, auto
            'device': os.getenv('LOCAL_DEVICE', 'auto'),
            'compute_type': os.getenv('LOCAL_COMPUTE_TYPE', 'auto'),
            'language': os.getenv('LOCAL_LANGUAGE') or None,
            'temperature': float(os.getenv('LOCAL_TEMPERATURE', '0.0')),
            'initial_prompt': os.getenv('LOCAL_INITIAL_PROMPT'),
            'condition_on_previous_text': os.getenv('LOCAL_CONDITION_ON_PREVIOUS_TEXT', 'True').lower() in ('true', '1', 't'),
            'vad_filter': os.getenv('LOCAL_VAD_FILTER', 'False').lower() in ('true', '1', 't'),
        },
        # vad silence filter: 3 highest
        'vad': int(os.getenv('VAD', '2')),
        'activation_key': os.getenv('ACTIVATION_KEY', 'ctrl+shift+space'),
        'sound_device': int(os.getenv('SOUND_DEVICE')) if os.getenv('SOUND_DEVICE') else None,
        'sample_rate': int(os.getenv('SAMPLE_RATE', '16000')),
        'silence_duration': int(os.getenv('SILENCE_DURATION', '900')),
        'writing_key_press_delay': float(os.getenv('WRITING_KEY_PRESS_DELAY', '0.008')),
        'remove_trailing_period': os.getenv('REMOVE_TRAILING_PERIOD', 'True').lower() in ('true', '1', 't'),
        'add_trailing_space': os.getenv('ADD_TRAILING_SPACE', 'False').lower() in ('true', '1', 't'),
        'remove_capitalization': os.getenv('REMOVE_CAPITALIZATION', 'False').lower() in ('true', '1', 't'),
        'print_to_terminal': os.getenv('PRINT_TO_TERMINAL', 'True').lower() in ('true', '1', 't'),
    }
    return config
