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
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv

from chip8.env import Chip8Env
from ai.pong_reward import find_positions

ROM = "roms/Pong-train.ch8"
GONE_FRAMES = 6      # ball must be missing this long to count as out of play


def _fold(y):
    # reflect a projected y off the top (0) and bottom (31) walls
    p = y % 62.0
    return p if p <= 31.0 else 62.0 - p


class PongGym(gym.Env):
    def __init__(self, opponent_model=None):
        super().__init__()
        self.env = Chip8Env(ROM, actions=[set(), {0x1}, {0x4}],
                            cycles_per_step=10, max_steps=3000)
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(5,), dtype=np.float32)
        # None = scripted right paddle; a model = same policy plays both sides
        self.opponent_model = opponent_model
        self._reset_tracking()

    def _reset_tracking(self):
        self.ball_x = None       # last known position, persisted through blinks
        self.ball_y = None
        self.ball_dx = 0.0
        self.ball_dy = 0.0
        self.intercept_y = None        # projected y at the left paddle's column
        self.intercept_right = None    # projected y at the right paddle's column
        self.right_y = None            # right paddle, persisted through blinks
        self.missing = 999

    def _track_ball(self, obs):
        """Update persistent ball state. Returns event reward (+5 hit, -5 concede)."""
        bx, by, _ = find_positions(obs)
        bonus = 0.0

        if bx is not None:
            if self.ball_x is not None and self.missing < GONE_FRAMES:
                # normalise by frames elapsed — a blink gap otherwise doubles
                # the measured velocity and throws the intercept off
                frames = self.missing + 1
                dx = (bx - self.ball_x) / frames
                dy = (by - self.ball_y) / frames
                # bounce off our paddle: direction flips near the left edge
                if self.ball_dx < 0 and dx > 0 and bx < 10:
                    bonus = 5.0
                if dx != 0:
                    self.ball_dx = dx
                if dy != 0:
                    self.ball_dy = dy
                # project where the ball will cross each paddle's column
                if self.ball_dx < 0:
                    t = (bx - 1.0) / -self.ball_dx
                    self.intercept_y = _fold(by + self.ball_dy * t)
                    self.intercept_right = None
                elif self.ball_dx > 0:
                    t = (62.0 - bx) / self.ball_dx
                    self.intercept_right = _fold(by + self.ball_dy * t)
                    self.intercept_y = None
            else:
                self.ball_dx = 0.0
                self.ball_dy = 0.0
                self.intercept_y = None
                self.intercept_right = None
            self.ball_x = bx
            self.ball_y = by
            self.missing = 0
        else:
            self.missing += 1
            if self.missing == GONE_FRAMES and self.ball_x is not None:
                # ball stayed gone: a point was scored on whichever side it exited
                if self.ball_dx < 0 and self.ball_x < 12:
                    bonus = -10.0
                elif self.ball_dx > 0 and self.ball_x > 52:
                    bonus = 5.0        # we beat the opponent
                self.ball_x = None
                self.ball_y = None
                self.intercept_y = None
                self.intercept_right = None

        # right paddle position, persisted through its redraw blinks
        rows = np.where(obs[:, 63] == 1)[0]
        if len(rows):
            self.right_y = rows.mean()
        return bonus

    def _features(self, obs):
        _, _, paddle_y = find_positions(obs)
        py = paddle_y / 32.0 if paddle_y is not None else -1.0
        if self.ball_x is None:
            return np.array([py, -1.0, -1.0, 0.0, 0.0], dtype=np.float32)
        dy = max(-1.0, min(1.0, self.ball_dy / 4.0))
        if self.intercept_y is not None and paddle_y is not None:
            # the answer feature: signed distance from paddle to intercept point
            delta = max(-1.0, min(1.0, (self.intercept_y - paddle_y) / 16.0))
        else:
            delta = 0.0
        return np.array([py, self.ball_x / 64.0, self.ball_y / 32.0, dy, delta],
                        dtype=np.float32)

    def _mirror_features(self, obs):
        # the right paddle's view of the game, x-axis flipped so the
        # left-trained policy applies unchanged
        ry = self.right_y / 32.0 if self.right_y is not None else -1.0
        if self.ball_x is None:
            return np.array([ry, -1.0, -1.0, 0.0, 0.0], dtype=np.float32)
        dy = max(-1.0, min(1.0, self.ball_dy / 4.0))
        if self.intercept_right is not None and self.right_y is not None:
            delta = max(-1.0, min(1.0, (self.intercept_right - self.right_y) / 16.0))
        else:
            delta = 0.0
        return np.array([ry, (63.0 - self.ball_x) / 64.0, self.ball_y / 32.0, dy, delta],
                        dtype=np.float32)

    def _opponent_keys(self, obs):
        # right paddle: either the trained model on mirrored features,
        # or the simple scripted ball-tracker (used during training)
        if self.opponent_model is not None:
            action, _ = self.opponent_model.predict(self._mirror_features(obs),
                                                    deterministic=True)
            return [set(), {0xC}, {0xD}][int(action)]
        rows = np.where(obs[:, 63] == 1)[0]
        if self.ball_y is None or not len(rows):
            return set()
        right_y = rows.mean()
        if right_y > self.ball_y + 0.5:
            return {0xC}
        if right_y < self.ball_y - 0.5:
            return {0xD}
        return set()

    def _shaped(self, obs):
        # shape toward the predicted intercept when the ball is incoming,
        # otherwise toward the ball itself
        _, _, paddle_y = find_positions(obs)
        if paddle_y is None:
            return 0.0
        target = self.intercept_y if self.intercept_y is not None else self.ball_y
        if target is None:
            return 0.0
        return 1.0 - abs(target - paddle_y) / 32.0

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
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 3_000_000
    env = make_vec_env(PongGym, n_envs=8, vec_env_cls=SubprocVecEnv)
    model = PPO("MlpPolicy", env, verbose=1,
                learning_rate=3e-4, n_steps=512, batch_size=1024,
                ent_coef=0.01,
                policy_kwargs={"net_arch": [128, 128]})
    model.learn(total_timesteps=steps)
    model.save("ai/pong_ppo")
    print("saved to ai/pong_ppo.zip")
