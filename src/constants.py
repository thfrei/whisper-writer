from enum import Enum

# constants 
class State(Enum):
    IDLE = 'idle'
    RECORDING = 'recording'

class Recording(Enum):
    START = 'start'
    STOP = 'stop'