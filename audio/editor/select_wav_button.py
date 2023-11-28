import tkinter as tk
from typing import Callable
from tkinter import filedialog


__all__ = [
    "SelectWavButton",
]


class SelectWavButton(tk.Button):
    def __init__(
        self,
        master:tk.Misc,
        state=tk.NORMAL,
        background:str="white",
        selected_command:Callable[[str],None]=None,
    ):
        # resource
        self.folder_image = tk.PhotoImage(data="iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAOBJREFUOE/dk00OwiAQhedxEm7R7qSuqpfQnqTxJOolDCuLu+ol5CQ8M/7Fn0ZM3DkJIQTexzDzgPwYUH3p6vkLJ/bBh1d26WqbRGYwxu63m0b3UYynSyEVEB8FJFeH4Bd3EeBERIeesyArvQRFNeFtcQOUrnYEliAXOqtIgUZk3Qcfi2rSCRA1ixzgnOan+ATocuJLDQae8I3w+szunwAEWm3bkIGGavJWg2u/BWTzDeQNkERGalGktOuDX+U68Qg4ChCY0pOVcwBcrG2hXqcxrZA2J3raByJSWp9/4y9xAqmOrbG+UPNvAAAAAElFTkSuQmCC")
        
        super().__init__(master, image=self.folder_image, relief=tk.FLAT, width=22, height=22, state=state, background=background, anchor=tk.CENTER, command=self.command)
        
        # variable
        self.path = ""
        
        # callback
        self.selected_func = selected_command
    
    def command(self):
        filetypes = [("WAV", "*.wav")]
        initialdir = self.path if self.path != "" else "./"
        path = filedialog.askopenfilename(filetypes=filetypes, initialdir=initialdir)
        
        if path == "":
            return
        
        self.path = path
        
        if self.selected_func is not None:
            self.selected_func(self.path)