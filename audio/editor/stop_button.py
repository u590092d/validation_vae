import tkinter as tk
from typing import Callable
import threading
from ..runtime import AudioState, AudioPlayer


__all__ = [
    "StopImageButton",
]


class StopImageButton(tk.Button):
    """停止ボタン

    Args:
        tk (_type_): _description_
    """
    
    PLAYING_STATE = (AudioState.PLAY, AudioState.PAUSE)
    
    def __init__(
        self,
        master:tk.Misc,
        player:AudioPlayer,
        state=tk.NORMAL,
        background:str="white",
        stopped_command:Callable[[],None]=None,
    ):
        # resource
        self.stop_image = tk.PhotoImage(data="iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAADNJREFUOE9jNHPwmM3IyJjCQAb4////HEZzR8//ZOiFaxk1gIFhNAxGwwCUIShPB5RmZwADkyNDim2IIQAAAABJRU5ErkJggg==")

        super().__init__(master, image=self.stop_image, relief=tk.FLAT, width=22, height=22, state=state, background=background, anchor=tk.CENTER, command=self.command)

        # variable
        self.stop_thread = None

        # instance
        self.player = player
        
        # callback
        self.stopped_func = stopped_command
        
    def command(self):
        if self.player.state in self.PLAYING_STATE:
            self.stop_thread = threading.Thread(target=self.stop)
            self.stop_thread.start()

    def stop(self):
        if self.player.state is AudioState.RELEASE:
            return
        
        if self.player.stop() and self.stopped_func is not None:
            self.stopped_func()

    def release(self):
        """スレッド終了待ち
        player.state RELEASE 前提
        """
        
        if self.stop_thread is not None:
            self.stop_thread.join()