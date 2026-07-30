import pygame

def splash(screen, rom_name, duration_ms=2500):
    font_big = pygame.font.SysFont("Consolas", 48, bold=True)
    font_small = pygame.font.SysFont("Consolas", 20)
    title = "RIPT'S CHIP8 EMULATOR"
    subtitle = f"loading {rom_name}..."
    start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start < duration_ms:
        elapsed = pygame.time.get_ticks() - start
        # Type the title one char at a time over the first 1500ms
        n_chars = min(len(title), elapsed * len(title) // 1500)
        shown = title[:n_chars]
        screen.fill((0, 0, 0))
        title_surf = font_big.render(shown, True, (0, 255, 65))
        sub_surf = font_small.render(subtitle, True, (0, 180, 45))
        w, h = screen.get_size()
        screen.blit(title_surf, (w // 2 - title_surf.get_width() // 2, h // 2 - 40))
        screen.blit(sub_surf, (w // 2 - sub_surf.get_width() // 2, h // 2 + 20))
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.KEYDOWN:
                return True   
        pygame.time.wait(16)
    return True