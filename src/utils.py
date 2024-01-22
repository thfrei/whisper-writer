import json
import os

def load_config_with_defaults():
    default_config = {
        'use_api': False,
        'api_options': {
            'model': 'whisper-1',
            'language': None,
            'temperature': 0.0,
            'initial_prompt': None
        },
        'local_model_options': {
            'model': 'base',
            'device': 'auto',
            'compute_type': 'auto',
            'language': None,
            'temperature': 0.0,
            'initial_prompt': None,
            'condition_on_previous_text': True,
            'vad_filter': False,
        },
        'activation_key': 'ctrl+shift+space',
        'sound_device': None,
        'sample_rate': 16000,
        'silence_duration': 900,
        'writing_key_press_delay': 0.008,
        'remove_trailing_period': True,
        'add_trailing_space': False,
        'remove_capitalization': False,
        'print_to_terminal': True,
    }

    config_path = os.path.join('src', 'config.json')
    if os.path.isfile(config_path):
        with open(config_path, 'r') as config_file:
            user_config = json.load(config_file)
            for key, value in user_config.items():
                if key in default_config and value is not None:
                    default_config[key] = value

    return default_config
