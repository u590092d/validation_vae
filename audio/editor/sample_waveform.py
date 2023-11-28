from pathlib import Path
import tkinter as tk
from typing import Union
import time
from scipy.io import wavfile
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import importlib
import time
import matplotlib.pyplot as plt
import torch
import IPython.display
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
from torch import optim
import torch.utils as utils
from torchvision import datasets, transforms
from sklearn.utils import resample
import librosa
import librosa.display
import soundfile
import os
import scipy.signal
import re
import sys
import keyboard
from PIL import Image
import threading
import time
import queue
import pyaudio
import sys
from .common_func import *
from sklearn.svm import SVC
from pydub import AudioSegment

import librosa
import librosa.display

from ..runtime import AudioPlayer, AudioState
from . import PlayImageButton, StopImageButton, PlaySpeedButton, SelectWavButton


__all__ = [
    "SampleWaveform",
]


class SampleWaveform(tk.Frame):



    """波形表示サンプル

    Args:
        tk (_type_): _description_
    """
    
    def __init__(
        self,
        master:tk.Misc=None,
    ):
        super().__init__(master)
        
        self.master.resizable(width=False, height=False)
        self.master.iconphoto(False, tk.PhotoImage(data="iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAS9JREFUOE+9U8FthDAQ9NoUQjrhfsimB0IlHJVw6QFb/I5UEgrBbDTIG5E7SJRP+ABaz+zszpjUHx5r7eu6rpPWug4hdIDSEd45d48xNuM4zlKvqqpg5l7+mbkLIdyeCMqyzI0xH8x8lS4ACQERNcxce++bQwXW2la6rOv6JioScc/MExEVovBJAeR77y/oCKJhGCa8MT8RYYSbUionog61LwIc2CQRtd77FxAIWBQ55/oYY5dlWS61jSDNd8f34+y/mbQRpPlAMEP+EQhn0Bm1ZVlm2c2hjWnmlogw1gbaP3uVpwRYJhQx8zvAWusZnY0xLTPPPwYJABDIpvfdxeb/J0iLRshyhOlUQbK0VkoViO0uSFjq9dHqwyQCnEJ1EYKd1ZPcg9O7kOz7dvAsUJ+yMdARidZbuQAAAABJRU5ErkJggg=="))
        self.master.title("validation_visualizer")
        
        self.player = AudioPlayer(48000, post_setup_command=self.post_setup)
        
        #
        # === controller ===
        #
        
        self.controller_frame = tk.Frame(self.master, bg="white")
        self.controller_frame.pack(fill=tk.BOTH)
        
        self.play_button = PlayImageButton(self.controller_frame, self.player, state=tk.DISABLED, play_end_command=self.clear_seekbar, playing_command=self.set_seekbar)
        self.play_button.grid(column=0, row=0, padx=(14,0), pady=(4,0), sticky=tk.NSEW)

        self.stop_button = StopImageButton(self.controller_frame, self.player, state=tk.DISABLED)
        self.stop_button.grid(column=1, row=0, padx=(0,0), pady=(4,0), sticky=tk.NSEW)

        self.wav_button = SelectWavButton(self.controller_frame, state=tk.DISABLED, selected_command=self.load)
        self.wav_button.grid(column=2, row=0, padx=(0,0), pady=(4,0), sticky=tk.NSEW)
        
        self.play_speed_button = PlaySpeedButton(self.controller_frame, self.player, tk.DISABLED)
        self.play_speed_button.grid(column=3, row=0, padx=(0,0), pady=(4,0), sticky=tk.NSEW)
        
        self.mouse_position_label = tk.Label(self.controller_frame,text="mouse_x:",font = ("MSゴシック","10","bold"))
        self.mouse_position_label.grid(column=4,row=0,sticky=tk.NSEW)

        #
        # === canvas ===
        #
        
        self.canvas_frame = tk.Frame(self.master)
        self.canvas_frame.pack(side=tk.LEFT)

        # figure
        self.fig = Figure(figsize=(12.8,4.8), dpi=100)
        self.fig.subplots_adjust(left=0.05, right=0.99, bottom=0.10, top=0.95)
        self.ax = self.fig.add_subplot()
        
        # hide axis
        #self.ax.xaxis.set_visible(False)
        #self.ax.yaxis.set_visible(False)
        
        # canvas
        self.canvas = FigureCanvasTkAgg(self.fig, self.canvas_frame)
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky=tk.NSEW)
        
        #
        # === visualizer ===
        #
        self.mouse_x = None
        self.mouse_y = None
    
        self.visualizer_frame =  tk.Frame(self.master)
        self.visualizer_frame.pack(side=tk.LEFT)
        
        #figure
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        backimage_path = os.path.join(cur_dir,"z.png")
        self.backgroud_image = Image.open(backimage_path)

        self.fig2 = Figure(figsize=(4.8,4.8))
        self.fig2.subplots_adjust(left=0.05, right=0.95, bottom=0.10, top=0.95)
        self.ax2 = self.fig2.add_subplot()
        self.ax2.set_xlim(-3,3)
        self.ax2.set_ylim(-3,3)

        self.ax2_xlim = self.ax2.get_xlim()
        self.ax2_ylim = self.ax2.get_ylim()
        # canvas
        self.visualizer_canvas = FigureCanvasTkAgg(self.fig2, self.visualizer_frame)
        self.visualizer_canvas.get_tk_widget().grid(column=0, row=0, sticky=tk.NSEW)

    def post_setup(self):
        if self.player.state is AudioState.RELEASE:
            return
        
        self.play_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.NORMAL)
        self.wav_button.configure(state=tk.NORMAL)
        self.play_speed_button.configure(state=tk.NORMAL)
    
    def load(self, path:Union[str,Path]):
        # 再生途中にロードするとスレッド解放されないので適当に対処
        if self.player.state is not AudioState.NONE:
            if self.player.stop():
                while self.player.state is not AudioState.NONE:
                    time.sleep(0.01)
            else:
                return
        
        # clear canvas
        self.ax.clear()
        self.ax2.clear()
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        # load
        #sr, x = wavfile.read(str(path))
        x = AudioSegment.from_wav(str(path))
        x = x.set_channels(1)
        path = os.path.join(cur_dir,"./output.wav")
        x.export(path,format="wav")

        origin_sr = librosa.get_samplerate(str(path))
        x,_ = librosa.load(str(path),sr=origin_sr)
        sr = 24000
        x = librosa.resample(x,orig_sr=origin_sr,target_sr=sr)
        
        soundfile.write(path,x,sr,'PCM_16')

        # wave plot
        librosa.display.waveshow(x, sr=sr, ax=self.ax, x_axis="s", lw=0.5, zorder=1)
        self.ax2.imshow(self.backgroud_image,extent=[*self.ax2_xlim,*self.ax2_ylim],aspect='auto',alpha=0.6)


        labeltoword = ["a","i","u","e","o"]
        color_map = ["red", "green", "blue", "darkorange", "purple"]
       

        share_data_params=np.loadtxt(os.path.join(cur_dir,"./share_data_params.csv"), delimiter=',')
        n_fft= share_data_params[1].astype(int)
        hop_length= share_data_params[2].astype(int)
        n_mels= share_data_params[3].astype(int)
        dataset_mean= share_data_params[4].astype(float)
        dataset_std= share_data_params[5].astype(float)
        x_size= share_data_params[6].astype(int)
        y_size= share_data_params[7].astype(int)
        self.frame_len = share_data_params[8].astype(int)
        device = torch.device("cuda")

        model_save_path = os.path.join(cur_dir,"./model_2dim.pth")
        model = VAE(x_dim=x_size*y_size, z_dim=2).to(device)
        model.load_state_dict(torch.load(model_save_path))

        model.eval()
        points=np.loadtxt(os.path.join(cur_dir,"./z_points.csv"), delimiter=',')
        label=np.loadtxt(os.path.join(cur_dir,"./z_labels.csv"), delimiter=',').astype(int)

        random_seed = 123
        algorithm = SVC(kernel='rbf', probability=True, random_state=random_seed)
        algorithm.fit(points,label)

        latent = slice_encode(sr,n_fft,hop_length,n_mels,self.frame_len,dataset_mean,dataset_std,model,device,input_data=x)
        for i in latent:
           i.predict(algorithm)
      
        latent_before_sorted = Points(latent)
        self.points = latent_before_sorted
        latent_sorted = latent_before_sorted.point_sort()

        # set xlim
        self.ax.set_xlim(-0.5, len(x)/sr)

        # set axis info 
        self.ax.set_xticks(np.arange(-0.5,len(x)/sr,step=0.5))
        self.ax.grid(axis="x")
        # set latent info
        for point in latent_sorted.points:
            self.ax.vlines(round((1/sr)*point.time_start,2),ymax=np.max(x),ymin=-np.max(x),colors=color_map[point.predicted_label])
        # save current canvas

        self.sr2 = sr
        self.canvas.draw()
        self.visualizer_canvas.draw()
        self.bg = self.canvas.copy_from_bbox(self.ax.bbox)
        self.bg2 = self.visualizer_canvas.copy_from_bbox(self.ax2.bbox)
        for point in latent_sorted.points:
            print("label:"+str(labeltoword[point.predicted_label])+" start:"+str(round((1/sr)*point.time_start,2))+" end:"+str(round((1/sr)*point.time_end,2)))
        # set play data
        self.fig.canvas.mpl_connect('motion_notify_event',self.mouse_move)
        self.fig.canvas.mpl_connect('button_press_event',self.click_mouse)
        self.play_button.set_path(path)
    def mouse_move(self,event):
        
        if not event.inaxes:
            return
        self.mouse_x, self.mouse_y = event.xdata, event.ydata
        if  (self.player.state is AudioState.NONE)or (self.player.state is AudioState.RECV):
            self.canvas.restore_region(self.bg)
            if self.mouse_x != None and self.mouse_y != None:
                mouse_cursor = self.ax.axvline(self.mouse_x, lw=0.5, zorder=2)
                self.ax.draw_artist(mouse_cursor)
                self.mouse_position_label["text"] = "mouse_x:"+str(self.mouse_x)+"s"
            self.canvas.blit(self.ax.bbox)

    def click_mouse(self,event):
        if (self.player.state != AudioState.NONE) and (self.player.state != AudioState.PLAY):
            self.player.playback_position = self.mouse_x

    def set_seekbar(self, sec:float):
        # clear canvas
        self.canvas.restore_region(self.bg)
        self.visualizer_canvas.restore_region(self.bg2)
        # seek bar
        seekbar_wav = self.ax.axvline(sec, lw=0.5, zorder=2)
        self.ax.draw_artist(seekbar_wav)
        if self.mouse_x != None and self.mouse_y != None:
            mouse_cursor = self.ax.axvline(self.mouse_x, lw=0.5, zorder=2)
            self.ax.draw_artist(mouse_cursor) 
            self.mouse_position_label["text"] = "mouse_x:"+str(self.mouse_x)+"s"
        
        num_sample = int(sec*float(self.sr2))
        quo = num_sample//self.frame_len - 1 
        rem = num_sample%self.frame_len
        
        point = None
        if (rem == 0)and( len(self.points.points) >= quo)and(num_sample < len(self.points.points)*self.frame_len):
            point = self.points.points[quo]
        elif len(self.points.points) >= (quo+1)and(num_sample < len(self.points.points)*self.frame_len):
            point = self.points.points[quo+1]
        
        if point != None:
            z = point.get_z()
            scatter_latent = self.ax2.scatter(z[0][0],z[0][1],c="pink", alpha=1, linewidths=2,edgecolors="red")
            self.ax2.draw_artist(scatter_latent)

        # blit canvas
        self.canvas.blit(self.ax.bbox)
        self.visualizer_canvas.blit(self.ax2.bbox)
    def clear_seekbar(self):
        # clear canvas
        self.canvas.restore_region(self.bg)
        self.visualizer_canvas.restore_region(self.bg2)
        # blit canvas
        self.canvas.blit(self.ax.bbox)
        self.visualizer_canvas.blit(self.ax2.bbox)

    def destroy(self):
        self.player.release()
        self.play_button.release()
        self.stop_button.release()
        self.play_speed_button.release()
        return super().destroy()