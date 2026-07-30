"""CHIP-8 emulator — frontend with menu → game state machine."""
import sys
import os
import pygame

from chip8.cpu import Chip8
from chip8.audio import Beeper
from chip8.display import Renderer, THEMES, SCALE
from chip8.input import KEYMAP
from chip8.music import MusicPlayer
from chip8.intro import splash
from chip8.menu import scan_roms, run_main_menu, run_rom_picker, run_settings
from chip8.settings import Settings


def run_game(chip, screen, beeper, renderer, music, settings):
    """Run one ROM. Returns True to go back to menu, False to quit entirely."""
    paused = False
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True   # back to menu
                if chip.waiting_for_key and event.key in KEYMAP:
                    chip.V[chip.waiting_register] = KEYMAP[event.key]
                    chip.waiting_for_key = False
                if event.key == pygame.K_TAB:
                    settings.theme_idx = (settings.theme_idx + 1) % len(THEMES)
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_r:
                    chip.reset()
                    if hasattr(beeper, "stop"):
                        beeper.stop()
                elif event.key == pygame.K_m:
                    music.toggle()
                elif event.key == pygame.K_n:
                    music.next()
                elif event.key == pygame.K_LEFTBRACKET:
                    settings.music_volume = max(0.0, settings.music_volume - 0.1)
                    music.set_volume(settings.music_volume)
                elif event.key == pygame.K_RIGHTBRACKET:
                    settings.music_volume = min(1.0, settings.music_volume + 0.1)
                    music.set_volume(settings.music_volume)

        # feed current keypad state into the CPU
        keys = pygame.key.get_pressed()
        chip.keys = {c8 for pyk, c8 in KEYMAP.items() if keys[pyk]}

        # tick timers + step CPU
        chip.tick_timers()
        if not paused:
            for _ in range(settings.cycles_per_frame):
                if chip.waiting_for_key:
                    break
                chip.step()

        # audio + render
        music.update()
        beeper.update(chip.sound_timer)
        renderer.draw(chip.framebuffer, THEMES[settings.theme_idx])

        pygame.display.flip()
        clock.tick(60)


def main():
    # --- pygame setup ---
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
    pygame.init()
    screen = pygame.display.set_mode((64 * SCALE, 32 * SCALE))

    # --- settings + shared components ---
    settings = Settings.load()
    beeper = Beeper()
    beeper.sound.set_volume(settings.beep_volume)
    renderer = Renderer(screen)
    music = MusicPlayer(folder="music", volume=settings.music_volume)

    roms = scan_roms("roms")
    if not roms:
        print("No ROMs found in roms/ folder.")
        pygame.quit()
        sys.exit(1)

    # --- optional shortcut: python main.py roms/pong.ch8 → skip menu ---
    if len(sys.argv) > 1:
        chip = Chip8()
        chip.load_rom(sys.argv[1])
        splash(screen, os.path.basename(chip.rom_path))
        pygame.display.set_caption(f"chip8 — {os.path.basename(chip.rom_path)}")
        run_game(chip, screen, beeper, renderer, music, settings)
        settings.save()
        pygame.quit()
        return

    # --- splash once at startup ---
    if not splash(screen, "menu"):
        pygame.quit()
        return

    # --- menu ↔ settings ↔ game state machine ---
    while True:
        choice = run_main_menu(screen, settings)

        if choice is None:
            break

        if choice == "SETTINGS":
            run_settings(screen, settings, beeper, music)
            continue

        if choice == "PLAY":
            rom_path = run_rom_picker(screen, roms, settings)
            if rom_path is None:
                continue
            chip = Chip8()
            chip.load_rom(rom_path)
            pygame.display.set_caption(f"chip8 — {os.path.basename(rom_path)}")
            if hasattr(beeper, "stop"):
                beeper.stop()
            if not run_game(chip, screen, beeper, renderer, music, settings):
                break

    settings.save()
    pygame.quit()


if __name__ == "__main__":
    main()