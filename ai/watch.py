"""Watch the trained agent play Pong in the real emulator window."""
import os

import pygame
from stable_baselines3 import DQN, PPO

from ai.train_pong import PongGym
from chip8.display import Renderer, THEMES, SCALE

if os.path.exists("ai/pong_ppo.zip"):
    model = PPO.load("ai/pong_ppo")
else:
    model = DQN.load("ai/pong_dqn")
env = PongGym()

pygame.init()
screen = pygame.display.set_mode((64 * SCALE, 32 * SCALE))
pygame.display.set_caption("chip8 — AI playing Pong")
renderer = Renderer(screen)
clock = pygame.time.Clock()

obs, _ = env.reset()
running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, _, _ = env.step(action)
    if done:
        obs, _ = env.reset()
    renderer.draw(env.env.chip.planes, THEMES[0], env.env.chip.high_res)
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
