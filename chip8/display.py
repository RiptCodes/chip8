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

    def draw(self, framebuffer, theme):
        _, bg, fg = theme
        self.screen.fill(bg)
        for y in range(32):
            for x in range(64):
                if framebuffer[y][x]:
                    pygame.draw.rect(self.screen, fg,
                                     (x * SCALE, y * SCALE, SCALE, SCALE))