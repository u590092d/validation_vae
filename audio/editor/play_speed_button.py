import tkinter as tk
import threading
import time
from functools import partial
from ..runtime import AudioState, AudioPlayer


__all__ = [
    "PlaySpeedButton",
]


class PlaySpeedButton(tk.Button):
    def __init__(
        self,
        master:tk.Misc,
        player:AudioPlayer,
        state=tk.NORMAL,
        background:str="white",
        current:float=1.0,
        steps:list[float]=[0.25,0.5,0.75,1.0,1.25,1.5,1.75],
        digits:list[int]=[2,1,2,0,2,1,2],
    ):
        # resource
        self.play_speed_image = tk.PhotoImage(data="iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAALdJREFUOE/Fk8ENwyAMRe1NMkp6Q4IdKjYpmzAEsnJrRmERyxVRHBFKFKkcypFvP3/bgDB4cDAfxgHGmKm4WJYl99zc6WitFQDIIhKIKLYQa+0bACYRiUQUWl0Ber8ys6/d7IB5DyiFTqAWoKDIzKGAGoDqmZkfRb8CbIEi4hHxCQDqoO5gczMCKAVev7ZwzOpriIgYUkqreu0M8bStY42I6OvEFlDsdtfonJt7iQq408ef8t8/0wd1QYfLTf/uUwAAAABJRU5ErkJggg==")

        super().__init__(master, compound=tk.CENTER, image=self.play_speed_image, command=lambda:self.menu.post(self.winfo_rootx(), self.winfo_rooty()), relief=tk.FLAT, width=22, height=22, state=state, background=background)
        
        # instance
        self.player = player
        
        # variable
        self.set_rate_thread = None
        
        self.menu = tk.Menu(self, tearoff=0)
        for step, digit in zip(steps, digits):
            label = "\n"
            if digit == 0:
                label += f"{int(step)}"
            elif digit == 1:
                label += f"{step:.1f}"
            elif digit == 2:
                label += f"{step:.2f}"
            label += "x"
            if current == step:
                self.rate = current
                self.text = label
                self.configure(text=self.text)
            self.menu.add_command(label=label, command=partial(self.command, step, label))
    
    def command(self, rate:float, text:str):
        if self.player.state is AudioState.RELEASE:
            return
        
        self.rate = rate
        self.text = text
        
        self.configure(text=self.text)
        
        if self.player.state is AudioState.NONE:
            self.set_rate()
        elif self.set_rate_thread is None or not self.set_rate_thread.is_alive():
            self.set_rate_thread = threading.Thread(target=self.set_rate)
            self.set_rate_thread.start()
    
    def set_rate(self):
        while self.player.state not in [AudioState.NONE, AudioState.RELEASE]:
            time.sleep(0.01)
        
        if self.player.state is AudioState.RELEASE:
            return
        
        self.player.rate = self.rate
    
    def release(self):
        if self.set_rate_thread is not None:
            self.set_rate_thread.join()