import pygame

SCALE = 10

THEMES = [
    ("phosphor", (0, 0, 0),      (0, 255, 65)),
    ("amber",    (0, 0, 0),      (255, 176, 0)),
    ("gameboy",  (155, 188, 15), (15, 56, 15)),
    ("ibm",      (30, 30, 60),   (200, 220, 255)),
]


def _palette(bg, fg):
    # 4 colours for xo-chip's two planes: bg, fg, and two blends
    mid = tuple((a + b) // 2 for a, b in zip(bg, fg))
    dark = tuple((a + b * 2) // 3 for a, b in zip(fg, bg))
    return [bg, fg, mid, dark]


class Renderer:
    def __init__(self, screen):
        self.screen = screen

    def draw(self, planes, theme, high_res):
        _, bg, fg = theme
        palette = _palette(bg, fg)
        if high_res:
            scale = SCALE // 2
            logical_w, logical_h = 128, 64
        else:
            scale = SCALE
            logical_w, logical_h = 64, 32

        p0, p1 = planes
        self.screen.fill(bg)
        for y in range(logical_h):
            row0 = p0[y]
            row1 = p1[y]
            for x in range(logical_w):
                color_idx = row0[x] | (row1[x] << 1)
                if color_idx:
                    pygame.draw.rect(self.screen, palette[color_idx],
                                     (x * scale, y * scale, scale, scale))
