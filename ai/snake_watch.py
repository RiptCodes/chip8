"""Watch the evolved agent play snake.ch8 in the emulator window."""
import numpy as np
import pygame

from ai.snake_env import SnakeEnv, HEADING_TO_ACTION
from ai.snake_evolve import forward
from chip8.display import Renderer, THEMES, SCALE


def main():
    genome = np.load("ai/snake_best.npy")
    env = SnakeEnv(max_moves=100000)

    pygame.init()
    screen = pygame.display.set_mode((64 * SCALE, 32 * SCALE))
    pygame.display.set_caption("chip8 — evolved agent playing snake.ch8")
    renderer = Renderer(screen)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Consolas", 16)

    state = env.reset()
    best = 0
    speed = 20
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_UP:
                    speed = min(240, speed + 10)
                elif e.key == pygame.K_DOWN:
                    speed = max(2, speed - 10)

        action = int(np.argmax(forward(genome, state)))
        state, _, done, info = env.step(action)
        best = max(best, env.best_life, info["length"])
        if done:
            state = env.reset()

        renderer.draw(env.env.chip.planes, THEMES[0], env.env.chip.high_res)
        label = font.render(f"len {info['length']}   best {best}   speed {speed}",
                            True, (140, 255, 170))
        screen.blit(label, (6, 4))
        pygame.display.flip()
        clock.tick(speed)

    pygame.quit()


if __name__ == "__main__":
    main()
