"""RL environment for the snake.ch8 ROM running on the emulator.

The agent plays the real game through the real emulator, reading state out
of the 64x32 framebuffer the same way a person reads the screen.

Two things the screen makes awkward, both handled here:
  - the ROM XOR-redraws sprites, so pixels blink; food and body are tracked
    with persistence rather than trusted frame by frame
  - one game move takes ~50 cpu cycles, so a step is sized to match and the
    agent acts once per move instead of five times
"""
from collections import deque

import numpy as np

from chip8.env import Chip8Env

ROM = "roms/snake.ch8"
KEY_UP, KEY_LEFT, KEY_DOWN, KEY_RIGHT = 0x5, 0x7, 0x8, 0x9
ACTIONS = [set(), {KEY_UP}, {KEY_LEFT}, {KEY_DOWN}, {KEY_RIGHT}]

# absolute headings, clockwise, matching the action indices above
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
HEADING_TO_ACTION = {UP: 1, LEFT: 2, DOWN: 3, RIGHT: 4}
STEP = {UP: (-1, 0), RIGHT: (0, 1), DOWN: (1, 0), LEFT: (0, -1)}
CYCLES_PER_MOVE = 50
BOOT_STEPS = 80
H, W = 32, 64


def _neighbours(cell):
    y, x = cell
    yield (y - 1) % H, x
    yield (y + 1) % H, x
    yield y, (x - 1) % W
    yield y, (x + 1) % W


def clusters(points):
    """Split lit pixels into connected blobs, wrapping at the screen edges."""
    left = set(points)
    out = []
    while left:
        seed = left.pop()
        blob = {seed}
        frontier = [seed]
        while frontier:
            for n in _neighbours(frontier.pop()):
                if n in left:
                    left.remove(n)
                    blob.add(n)
                    frontier.append(n)
        out.append(blob)
    return out


