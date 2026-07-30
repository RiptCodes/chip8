# Attempting to make a chip 8 emulator with additional improvements and features without going over memory budget
"""CHIP-8 emulator"""
import sys
import pygame
import os

from chip8.cpu import Chip8
from chip8.audio import Beeper
from chip8.display import Renderer, THEMES, SCALE
from chip8.input import KEYMAP
from chip8.music import MusicPlayer
from chip8.intro import splash

CYCLES_PER_FRAME = 10
DEFAULT_ROM = "roms/Pong.ch8"


def main():
    # --- pygame setup ---
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
    pygame.init()
    screen = pygame.display.set_mode((64 * SCALE, 32 * SCALE))
    
    clock = pygame.time.Clock()

    # --- components ---
    chip = Chip8()
    chip.load_rom(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROM)
    beeper = Beeper()
    renderer = Renderer(screen)
    music = MusicPlayer(folder="music", volume=0.2)

    if not splash(screen, os.path.basename(chip.rom_path)):
        pygame.quit()
        sys.exit()

    # --- UI state (lives in main, not the CPU) ---
    theme_idx = 0
    paused = False

    pygame.display.set_caption(f"chip8 — {chip.rom_path}")

    running = True
    while running:
        # events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # wait-for-key resolution
                if chip.waiting_for_key and event.key in KEYMAP:
                    chip.V[chip.waiting_register] = KEYMAP[event.key]
                    chip.waiting_for_key = False
                # UI shortcuts
                if event.key == pygame.K_TAB:
                    theme_idx = (theme_idx + 1) % len(THEMES)
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_r:
                    chip.reset()
                    beeper.stop() if hasattr(beeper, "stop") else None
                elif event.key == pygame.K_LEFTBRACKET:
                    music.set_volume(music.volume - 0.1)
                elif event.key == pygame.K_RIGHTBRACKET:
                    music.set_volume(music.volume + 0.1)

        # feed current keypad state into the CPU
        keys = pygame.key.get_pressed()
        chip.keys = {c8 for pyk, c8 in KEYMAP.items() if keys[pyk]}

        # tick timers + step CPU
        chip.tick_timers()
        if not paused:
            for _ in range(CYCLES_PER_FRAME):
                if chip.waiting_for_key:
                    break
                chip.step()

        # audio + render
        music.update()
        beeper.update(chip.sound_timer)
        renderer.draw(chip.framebuffer, THEMES[theme_idx])

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()