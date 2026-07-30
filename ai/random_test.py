"""Random agent — proves the env loop works before any training."""
from chip8.env import Chip8Env
import random

env = Chip8Env("roms/Pong.ch8", actions=[set(), {0x1}, {0x4}], cycles_per_step=10)
obs = env.reset()
for i in range(600):
    obs, reward, done, info = env.step(random.randrange(env.n_actions))
    if i % 100 == 0:
        print(f"frame {i}, pixels on: {obs.sum()}")
print(env.render_ascii())