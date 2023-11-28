import multiprocessing
from multiprocessing.sharedctypes import Synchronized
from multiprocessing.connection import PipeConnection
from pathlib import Path
import threading
from typing import Callable, Union
import soundfile as sf
import numpy as np
import librosa
import librosa.effects
from .common import *
from .player_subprocesser import *


__all__ = [
    "AudioPlayer",
]


class AudioPlayer:
    # 対応している拡張子
    # 現状.wav以外使う予定なし
    SUPPORT_SUFFIXES = tuple([".wav"])
    
    def __init__(
        self,
        sr:int=48000,
        rate:float=1.0,
        post_setup_command:Callable[[],None]=None,
    ):
        self.__state:Synchronized = multiprocessing.Value("i", AudioState.SETUP.value)
        self.__sr:Synchronized = multiprocessing.Value("i", sr)
        self.__rate:Synchronized = multiprocessing.Value("i", int(rate*100))
        self.__playback_position:Synchronized = multiprocessing.Value("i", 0)
        self.parent_conn, self.child_conn = multiprocessing.Pipe()
        
        # variable
        self.channelmap:list[int] = []
        self.x:np.ndarray = np.zeros(0)
        
        self.player_subprocess = multiprocessing.Process(
            target=self.subprocess,
            args=(self.child_conn, self.__state, self.__sr, self.__rate, self.__playback_position, ),
        )
        self.player_subprocess.start()
        
        self.post_setup_thread = threading.Thread(target=self.post_setup, args=(post_setup_command, ))
        self.post_setup_thread.start()

    @property
    def state(self) -> AudioState:
        pass

    @state.getter
    def state(self):
        return AudioState.parse(self.__state.value)

    @state.setter
    def state(self, value:AudioState):
        if self.state is not AudioState.RELEASE:
            self.__state.value = value.value
    
    @property
    def sr(self) -> int:
        pass
    
    @sr.getter
    def sr(self):
        return self.__sr.value
    
    @sr.setter
    def sr(self, sr:float):
        self.__sr.value = sr
    
    @property
    def rate(self) -> float:
        pass
    
    @rate.getter
    def rate(self):
        return self.__rate.value * 0.01
    
    @rate.setter
    def rate(self, value:float):
        if self.state is AudioState.NONE:
            self.__rate.value = int(value * 100)

    @property
    def playback_position(self) -> int:
        pass
    
    @playback_position.getter
    def playback_position(self):
        return self.__playback_position.value
    
    @playback_position.setter
    def playback_position(self,sec):
        self.__playback_position.value = int(sec * self.sr)
    
    @property
    def playback_position_sec(self) -> float:
        pass
    
    @playback_position_sec.getter
    def playback_position_sec(self):
        return self.playback_position / self.sr

    def post_setup(self, post_func:Union[Callable[[],None],None]):
        """セットアップ完了時の処理

        Args:
            func (Union[Callable[[],None],None]): _description_
        """
        # APSからchannelmapを受信
        self.channelmap = self.parent_conn.recv()
        
        if self.state is AudioState.RELEASE:
            return
        
        if post_func is not None:
            post_func()
    
    def playpath(self, path:Union[str,Path]) -> bool:
        if isinstance(path, str):
            path = Path(path)
        elif not isinstance(path, Path):
            return False
        
        if not path.is_file():
            return False
        
        if path.suffix not in self.SUPPORT_SUFFIXES:
            return False
        
        x, sr = sf.read(str(path), dtype=np.float32)
        
        return self.playdata(x, sr)
    
    def playdata(self, x:np.ndarray, sr:int) -> bool:
        if not isinstance(x, np.ndarray) or not isinstance(sr, int):
            return False
    
        if sr != self.sr:
            self.sr = sr
            self.state = AudioState.SETUP
            self.channelmap = self.parent_conn.recv()
        
        if self.rate != 1.0:
            x = librosa.effects.time_stretch(x, rate=self.rate)
        
        if x.ndim == 1:
            x = x[:, None] # force 2d
        if x.ndim != 2:
            print(f"data must be 1d or 2d, not {x.ndim}d")
            return False

        if x.shape[1] == 1 and len(self.channelmap) != 1:
            x = np.tile(x, [1, len(self.channelmap)])
        
        # internally, channel numbers are always ascending:
        sortidx = sorted(range(len(self.channelmap)), key=lambda k: self.channelmap[k])
        x:np.ndarray = x[:, sortidx]
        
        if x.shape[1] != len(self.channelmap):
            print(f"second dimension of data must be equal to the number of channels, not {x.shape[1]}")
            return False
        
        if x.shape != self.x.shape or not np.allclose(x, self.x):
            self.x = x
            self.state = AudioState.RECV
            self.parent_conn.send(x)
        else:
            self.state = AudioState.PLAY
        
        return True
    
    def stop(self) -> bool:
        """再生停止

        Returns:
            bool: _description_
        """
        if self.state in [AudioState.PLAY, AudioState.PAUSE]:
            self.state = AudioState.STOP
            return True
        return False
    
    def pause(self) -> bool:
        """一時停止

        Returns:
            bool: _description_
        """
        if self.state is AudioState.PLAY:
            self.state = AudioState.PAUSE
            return True
        return False
    
    def resume(self) -> bool:
        """再生再開

        Returns:
            bool: _description_
        """
        if self.state is AudioState.PAUSE:
            self.state = AudioState.PLAY
            return True
        return False
    
    def release(self) -> None:
        """解放処理
        """
        self.state = AudioState.RELEASE
        self.post_setup_thread.join()
        self.player_subprocess.join()
    
    @staticmethod
    def subprocess(
        conn:PipeConnection,
        state:Synchronized,
        sr:Synchronized,
        rate:Synchronized,
        playback_position:Synchronized,
    ):
        aps = AudioPlayerSubprocesser(conn, state, sr, rate, playback_position)
        aps.mainloop()