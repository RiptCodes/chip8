"""Main menu, ROM picker, and settings screen."""
import os
import pygame

from chip8.display import THEMES

TITLE_FONT = None
ITEM_FONT = None
HINT_FONT = None


def _init_fonts():
    global TITLE_FONT, ITEM_FONT, HINT_FONT
    if TITLE_FONT is None:
        TITLE_FONT = pygame.font.SysFont("Consolas", 40, bold=True)
        ITEM_FONT = pygame.font.SysFont("Consolas", 24)
        HINT_FONT = pygame.font.SysFont("Consolas", 14)


PROFILES = ["schip", "chip-8", "xo-chip"]

SETTING_ROWS = [
    ("Theme",          lambda s: s.theme_idx,        lambda s, v: setattr(s, "theme_idx", v % len(THEMES)),          1,   lambda s: THEMES[s.theme_idx][0]),
    ("Cycles / frame", lambda s: s.cycles_per_frame, lambda s, v: setattr(s, "cycles_per_frame", max(1, min(100, v))), 1,   lambda s: str(s.cycles_per_frame)),
    ("Music volume",   lambda s: s.music_volume,     lambda s, v: setattr(s, "music_volume", max(0.0, min(1.0, v))),  0.1, lambda s: f"{s.music_volume:.1f}"),
    ("Beep volume",    lambda s: s.beep_volume,      lambda s, v: setattr(s, "beep_volume", max(0.0, min(1.0, v))),   0.1, lambda s: f"{s.beep_volume:.1f}"),
    ("CRT effect",     lambda s: s.crt_enabled,      lambda s, v: setattr(s, "crt_enabled", bool(v)),                1,   lambda s: "on" if s.crt_enabled else "off"),
    ("Quirks",         lambda s: PROFILES.index(s.quirks_profile) if s.quirks_profile in PROFILES else 0, lambda s, v: setattr(s, "quirks_profile", PROFILES[v % len(PROFILES)]), 1, lambda s: s.quirks_profile),
]


def scan_roms(folder="roms"):
    if not os.path.isdir(folder):
        return []
    return sorted(
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.lower().endswith(".ch8")
    )


def _draw_list(screen, title, entries, selected, hint, theme):
    _, bg, fg = theme
    dim = tuple(c * 4 // 10 for c in fg)      # 40% of foreground = dim

    screen.fill(bg)
    title_surf = TITLE_FONT.render(title, True, fg)
    screen.blit(title_surf, (screen.get_width() // 2 - title_surf.get_width() // 2, 40))

    # fit as many rows as the space between title and hint allows, scroll around selection
    y = 100
    step = 28
    visible = max(1, (screen.get_height() - 40 - y) // step)
    start = max(0, min(len(entries) - visible, selected - visible // 2))
    for i in range(start, min(len(entries), start + visible)):
        color = fg if i == selected else dim
        prefix = "> " if i == selected else "  "
        surf = ITEM_FONT.render(prefix + entries[i], True, color)
        screen.blit(surf, (screen.get_width() // 2 - 120, y))
        y += step

    # scroll arrows when the list continues off-screen
    if start > 0:
        up = HINT_FONT.render("...", True, dim)
        screen.blit(up, (screen.get_width() // 2 - up.get_width() // 2, 86))
    if start + visible < len(entries):
        down = HINT_FONT.render("...", True, dim)
        screen.blit(down, (screen.get_width() // 2 - down.get_width() // 2,
                           screen.get_height() - 42))

    hint_surf = HINT_FONT.render(hint, True, dim)
    screen.blit(hint_surf, (screen.get_width() // 2 - hint_surf.get_width() // 2,
                             screen.get_height() - 28))
    pygame.display.flip()


def run_main_menu(screen, settings):
    _init_fonts()
    entries = ["Play", "Settings", "Quit"]
    selected = 0
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(entries)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(entries)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if entries[selected] == "Play":     return "PLAY"
                    if entries[selected] == "Settings": return "SETTINGS"
                    if entries[selected] == "Quit":     return None

        _draw_list(screen, "CHIP-8", entries, selected,
                   "up/down select   enter open   esc quit",
                   THEMES[settings.theme_idx])
        clock.tick(30)


def run_rom_picker(screen, roms, settings):
    _init_fonts()
    entries = [os.path.basename(r) for r in roms] + ["Back"]
    selected = 0
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(entries)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(entries)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected == len(entries) - 1:   # Back
                        return None
                    return roms[selected]

        _draw_list(screen, "SELECT GAME", entries, selected,
                   "up/down select   enter play   esc back",
                   THEMES[settings.theme_idx])
        clock.tick(30)


def run_settings(screen, settings, beeper, music):
    """Returns True on save+back, False on window close."""
    _init_fonts()
    selected = 0
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    settings.save()
                    beeper.sound.set_volume(settings.beep_volume)
                    music.set_volume(settings.music_volume)
                    return True
                elif event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(SETTING_ROWS)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(SETTING_ROWS)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    _, getter, setter, delta, _ = SETTING_ROWS[selected]
                    setter(settings, getter(settings) - delta)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    _, getter, setter, delta, _ = SETTING_ROWS[selected]
                    setter(settings, getter(settings) + delta)

        _, bg, fg = THEMES[settings.theme_idx]
        dim = tuple(c * 4 // 10 for c in fg)

        screen.fill(bg)
        title = TITLE_FONT.render("SETTINGS", True, fg)
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 30))

        y = 90
        step = 28
        visible = max(1, (screen.get_height() - 40 - y) // step)
        start = max(0, min(len(SETTING_ROWS) - visible, selected - visible // 2))
        for i in range(start, min(len(SETTING_ROWS), start + visible)):
            label, _, _, _, fmt = SETTING_ROWS[i]
            color = fg if i == selected else dim
            prefix = "> " if i == selected else "  "
            value = "< {} >".format(fmt(settings)) if i == selected else fmt(settings)
            row = f"{prefix}{label:<16} {value}"
            surf = ITEM_FONT.render(row, True, color)
            screen.blit(surf, (screen.get_width() // 2 - 200, y))
            y += step

        hint = HINT_FONT.render("up/down select   left/right change   enter save & back",
                                 True, dim)
        screen.blit(hint, (screen.get_width() // 2 - hint.get_width() // 2,
                            screen.get_height() - 28))
        pygame.display.flip()
        clock.tick(30)