class SnakeEnv:
    def __init__(self, max_moves=800):
        self.env = Chip8Env(ROM, actions=ACTIONS, cycles_per_step=CYCLES_PER_MOVE)
        self.max_moves = max_moves

    def reset(self):
        # step() halves cycles_per_step for mid-move sampling; put it back
        # or every boot after the first runs at half speed and never
        # clears the title screen
        self.env.cycles_per_step = CYCLES_PER_MOVE
        self.env.reset()
        for _ in range(BOOT_STEPS):
            self.env.step(1)          # any key clears the title screen
        self.body = set()
        self.head = None
        self.food = None
        self.food_age = 99
        self.length = 0
        self.moves = 0
        self.stale = 0
        self.best_life = 0
        self.game_over = False
        self.victory = False
        self.heading = UP
        self._len_hist = deque(maxlen=4)
        self._read()
        return self.features()

    def _read(self, extra=None):
        obs = self.env._obs()
        pts = set(tuple(p) for p in np.argwhere(obs))
        if extra is not None:
            pts |= extra
        pts = list(pts)
        # victory screen = a solid fill, far more pixels than any snake can be
        self.victory = len(pts) > 1500
        if self.victory:
            return
        blobs = clusters(pts)
        if not blobs:
            return
        # in play the screen is one body blob plus a food pixel; the game-over
        # screen is text, which fragments into many letter blobs. counting
        # blobs tells them apart no matter how long the snake gets
        self.game_over = len(blobs) >= 8
        if self.game_over:
            return
        blobs.sort(key=len, reverse=True)
        body = blobs[0]

        # a lone pixel well away from the body is food; it blinks, so the
        # last sighting is kept until a new one shows up
        loose = [b for b in blobs[1:] if len(b) == 1]
        if loose:
            self.food = next(iter(loose[0]))
            self.food_age = 0
        else:
            self.food_age += 1

        new = body - self.body
        if new:
            head = min(new)
            if self.head:
                dy = ((head[0] - self.head[0] + H // 2) % H) - H // 2
                dx = ((head[1] - self.head[1] + W // 2) % W) - W // 2
                if dy or dx:
                    self.heading = (UP if dy < 0 else DOWN) if abs(dy) >= abs(dx) \
                        else (LEFT if dx < 0 else RIGHT)
            self.head = head
        elif self.head is None:
            self.head = min(body)
        self.body = body
        self._len_hist.append(len(body))
        self.length = max(self._len_hist)

    def step(self, action):
        """action: 0 straight, 1 turn left, 2 turn right."""
        prev_len = self.length
        prev_head = self.head

        if action == 1:
            self.heading = (self.heading - 1) % 4
        elif action == 2:
            self.heading = (self.heading + 1) % 4

        # split the move in two so the body can be sampled either side of a
        # redraw and unioned; a single sample lies about the length
        self.env.cycles_per_step = CYCLES_PER_MOVE // 2
        self.env.step(HEADING_TO_ACTION[self.heading])
        mid = set(tuple(p) for p in np.argwhere(self.env._obs()))
        self.env.step(HEADING_TO_ACTION[self.heading])
        self._read(extra=mid)
        self.moves += 1

        if self.victory:
            return self.features(), 200.0, True, {"length": prev_len, "died": False, "won": True}

        died = self.game_over or (prev_len > 7 and self.length <= prev_len - 3)
        if died:
            return self.features(), -10.0, True, {"length": prev_len, "died": True, "won": False}

        grew = self.length > prev_len
        reward = 5.0 if grew else 0.0
        if grew:
            self.best_life = max(self.best_life, self.length)
            self.stale = 0
            # the eaten apple is gone; its replacement may have spawned
            # against the body where the cluster detector cannot see it yet.
            # chasing the old position is chasing a ghost
            self.food = None
            self.food_age = 99
        else:
            self.stale += 1
            # closing on the food is worth a little, drifting away costs a little
            if self.head and self.food and prev_head:
                before = self._dist(prev_head, self.food)
                after = self._dist(self.head, self.food)
                reward += 0.1 if after < before else -0.1

        done = self.moves >= self.max_moves or self.stale > 100
        return self.features(), reward, done, {"length": self.length, "died": False, "won": False}

    @staticmethod
    def _dist(a, b):
        dy = min(abs(a[0] - b[0]), H - abs(a[0] - b[0]))
        dx = min(abs(a[1] - b[1]), W - abs(a[1] - b[1]))
        return dy + dx

    def features(self):
        """v2 senses: 8 body-distance rays in the snake's frame, plus the food
        offset cyclically encoded (sin/cos) so nothing jumps at the wrap seam."""
        if not self.head:
            return np.zeros(14, dtype=np.float32)
        hy, hx = self.head
        food_known = self.food is not None
        fy, fx = self.food if food_known else (hy, hx)

        def ray(dy, dx):
            y, x, dist = hy, hx, 0
            for _ in range(20):
                y, x = (y + dy) % H, (x + dx) % W
                if (y, x) in self.body:
                    return dist
                dist += 1
            return 20

        # 8 directions rotated into the snake's frame: F, FR, R, BR, B, BL, L, FL
        sy, sx = STEP[self.heading]
        ly, lx = STEP[(self.heading - 1) % 4]
        dirs = []
        for f_c, l_c in ((1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1),(0,1),(1,1)):
            dirs.append((f_c * sy + l_c * ly, f_c * sx + l_c * lx))
        rays = [ray(dy, dx) / 20.0 for dy, dx in dirs]

        # food offset in the snake's frame, then cyclic-encoded. the wrap
        # period of each axis depends on which way we face
        gy = fy - hy
        gx = fx - hx
        fwd = gy * sy + gx * sx
        lat = gy * ly + gx * lx
        p_fwd = H if sy else W
        p_lat = H if ly else W
        import math
        af = 2 * math.pi * fwd / p_fwd
        al = 2 * math.pi * lat / p_lat
        if not food_known:
            # rays stay live so it can still avoid itself while searching
            return np.array(rays + [0.0, 0.0, 0.0, 0.0,
                                    len(self.body) / 200.0,
                                    self.stale / 100.0],
                            dtype=np.float32)
        return np.array(rays + [math.sin(af), math.cos(af),
                                math.sin(al), math.cos(al),
                                len(self.body) / 200.0,
                                self.stale / 100.0],
                        dtype=np.float32)
