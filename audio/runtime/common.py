from enum import Enum, auto


__all__ = [
    "AudioState",
]


class AudioState(Enum):
    NONE = 0
    RELEASE = auto()
    SETUP = auto()
    RECV = auto()
    PLAY = auto()
    STOP = auto()
    PAUSE = auto()
    RESUME = auto()
    
    @staticmethod
    def parse(value:int):
        for state in AudioState:
            if state.value == value:
                return state
        raise ValueError("fail parse AudioState")