import os
import pygame


class MusicPlayer:
    def __init__(self, folder="music", volume=0.4):
        self.tracks = sorted(
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith((".mp3", ".ogg", ".wav"))
        ) if os.path.isdir(folder) else []
        self.idx = 0
        self.enabled = bool(self.tracks)
        self.volume = volume
        if self.enabled:
            pygame.mixer.music.set_volume(volume)
            self._load_current()
            pygame.mixer.music.play()

    def _load_current(self):
        pygame.mixer.music.load(self.tracks[self.idx])

    def next(self):
        if not self.enabled: return
        self.idx = (self.idx + 1) % len(self.tracks)
        self._load_current()
        pygame.mixer.music.play()

    def toggle(self):
        if not self.enabled: return
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, v))
        pygame.mixer.music.set_volume(self.volume)

    def update(self):
        """Auto-advance when current track ends."""
        if self.enabled and not pygame.mixer.music.get_busy():
            self.next()