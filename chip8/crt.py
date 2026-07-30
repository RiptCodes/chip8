""" CRT effect overlay"""
import pygame

class CRT:
    def __init__(self, width, height, scanline_alpha=70, vignette_strength=140):
        self.width = width
        self.height = height
        self.scanlines = self._build_scanlines(scanline_alpha)
        self.vignette = self._build_vignette(vignette_strength)

    def apply(self, screen):
        """Blit both overlays onto the screen surface."""
        screen.blit(self.scanlines, (0, 0))
        screen.blit(self.vignette, (0, 0))

    def _build_scanlines(self, alpha):
        """Horizontal dark lines every 3 pixels."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(0, self.height, 3):
            pygame.draw.line(surf, (0, 0, 0, alpha), (0, y), (self.width, y))
        return surf

    def _build_vignette(self, strength):
        """Radial darkening — corners get dimmer than centre."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        cx, cy = self.width // 2, self.height // 2
        max_dist = ((cx ** 2 + cy ** 2) ** 0.5)
        for y in range(0, self.height, 2):
            for x in range(0, self.width, 2):
                dx, dy = x - cx, y - cy
                dist = (dx * dx + dy * dy) ** 0.5
                a = int(strength * (dist / max_dist) ** 2)
                pygame.draw.rect(surf, (0, 0, 0, min(255, a)), (x, y, 2, 2))
        return surf