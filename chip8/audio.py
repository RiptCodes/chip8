import pygame
import numpy as np


class Beeper:
    def __init__(self, freq=440, sample_rate=22050, amplitude=4000):
        n = int(sample_rate * 1.0)
        t = np.arange(n)
        wave = (amplitude * np.sign(np.sin(2 * np.pi * freq * t / sample_rate))).astype(np.int16)
        wave = np.column_stack([wave, wave])
        self.sound = pygame.sndarray.make_sound(wave)
        self.sound.set_volume(0.2)
        self.playing = False

    def update(self, sound_timer):
        if sound_timer > 0 and not self.playing:
            self.sound.play(loops=-1); self.playing = True
        elif sound_timer == 0 and self.playing:
            self.sound.stop(); self.playing = False