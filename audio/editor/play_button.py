from enum import Enum, auto
from dataclasses import dataclass, field
from pathlib import Path
import tkinter as tk
from typing import Callable, Union
import threading
import numpy as np
import time
from ..runtime import AudioState, AudioPlayer


__all__ = [
    "PlayImageButton",
]


class PlayType(Enum):
    NONE = auto()
    DATA = auto()
    PATH = auto()


@dataclass
class Playdata:
    type:PlayType=PlayType.NONE
    x:np.ndarray=field(default=lambda x:np.zeros(0))
    sr:int=0
    path:Union[str,Path]=""


class PlayImageButton(tk.Button):
    """再生/一時停止ボタン

    Args:
        tk (_type_): _description_
    """
    
    PLAYING_STATE = (AudioState.RECV, AudioState.PLAY, AudioState.PAUSE)
    
    def __init__(
        self,
        master:tk.Misc,
        player:AudioPlayer,
        state=tk.NORMAL,
        background:str="white",
        play_begin_command:Callable[[],None]=None,
        play_end_command:Callable[[],None]=None,
        playing_command:Callable[[float],None]=None,
    ):
        # resource
        self.play_image = tk.PhotoImage(data="iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAKNJREFUOE+t08ENwyAMBVB7lM7DFGxSNqE7YItb2SRZxLgiIlKkhEJoucCFp4+NEQDAGPMuu4jYGONazqMLK6CHC15E3Ch0BWyWqtqcc+pBTaAmSojoQgip9aQesN9LrfqMAjt0qs9d4FSfKaDG8URkfwFWInpMAaXFzOxLkrvAFvvY0lGg+R96wIqIduojqeqTmV1vqP42TAsAlHe+vsW9SvMBv2p7EbjkvWgAAAAASUVORK5CYII=")
        self.pause_image = tk.PhotoImage(data="iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAHRJREFUOE9jtHDybPn/n6GaAQX833hy/44AZCFzR48NDAyM/shijAwMbYzmjp5fGBgYuFENYGBgZmRUOLZv20OQuJWTl/zf//8foKthYGD4CjIAJCFPpgEPRw1gGA0DhmETBpRlJgtHz9b/DAxVZGVnRoZWAFRqqJWftJqjAAAAAElFTkSuQmCC")
        
        super().__init__(master, image=self.play_image, relief=tk.FLAT, width=22, height=22, state=state, background=background, anchor=tk.CENTER, command=self.command)

        # instance
        self.player = player
        
        # variable
        self.playdata = Playdata()
        self.play_thread = None
        self.playing_thread = None
        
        # callback
        self.play_begin_func = play_begin_command
        self.play_end_func = play_end_command
        self.playing_func = playing_command
    
    def set_data(self, x:np.ndarray, sr:int):
        self.playdata.type = PlayType.DATA
        self.playdata.x = x
        self.playdata.sr = sr
    
    def set_path(self, path:Union[str,Path]):
        self.playdata.type = PlayType.PATH
        self.playdata.path = path
    
    def command(self):
        if self.player.state is AudioState.NONE:
            self.play_thread = threading.Thread(target=self.play)
        else:
            self.play_thread = threading.Thread(target=self.pause_or_resume)
        
        self.play_thread.start()
    
    def play(self):
        if self.playdata.type is PlayType.NONE:
            return
        
        if self.player.state is AudioState.RELEASE:
            return
        
        if self.playdata.type is PlayType.DATA:
            result = self.player.playdata(self.playdata.x, self.playdata.sr)
        else:
            result = self.player.playpath(self.playdata.path)
        
        if result:
            if self.play_begin_func is not None:
                self.play_begin_func()
            
            self.playing_thread = threading.Thread(target=self.playing)
            self.playing_thread.start()
            
            self.configure(image=self.pause_image)
    
    def pause_or_resume(self):
        if self.player.state is AudioState.RELEASE:
            return
        
        if self.player.state is AudioState.PLAY:
            if self.player.pause():
                self.configure(image=self.play_image)
        elif self.player.state is AudioState.PAUSE:
            if self.player.resume():
                self.configure(image=self.pause_image)
    
    def playing(self):
        while self.player.state in self.PLAYING_STATE:
            if self.playing_func is not None:
                self.playing_func(self.player.playback_position_sec)
            time.sleep(0.01)
        
        if self.player.state is AudioState.RELEASE:
            return
        
        # MEMO: これ以降のタイミングでRELEASEになると困る
        if self.play_end_func is not None:
            self.play_end_func()
        
        self.configure(image=self.play_image)
    
    def release(self):
        """スレッド終了待ち
        player.state RELEASE 前提
        """
        
        if self.playing_thread is not None:
            self.playing_thread.join()
        
        if self.play_thread is not None:
            self.play_thread.join()