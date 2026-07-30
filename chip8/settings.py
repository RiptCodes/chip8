import json
import os
from dataclasses import dataclass, asdict

SETTINGS_FILE = "settings.json"


@dataclass
class Settings:
    theme_idx: int = 0
    cycles_per_frame: int = 10
    music_volume: float = 0.3
    beep_volume: float = 0.2

    def save(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls):
        if not os.path.exists(SETTINGS_FILE):
            return cls()
        try:
            with open(SETTINGS_FILE) as f:
                return cls(**json.load(f))
        except Exception:
            return cls()