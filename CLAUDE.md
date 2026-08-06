# CLAUDE.md — CHIP-8 emulator project

> Loaded automatically when Claude Code runs in this folder. Context + conventions for this repo.
> Owner: RiptCodes. Learning to code / building a portfolio. Be direct, teach the *why*, flag uncertainty.

## What this is
A **CHIP-8 / SUPER-CHIP / XO-CHIP emulator in Python** (pygame frontend), faithful to Cowgod's spec.
Runs classic ROMs (Pong, Tetris, Space Invaders, Brix), passes the Timendus test suite, and doubles
as a **headless RL environment** — a PPO agent plays Pong, neuroevolution learns Snake from the screen.
GitHub: https://github.com/RiptCodes/chip8

## The core design decision
The **CPU is completely I/O-free** — no pygame, no filesystem inside opcodes. `main.py` writes into
`chip.keys` each frame and reads `chip.framebuffer` / `chip.sound_timer`. Rendering, audio, music,
menus are separate layers that only touch the CPU through those attributes. This is what makes the
CPU unit-testable and reusable as an RL env — **preserve this separation** in any change.

## Layout
```
chip8/
  cpu.py       # class Chip8 — pure emulation, unit-tested, NO I/O
  display.py   # Renderer + colour themes (phosphor/amber/gameboy/ibm)
  audio.py     # Beeper — square wave tied to sound_timer
  music.py     input.py     font.py (hex sprites @0x50)
  intro.py     menu.py      settings.py (JSON-persisted)     crt.py (scanline/vignette, F1)
  env.py       # headless gym-style RL environment
main.py        # frontend: pygame setup + state machine
ai/  train_pong.py (PPO/sb3)  watch.py  snake_env.py  snake_evolve.py  snake_watch_top.py
tests/test_cpu.py
roms/          # Timendus test suite + games
```

## Status — implemented
- Full 35-opcode CPU, correct VF (carry/borrow/shift/collision), XOR sprites with wrapping
- 16-key keypad incl. blocking `Fx0A`; 60Hz delay+sound timers; square-wave beep
- 4 themes, runtime cycle-rate, pause, hot-reset, music, boot splash, menu, ROM picker, settings
- **SUPER-CHIP**: 128x64 hi-res, 16x16 sprites, scroll, hi-res font
- **XO-CHIP**: 64KB, `F000` long instr, dual planes (4 colours), scroll-up, register save/load
- Configurable **quirks** (chip-8 / schip / xo-chip); CRT shader
- pytest: `6xkk`, `8xy4`, `8xy5`, `Fx33`, `Dxyn`
- AI/Pong: PPO, 8 parallel envs, 24k frames no concede. AI/Snake: neuroevolution, record ~116

## Gotchas / conventions (learned the hard way)
- **VF ordering**: compute the flag from the operands FIRST, then store the result. Reversing it is the classic bug.
- **Sprites XOR-draw** — games erase by redrawing; collision = any pixel that flipped 1→0.
- **Quirks differ** across CHIP-8/SCHIP/XO-CHIP (shift source, Fx55/Fx65 I increment, wrapping). Route through the quirks profile, don't hardcode.
- **RL screen-reading**: XOR-erase makes sprites blink/flicker, so the env wrappers reconstruct stable state via **persistence tracking** — don't "fix" the flicker in the CPU, it's correct emulation.
- Keep new features out of `cpu.py` unless they're genuinely CPU behaviour.

## Run / test
```bash
.\.venv\Scripts\Activate.ps1
python main.py                 # menu
python main.py roms/Pong.ch8   # straight into a ROM
python -m pytest tests/ -v
```

## Memory
This project also has a summary note in the Obsidian vault (`Projects/CHIP-8/`). Use `/preserve` to
record durable decisions here and `/compress` to save session logs as you work.

## Next / TODO
- (add what you're working on next)
