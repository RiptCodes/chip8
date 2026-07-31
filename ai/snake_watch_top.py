"""Launch the top 20 snakes, each in its own window, tiled 5x4.

Run:  python -m ai.snake_watch_top              # tile from the top-left of the main monitor
      python -m ai.snake_watch_top 1920 0       # tile starting at x=1920 (second monitor)
      python -m ai.snake_watch_top -1920 0      # monitor to the LEFT of the main one
Close them all with ctrl+c here, or each window individually.
"""
import os
import subprocess
import sys

COLS = 5
WIN_W = 64 * 6 + 8          # viewer cell size 6 + window chrome fudge
WIN_H = 32 * 6 + 22 + 34


def main():
    if not os.path.isdir("ai/top_snakes"):
        print("no ai/top_snakes/ yet — run ai.snake_evolve first")
        sys.exit(1)

    ox = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    oy = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    ranks = sorted(f for f in os.listdir("ai/top_snakes") if f.endswith(".npy") and f.startswith("rank"))
    procs = []
    for i in range(min(20, len(ranks))):
        x = ox + (i % COLS) * WIN_W
        y = oy + (i // COLS) * WIN_H
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "ai.snake_watch_one", str(i), str(x), str(y)]))
    print(f"launched {len(procs)} snake windows — ctrl+c here closes them all")
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
