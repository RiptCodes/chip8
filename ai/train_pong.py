"""Train a DQN to play Pong on the chip8 emulator.

The agent controls the left paddle (keys 1/4). A scripted opponent moves the
right paddle (keys C/D) so rallies actually happen. Observations are compact
features: [paddle_y, ball_x, ball_y, ball_dy].

Pong erases the ball by XOR-redrawing it every game loop, so screen samples
often catch the ball mid-blink. Ball state is therefore tracked with
persistence: the last seen position survives short gaps, and the ball only
counts as gone after several consecutive missing frames.

Run:  python -m ai.train_pong            (full 500k-step run)
      python -m ai.train_pong 5000       (short run, any step count)
"""
import sys

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3 import DQN

from chip8.env import Chip8Env
from ai.pong_reward import find_positions

ROM = "roms/Pong-train.ch8"
GONE_FRAMES = 6      # ball must be missing this long to count as out of play


class PongGym(gym.Env):
    def __init__(self):
        super().__init__()
        self.env = Chip8Env(ROM, actions=[set(), {0x1}, {0x4}],
                            cycles_per_step=10, max_steps=3000)
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(4,), dtype=np.float32)
        self._reset_tracking()

    def _reset_tracking(self):
        self.ball_x = None       # last known position, persisted through blinks
        self.ball_y = None
        self.ball_dx = 0.0
        self.ball_dy = 0.0
        self.missing = 999

    def _track_ball(self, obs):
        """Update persistent ball state. Returns event reward (+5 hit, -5 concede)."""
        bx, by, _ = find_positions(obs)
        bonus = 0.0

        if bx is not None:
            if self.ball_x is not None and self.missing < GONE_FRAMES:
                dx = bx - self.ball_x
                dy = by - self.ball_y
                # bounce off our paddle: direction flips near the left edge
                if self.ball_dx < 0 and dx > 0 and bx < 10:
                    bonus = 5.0
                if dx != 0:
                    self.ball_dx = dx
                if dy != 0:
                    self.ball_dy = dy
            else:
                self.ball_dx = 0.0
                self.ball_dy = 0.0
            self.ball_x = bx
            self.ball_y = by
            self.missing = 0
        else:
            self.missing += 1
            if self.missing == GONE_FRAMES and self.ball_x is not None:
                # ball stayed gone: a point was scored on whichever side it exited
                if self.ball_dx < 0 and self.ball_x < 12:
                    bonus = -5.0
                self.ball_x = None
                self.ball_y = None
        return bonus

    def _features(self, obs):
        _, _, paddle_y = find_positions(obs)
        py = paddle_y / 32.0 if paddle_y is not None else -1.0
        if self.ball_x is None:
            return np.array([py, -1.0, -1.0, 0.0], dtype=np.float32)
        dy = max(-1.0, min(1.0, self.ball_dy / 4.0))
        return np.array([py, self.ball_x / 64.0, self.ball_y / 32.0, dy],
                        dtype=np.float32)

    def _opponent_keys(self, obs):
        # scripted right paddle: track the ball with keys C (up) / D (down)
        rows = np.where(obs[:, 63] == 1)[0]
        if self.ball_y is None or not len(rows):
            return set()
        right_y = rows.mean()
        if right_y > self.ball_y + 1:
            return {0xC}
        if right_y < self.ball_y - 1:
            return {0xD}
        return set()

    def _shaped(self, obs):
        _, _, paddle_y = find_positions(obs)
        if self.ball_y is None or paddle_y is None:
            return 0.0
        return 1.0 - abs(self.ball_y - paddle_y) / 32.0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        obs = self.env.reset()
        self._reset_tracking()
        return self._features(obs), {}

    def step(self, action):
        agent_keys = self.env.actions[int(action)]
        opp_keys = self._opponent_keys(self.env._obs())
        self.env.chip.keys = set(agent_keys) | opp_keys

        for _ in range(self.env.cycles_per_step):
            if self.env.chip.waiting_for_key:
                if self.env.chip.keys:
                    self.env.chip.V[self.env.chip.waiting_register] = next(iter(self.env.chip.keys))
                    self.env.chip.waiting_for_key = False
                else:
                    break
            self.env.chip.step()
        self.env.chip.tick_timers()
        self.env.steps += 1

        obs = self.env._obs()
        event = self._track_ball(obs)
        reward = self._shaped(obs) * 0.2 + event
        done = self.env.steps >= self.env.max_steps
        return self._features(obs), reward, done, False, {"steps": self.env.steps}


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 500_000
    env = PongGym()
    model = DQN("MlpPolicy", env, verbose=1,
                learning_rate=1e-3, buffer_size=50_000,
                exploration_fraction=0.3)
    model.learn(total_timesteps=steps)
    model.save("ai/pong_dqn")
    print("saved to ai/pong_dqn.zip")
