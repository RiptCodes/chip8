"""Gym-style RL environment wrapping the Chip8 CPU.

Runs headless (no pygame). One env step = one emulated frame:
a batch of CPU cycles with a chosen key held, then a timer tick.

Example:

    from chip8.env import Chip8Env

    def pong_reward(chip, prev):
        # reward = our score going up, penalty = opponent scoring.
        # find the score addresses by watching chip.I during Fx33 calls.
        return 0.0

    env = Chip8Env("roms/Pong.ch8", actions=[set(), {0x1}, {0x4}],
                   reward_fn=pong_reward)
    obs = env.reset()
    obs, reward, done, info = env.step(1)   # hold key 1 for one frame
"""
import numpy as np

from chip8.cpu import Chip8


class Chip8Env:
    def __init__(self, rom_path, actions=None, cycles_per_step=10,
                 max_steps=10000, reward_fn=None, done_fn=None,
                 profile="chip-8"):
        self.rom_path = rom_path
        # default action space: do nothing, or hold any single key
        self.actions = actions if actions is not None else [set()] + [{k} for k in range(16)]
        self.cycles_per_step = cycles_per_step
        self.max_steps = max_steps
        self.reward_fn = reward_fn
        self.done_fn = done_fn
        self.profile = profile
        self.chip = None
        self.steps = 0

    @property
    def n_actions(self):
        return len(self.actions)

    def reset(self):
        self.chip = Chip8(self.profile)
        self.chip.load_rom(self.rom_path)
        self.steps = 0
        return self._obs()

    def step(self, action_idx):
        prev = self._snapshot()
        self.chip.keys = set(self.actions[action_idx])

        for _ in range(self.cycles_per_step):
            if self.chip.waiting_for_key:
                # feed the held key straight in so Fx0A never stalls training
                if self.chip.keys:
                    self.chip.V[self.chip.waiting_register] = next(iter(self.chip.keys))
                    self.chip.waiting_for_key = False
                else:
                    break
            self.chip.step()
        self.chip.tick_timers()

        self.steps += 1
        obs = self._obs()
        reward = self.reward_fn(self.chip, prev) if self.reward_fn else 0.0
        done = self.steps >= self.max_steps
        if self.done_fn:
            done = done or self.done_fn(self.chip)
        return obs, reward, done, {"steps": self.steps}

    def _obs(self):
        # binary screen as a (32, 64) or (64, 128) uint8 array
        h, w = (64, 128) if self.chip.high_res else (32, 64)
        fb = self.chip.framebuffer
        return np.array([row[:w] for row in fb[:h]], dtype=np.uint8)

    def _snapshot(self):
        # cheap copy of the bits a reward function usually needs
        return {
            "V": bytes(self.chip.V),
            "memory": bytes(self.chip.memory[0x200:0x300]),
            "score_area": bytes(self.chip.memory[self.chip.I:self.chip.I + 3]),
        }

    def render_ascii(self):
        # quick debug view in the terminal
        h, w = (64, 128) if self.chip.high_res else (32, 64)
        fb = self.chip.framebuffer
        lines = []
        for y in range(h):
            lines.append("".join("#" if fb[y][x] else "." for x in range(w)))
        return "\n".join(lines)
