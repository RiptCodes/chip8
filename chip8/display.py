import pygame

SCALE = 10

THEMES = [
    ("phosphor", (0, 0, 0),      (0, 255, 65)),
    ("amber",    (0, 0, 0),      (255, 176, 0)),
    ("gameboy",  (155, 188, 15), (15, 56, 15)),
    ("ibm",      (30, 30, 60),   (200, 220, 255)),
]


class Renderer:
    def __init__(self, screen):
        self.screen = screen

    def draw(self, framebuffer, theme, high_res):
        _, bg, fg = theme
        if high_res:
            scale = SCALE // 2
            logical_w, logical_h = 128, 64
        else:
            scale = SCALE
            logical_w, logical_h = 64, 32

        self.screen.fill(bg)
        for y in range(logical_h):
            row = framebuffer[y]
            for x in range(logical_w):
                if row[x]:
                    pygame.draw.rect(self.screen, fg,
                                     (x * scale, y * scale, scale, scale))