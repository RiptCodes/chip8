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

LAYERS = (14, 18, 10, 3)     # v2: 8 rays + cyclic food + length/stale
POPULATION = 120
GAMES_PER_BRAIN = 2
ELITE = 12
TOURNAMENT = 4
MUTATION_RATE = 0.1
MUTATION_SCALE = 0.4
MAX_MOVES = 20000
STALL_LIMIT = 250   # stop only after this many generations with no new record


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
    return max(env.best_life, info["length"]), env.moves, info.get("won", False)


def evaluate(genome):
    total = 0.0
    best = 0
    for _ in range(GAMES_PER_BRAIN):
        length, moves, won = play(genome)
        # length dominates. early survival earns a little (so a fresh random
        # population has a gradient to climb) but it caps at 400 moves, and
        # past that loitering costs, so circling never pays. winning is
        # the jackpot
        total += length * 1000 + min(moves, 400) - moves * 0.2
        if won:
            total += 100_000
            best = max(best, 250)
        best = max(best, length)
    return total / GAMES_PER_BRAIN, best


def run(generations=None, seed=0):
    """generations=None runs until the record stalls for STALL_LIMIT gens."""
    import os
    os.makedirs("ai/top_snakes", exist_ok=True)
    rng = np.random.default_rng(seed)
    pop = [rng.normal(0, 1, GENOME_SIZE).astype(np.float32)
           for _ in range(POPULATION)]
    # warm start: seed with any survivors from a previous run
    saved = sorted(f for f in os.listdir("ai/top_snakes") if f.endswith(".npy"))
    for i, f in enumerate(saved[:20]):
        g = np.load(os.path.join("ai/top_snakes", f))
        if g.shape == (GENOME_SIZE,):
            pop[i] = g.astype(np.float32)
    if saved:
        print(f"warm-started with {min(len(saved), 20)} saved genomes")
    best_genome, record = None, 0
    last_improve = 0
    started = time.time()

    with mp.Pool() as pool:
        gen = -1
        while True:
            gen += 1
            if generations is not None and gen >= generations:
                break
            if generations is None and gen - last_improve >= STALL_LIMIT:
                print(f"stalled: no record improvement for {STALL_LIMIT} generations")
                break
            results = pool.map(evaluate, pop)
            fits = [r[0] for r in results]
            lens = [r[1] for r in results]
            order = np.argsort(fits)[::-1]

            if lens[order[0]] > record:
                record = lens[order[0]]
                best_genome = pop[order[0]].copy()
                np.save("ai/snake_best.npy", best_genome)
                last_improve = gen

            # keep the current top 20 on disk so they can be watched mid-run
            if gen % 20 == 0:
                for rank, i in enumerate(order[:20]):
                    np.save(f"ai/top_snakes/rank_{rank:02}.npy", pop[i])

            if gen % 5 == 0:
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
    run(int(sys.argv[1]) if len(sys.argv) > 1 else None)
