from multiprocessing.sharedctypes import Synchronized
from multiprocessing.connection import PipeConnection
import soundcard as sc
from soundcard.mediafoundation import _ffi, _Player
import time
import numpy as np
from .common import *


__all__ = [
    "AudioPlayerSubprocesser",
]


class AudioPlayerSubprocesser:
    def __init__(
        self,
        conn:PipeConnection,
        state:Synchronized,
        sr:Synchronized,
        rate:Synchronized,
        playback_position:Synchronized,
    ):
        self.conn = conn
        self.data = None
        self.__state = state
        self.__sr = sr
        self.__rate = rate
        self.__playback_position = playback_position
    
    @property
    def sr(self) -> int:
        pass

    @sr.getter
    def sr(self):
        return self.__sr.value
    
    @property
    def rate(self) -> float:
        pass

    @rate.getter
    def rate(self):
        return self.__rate.value * 0.01
    
    @property
    def playback_position(self) -> int:
        pass

    @playback_position.getter
    def playback_position(self):
        return self.__playback_position.value

    @playback_position.setter
    def playback_position(self, value:int):
        self.__playback_position.value = value

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
    
    def update(self, sp:_Player):
        if self.state is AudioState.RECV:
            # サウンドデータを受信
            self.x:np.ndarray = self.conn.recv()
            self.state = AudioState.PLAY
        
        if self.state is AudioState.PLAY:
            self.playloop(sp, self.x.copy())
            self.state = AudioState.NONE
            self.playback_position = 0
        else:
            time.sleep(0.01)
    
    def playloop(self, sp:_Player, data:np.ndarray):
        data_len = len(data)
        while (data.nbytes > 0) and (data_len>self.playback_position):
            if self.state is AudioState.PAUSE:
                time.sleep(0.01)
                continue
            elif self.state in [AudioState.STOP, AudioState.RELEASE]:
                break
            
            towrite:int = sp._render_available_frames()
            if towrite == 0:
                time.sleep(0.001)
                continue
            if data_len > self.playback_position + towrite:
                bytes = data[self.playback_position:self.playback_position + towrite].ravel().tobytes()
            elif self.playback_position + towrite >= data_len:
                bytes = data[self.playback_position:].ravel().tobytes()
            
            buffer = sp._render_buffer(towrite)
            _ffi.memmove(buffer[0], bytes, len(bytes))
            sp._render_release(towrite)
            current = towrite
            # MEMO: どれくらい誤差あるんだろう
            self.playback_position += int(towrite * self.rate)
    
    def mainloop(self):
        # SETUP後にsendをしないと無限ループに陥るので後ろでやる
        #if self.state is AudioState.RELEASE:
        #    return
        
        # MEMO: 複数対応する場合はget_speaker(self.id)に変更
        with sc.default_speaker().player(self.sr) as sp:
            # APにchannelmapを送信
            self.conn.send(sp.channelmap)
            
            # state SETUP to NONE
            self.state = AudioState.NONE
            
            while self.state not in [AudioState.RELEASE, AudioState.SETUP]:
                self.update(sp)
        
        # プレイヤーの再設定
        if self.state is not AudioState.RELEASE:
            self.mainloop()