from pynput import keyboard

# Define a dictionary that maps the string representation of keys to their keyboard.Key constants
KEY_MAP = {
    # Modifier keys
    'ctrl': keyboard.Key.ctrl_l, # ctrl only works linux, windows you most likely mean ctrl_l
    'alt': keyboard.Key.alt_l,
    'shift': keyboard.Key.shift_l,
    'ctrl_l': keyboard.Key.ctrl_l,
    'ctrl_r': keyboard.Key.ctrl_r,
    'alt_l': keyboard.Key.alt_l,
    'alt_r': keyboard.Key.alt_r,
    'shift_l': keyboard.Key.shift_l,
    'shift_r': keyboard.Key.shift_r,
    'cmd': keyboard.Key.cmd,
    'cmd_l': keyboard.Key.cmd_l,  # Often called the Windows key on Windows or Command on Mac
    'cmd_r': keyboard.Key.cmd_r,  # Often called the Windows key on Windows or Command on Mac

    # Function keys
    'f1': keyboard.Key.f1,
    'f2': keyboard.Key.f2,
    'f3': keyboard.Key.f3,
    'f4': keyboard.Key.f4,
    'f5': keyboard.Key.f5,
    'f6': keyboard.Key.f6,
    'f7': keyboard.Key.f7,
    'f8': keyboard.Key.f8,
    'f9': keyboard.Key.f9,
    'f10': keyboard.Key.f10,
    'f11': keyboard.Key.f11,
    'f12': keyboard.Key.f12,
    'f13': keyboard.Key.f13,
    'f14': keyboard.Key.f14,
    'f15': keyboard.Key.f15,
    'f16': keyboard.Key.f16,
    'f17': keyboard.Key.f17,
    'f18': keyboard.Key.f18,
    'f19': keyboard.Key.f19,
    'f20': keyboard.Key.f20,

    # Navigation keys
    'up': keyboard.Key.up,
    'down': keyboard.Key.down,
    'left': keyboard.Key.left,
    'right': keyboard.Key.right,
    'home': keyboard.Key.home,
    'end': keyboard.Key.end,
    'page_up': keyboard.Key.page_up,
    'page_down': keyboard.Key.page_down,

    # Editing keys
    'space': keyboard.Key.space,
    'backspace': keyboard.Key.backspace,
    'delete': keyboard.Key.delete,
    'insert': keyboard.Key.insert,
    'enter': keyboard.Key.enter,
    'esc': keyboard.Key.esc,
    'tab': keyboard.Key.tab,
    'caps_lock': keyboard.Key.caps_lock,

    # Other keys
    'print_screen': keyboard.Key.print_screen,
    'scroll_lock': keyboard.Key.scroll_lock,
    'pause': keyboard.Key.pause,
    'menu': keyboard.Key.menu,
}

# Please note that the exact set of keys can vary depending on your keyboard layout and the operating system you are using.

def parse_key_combination(combination_string):
    """
    Parse a string representing a key combination into a tuple of keyboard keys.
    
    The input should be a string with keys separated by the "+" character. Each key
    should represent the actual key on the keyboard, and the case is not sensitive.
    The parse function converts the string into a tuple of constants that represent
    the keyboard keys.

    Example input:
        "ctrl+alt+space" which will be converted to (keyboard.Key.ctrl, keyboard.Key.alt, keyboard.Key.space)
    
    Parameters:
        combination_string (str): A string representing the key combination, 
                                  for example "ctrl+alt+space".

    Returns:
        tuple: A tuple with the keyboard key constants that the input string represents.
    """
    # Split the combination string by "+" and remove any leading/trailing whitespace
    keys = combination_string.split("+")
    keys = [key.strip() for key in keys]

    # Map the string representation to the actual keyboard.Key constants
    key_combination = tuple(KEY_MAP[key.lower()] for key in keys if key.lower() in KEY_MAP)

    return key_combination

# Example usage:
# combination_string = "ctrl+alt+space"
# combination_keys = parse_key_combination(combination_string)

# print(combination_keys)  # Outputs the tuple corresponding to the keys
