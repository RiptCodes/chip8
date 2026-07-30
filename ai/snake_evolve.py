"""Evolve a network to play snake.ch8 on the emulator.

Same idea as the Pong agent but with no gradients: a population of brains
each play the real ROM, the best ones breed. Fitness is the length reached,
so nothing about the reward has to be hand-tuned.

Run:  python -m ai.snake_evolve            (120 generations)
      python -m ai.snake_evolve 20         (short run)
"""
import multiprocessing as mp
import sys
import time

import numpy as np

from ai.snake_env import SnakeEnv

LAYERS = (8, 14, 3)          # 8 screen features -> straight/left/right
POPULATION = 120
GAMES_PER_BRAIN = 2
ELITE = 12
TOURNAMENT = 4
MUTATION_RATE = 0.1
MUTATION_SCALE = 0.4
MAX_MOVES = 700


def genome_size(layers=LAYERS):
    return sum(a * b + b for a, b in zip(layers, layers[1:]))


GENOME_SIZE = genome_size()


def forward(genome, x):
    i = 0
    for a, b in zip(LAYERS, LAYERS[1:]):
        w = genome[i:i + a * b].reshape(a, b); i += a * b
        bias = genome[i:i + b]; i += b
        x = x @ w + bias
        if b != LAYERS[-1]:
            x = np.tanh(x)
    return x


def play(genome):
    """One life. Ends when the snake dies, so length is honestly earned."""
    env = SnakeEnv(max_moves=MAX_MOVES)
    state = env.reset()
    done = False
    while not done:
        action = int(np.argmax(forward(genome, state)))
        state, _, done, info = env.step(action)
    return max(env.best_life, info["length"]), env.moves


def evaluate(genome):
    total = 0.0
    best = 0
    for _ in range(GAMES_PER_BRAIN):
        length, moves = play(genome)
        total += length * 1000 + moves
        best = max(best, length)
    return total / GAMES_PER_BRAIN, best


def run(generations=120, seed=0):
    rng = np.random.default_rng(seed)
    pop = [rng.normal(0, 1, GENOME_SIZE).astype(np.float32)
           for _ in range(POPULATION)]
    best_genome, record = None, 0
    started = time.time()

    with mp.Pool() as pool:
        for gen in range(generations):
            results = pool.map(evaluate, pop)
            fits = [r[0] for r in results]
            lens = [r[1] for r in results]
            order = np.argsort(fits)[::-1]

            if lens[order[0]] > record:
                record = lens[order[0]]
                best_genome = pop[order[0]].copy()
                np.save("ai/snake_best.npy", best_genome)

            if gen % 5 == 0 or gen == generations - 1:
                print(f"gen {gen:3}  best len {lens[order[0]]:3}  "
                      f"mean fit {np.mean(fits):7.0f}  record {record:3}  "
                      f"{time.time() - started:5.0f}s", flush=True)

            nxt = [pop[i].copy() for i in order[:ELITE]]
            while len(nxt) < POPULATION:
                pa = max(rng.integers(0, POPULATION, TOURNAMENT), key=lambda i: fits[i])
                pb = max(rng.integers(0, POPULATION, TOURNAMENT), key=lambda i: fits[i])
                mask = rng.random(GENOME_SIZE) < 0.5
                child = np.where(mask, pop[pa], pop[pb]).astype(np.float32)
                mut = rng.random(GENOME_SIZE) < MUTATION_RATE
                child = child + mut * rng.normal(0, MUTATION_SCALE, GENOME_SIZE)
                nxt.append(child.astype(np.float32))
            pop = nxt

    np.save("ai/snake_best.npy", best_genome)
    print(f"done — record length {record}, saved to ai/snake_best.npy")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 120)
