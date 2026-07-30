"""One small snake viewer window. Launched 20x by snake_watch_top.

Runs forever: the snake resets on death, the genome hot-reloads whenever
training saves a newer one, and the all-time high score is shared between
all windows through a small file.
"""
import os
import sys

import numpy as np

# window position must be set before pygame initialises
if len(sys.argv) >= 4:
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{sys.argv[2]},{sys.argv[3]}"

import pygame

from ai.snake_env import SnakeEnv
from ai.snake_evolve import forward

CELL = 6
LABEL_H = 22
HISCORE_FILE = "ai/top_snakes/highscore.txt"


def read_hiscore():
    try:
        with open(HISCORE_FILE) as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def write_hiscore(score):
    try:
        with open(HISCORE_FILE, "w") as f:
            f.write(str(score))
    except OSError:
        pass


def main():
    rank = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    path = f"ai/top_snakes/rank_{rank:02}.npy"
    genome = np.load(path)
    mtime = os.path.getmtime(path)

    pygame.init()
    w, h = 64 * CELL, 32 * CELL + LABEL_H
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption(f"snake #{rank + 1}")
    font = pygame.font.SysFont("Consolas", 13)
    clock = pygame.time.Clock()

    env = SnakeEnv(max_moves=1000000)
    state = env.reset()
    best = 0
    lives = 1
    frames = 0
    fresh = False        # true briefly after a genome reload

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                return

        # hot-reload when training saves a newer generation of this rank
        frames += 1
        if frames % 90 == 0:
            try:
                m = os.path.getmtime(path)
                if m > mtime:
                    genome = np.load(path)
                    mtime = m
                    fresh = True
            except OSError:
                pass

        action = int(np.argmax(forward(genome, state)))
        state, _, done, info = env.step(action)
        length = max(env.best_life, info["length"])
        best = max(best, length)
        hiscore = read_hiscore()
        if best > hiscore:
            write_hiscore(best)
            hiscore = best
        if done:
            state = env.reset()
            lives += 1
            fresh = False

        screen.fill((10, 12, 18))
        obs = env.env._obs()
        for y in range(32):
            row = obs[y]
            for x in range(64):
                if row[x]:
                    pygame.draw.rect(screen, (0, 255, 65),
                                     (x * CELL, LABEL_H + y * CELL, CELL, CELL))
        tag = " NEW GEN" if fresh else ""
        label = font.render(
            f"#{rank + 1} len {info['length']} best {best} top {hiscore} L{lives}{tag}",
            True, (150, 220, 160))
        screen.blit(label, (4, 4))
        pygame.display.flip()
        clock.tick(30)


if __name__ == "__main__":
    main()
