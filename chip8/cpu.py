"""CHIP-8 / SUPER-CHIP / XO-CHIP CPU — pure emulation, no I/O, no pygame."""
import random

from chip8.font import FONT, FONT_HIGH

# behaviour differences between the interpreter generations.
# some ROMs need one, some need the other, so it's a setting.
QUIRK_PROFILES = {
    "chip-8": {
        "vf_reset": True,          # 8xy1/2/3 also set VF to 0
        "memory_increment": True,  # Fx55/Fx65 leave I pointing past the block
        "shift_uses_vy": True,     # 8xy6/8xyE shift VY into VX
        "jump_uses_vx": False,     # Bnnn jumps to nnn + V0
        "display_wait": True,      # one draw per frame
        "clip_sprites": True,      # pixels off the edge clip instead of wrapping
    },
    "schip": {
        "vf_reset": False,
        "memory_increment": False,
        "shift_uses_vy": False,
        "jump_uses_vx": True,      # Bxnn jumps to xnn + VX
        "display_wait": False,
        "clip_sprites": True,
    },
    "xo-chip": {
        "vf_reset": False,
        "memory_increment": True,
        "shift_uses_vy": False,
        "jump_uses_vx": False,
        "display_wait": False,
        "clip_sprites": False,     # xo-chip sprites wrap
    },
}

MEMORY_SIZE = 65536   # xo-chip extends the 4KB address space to 64KB


class Chip8:
    def __init__(self, profile="schip"):
        self.profile = profile if profile in QUIRK_PROFILES else "schip"
        self.quirks = dict(QUIRK_PROFILES[self.profile])
        self.memory = bytearray(MEMORY_SIZE)
        self.V = bytearray(16)
        self.I = 0
        self.pc = 0x200
        self.stack = []
        self.high_res = False
        self.delay_timer = 0
        self.sound_timer = 0
        self.waiting_for_key = False
        self.waiting_register = 0
        # two display planes; plane 1 gives xo-chip its extra two colours.
        # normal chip-8/schip ROMs only ever touch plane 0.
        self.planes = [[[0] * 128 for _ in range(64)], [[0] * 128 for _ in range(64)]]
        self.plane = 1            # bitmask of planes drawing applies to
        self.keys = set()
        self.rom_path = None
        self.drew = False
        self.audio_buffer = bytes(16)
        self.pitch = 64
        self.memory[0x50:0x50 + len(FONT)] = FONT
        self.memory[0xA0:0xA0 + len(FONT_HIGH)] = FONT_HIGH

    @property
    def framebuffer(self):
        return self.planes[0]

    def load_rom(self, path):
        with open(path, 'rb') as f:
            rom = f.read()
        self.memory[0x200:0x200 + len(rom)] = rom
        self.rom_path = path

    def reset(self):
        path = self.rom_path
        self.__init__(self.profile)
        if path:
            self.load_rom(path)

    def tick_timers(self):
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1

    def _dims(self):
        return (128, 64) if self.high_res else (64, 32)

    def _selected_planes(self):
        return [p for p in range(2) if (self.plane >> p) & 1]

    def _clear_screen(self):
        for p in self._selected_planes():
            self.planes[p] = [[0] * 128 for _ in range(64)]

    def _skip(self):
        # a skipped instruction can be the 4-byte F000 NNNN
        next_op = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc += 4 if next_op == 0xF000 else 2

    def _draw_sprite(self, X, Y, n):
        w, h = self._dims()
        sprite_x = self.V[X] % w
        sprite_y = self.V[Y] % h
        clip = self.quirks["clip_sprites"]
        self.V[0xF] = 0
        self.drew = True

        if n == 0:
            rows, wide = 16, True     # SCHIP/XO 16x16: two bytes per row
        else:
            rows, wide = n, False

        offset = 0
        for p in self._selected_planes():
            fb = self.planes[p]
            for row in range(rows):
                ty = sprite_y + row
                if ty >= h:
                    if clip:
                        continue
                    ty %= h
                if wide:
                    addr = self.I + offset + row * 2
                    bits = (self.memory[addr] << 8) | self.memory[addr + 1]
                    cols = 16
                else:
                    bits = self.memory[self.I + offset + row]
                    cols = 8
                for col in range(cols):
                    if not (bits >> (cols - 1 - col)) & 1:
                        continue
                    tx = sprite_x + col
                    if tx >= w:
                        if clip:
                            continue
                        tx %= w
                    if fb[ty][tx]:
                        self.V[0xF] = 1
                    fb[ty][tx] ^= 1
            offset += rows * 2 if wide else rows

    def _scroll_rows(self, shift):
        # shift > 0 scrolls down, shift < 0 scrolls up
        _, h = self._dims()
        for p in self._selected_planes():
            fb = self.planes[p]
            if shift > 0:
                for y in range(h - 1, -1, -1):
                    fb[y] = fb[y - shift][:] if y >= shift else [0] * 128
            else:
                s = -shift
                for y in range(h):
                    fb[y] = fb[y + s][:] if y + s < h else [0] * 128

    def _scroll_cols(self, shift):
        # shift > 0 scrolls right, shift < 0 scrolls left
        w, h = self._dims()
        for p in self._selected_planes():
            fb = self.planes[p]
            for y in range(h):
                row = fb[y]
                if shift > 0:
                    fb[y] = [0] * shift + row[:w - shift] + row[w:]
                else:
                    s = -shift
                    fb[y] = row[s:w] + [0] * s + row[w:]

    def step(self):
        if self.waiting_for_key:
            return

        opcode = self.memory[self.pc] << 8 | self.memory[self.pc + 1]
        self.pc += 2

        # operand fields, extracted once
        X = (opcode & 0x0F00) >> 8
        Y = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F
        kk = opcode & 0x00FF
        nnn = opcode & 0x0FFF
        top = opcode & 0xF000

        # 00E0 — clear screen
        if opcode == 0x00E0:
            self._clear_screen()

        # 00FE — low-res mode
        elif opcode == 0x00FE:
            self.high_res = False
            self.plane = 1
            self.planes = [[[0] * 128 for _ in range(64)], [[0] * 128 for _ in range(64)]]

        # 00FF — high-res mode
        elif opcode == 0x00FF:
            self.high_res = True
            self.plane = 1
            self.planes = [[[0] * 128 for _ in range(64)], [[0] * 128 for _ in range(64)]]

        # 00Cn — scroll down n pixels
        elif (opcode & 0xFFF0) == 0x00C0:
            self._scroll_rows(n)

        # 00Dn — scroll up n pixels (xo-chip)
        elif (opcode & 0xFFF0) == 0x00D0:
            self._scroll_rows(-n)

        # 00FB — scroll right 4 pixels
        elif opcode == 0x00FB:
            self._scroll_cols(4)

        # 00FC — scroll left 4 pixels
        elif opcode == 0x00FC:
            self._scroll_cols(-4)

        # 00FD — exit interpreter
        elif opcode == 0x00FD:
            raise SystemExit

        # 00EE — return
        elif opcode == 0x00EE:
            self.pc = self.stack.pop()

        # 1nnn — jump
        elif top == 0x1000:
            self.pc = nnn

        # 2nnn — call subroutine
        elif top == 0x2000:
            self.stack.append(self.pc)
            self.pc = nnn

        # 3xkk — skip if V[x] == kk
        elif top == 0x3000:
            if self.V[X] == kk:
                self._skip()

        # 4xkk — skip if V[x] != kk
        elif top == 0x4000:
            if self.V[X] != kk:
                self._skip()

        # 5xy0 / 5xy2 / 5xy3
        elif top == 0x5000:
            if n == 0x0:
                if self.V[X] == self.V[Y]:
                    self._skip()
            elif n == 0x2:
                # save V[x]..V[y] to memory at I (xo-chip)
                rng = range(X, Y + 1) if X <= Y else range(X, Y - 1, -1)
                for i, r in enumerate(rng):
                    self.memory[self.I + i] = self.V[r]
            elif n == 0x3:
                # load V[x]..V[y] from memory at I (xo-chip)
                rng = range(X, Y + 1) if X <= Y else range(X, Y - 1, -1)
                for i, r in enumerate(rng):
                    self.V[r] = self.memory[self.I + i]

        # 6xkk — V[x] = kk
        elif top == 0x6000:
            self.V[X] = kk

        # 7xkk — V[x] += kk (no carry)
        elif top == 0x7000:
            self.V[X] = (self.V[X] + kk) & 0xFF

        # 8xy_ arithmetic family
        elif top == 0x8000:
            if n == 0x0:
                self.V[X] = self.V[Y]
            elif n == 0x1:
                self.V[X] |= self.V[Y]
                if self.quirks["vf_reset"]:
                    self.V[0xF] = 0
            elif n == 0x2:
                self.V[X] &= self.V[Y]
                if self.quirks["vf_reset"]:
                    self.V[0xF] = 0
            elif n == 0x3:
                self.V[X] ^= self.V[Y]
                if self.quirks["vf_reset"]:
                    self.V[0xF] = 0
            elif n == 0x4:
                total = self.V[X] + self.V[Y]
                self.V[X] = total & 0xFF
                self.V[0xF] = 1 if total > 0xFF else 0
            elif n == 0x5:
                ox, oy = self.V[X], self.V[Y]
                self.V[X] = (ox - oy) & 0xFF
                self.V[0xF] = 1 if ox >= oy else 0
            elif n == 0x6:
                if self.quirks["shift_uses_vy"]:
                    self.V[X] = self.V[Y]
                bit = self.V[X] & 0x01
                self.V[X] >>= 1
                self.V[0xF] = bit
            elif n == 0x7:
                ox, oy = self.V[X], self.V[Y]
                self.V[X] = (oy - ox) & 0xFF
                self.V[0xF] = 1 if oy >= ox else 0
            elif n == 0xE:
                if self.quirks["shift_uses_vy"]:
                    self.V[X] = self.V[Y]
                bit = (self.V[X] & 0x80) >> 7
                self.V[X] = (self.V[X] << 1) & 0xFF
                self.V[0xF] = bit

        # 9xy0 — skip if V[x] != V[y]
        elif top == 0x9000:
            if self.V[X] != self.V[Y]:
                self._skip()

        # Annn — set I
        elif top == 0xA000:
            self.I = nnn

        # Bnnn — jump to nnn + V0 (or + VX with the schip quirk)
        elif top == 0xB000:
            offset = self.V[X] if self.quirks["jump_uses_vx"] else self.V[0]
            self.pc = (nnn + offset) & 0xFFFF

        # Cxkk — random
        elif top == 0xC000:
            self.V[X] = random.randint(0, 255) & kk

        # Dxyn — draw sprite (8xn, or 16x16 when n == 0)
        elif top == 0xD000:
            self._draw_sprite(X, Y, n)

        # Ex9E — skip if key V[x] is pressed
        elif (opcode & 0xF0FF) == 0xE09E:
            if self.V[X] in self.keys:
                self._skip()

        # ExA1 — skip if key V[x] is not pressed
        elif (opcode & 0xF0FF) == 0xE0A1:
            if self.V[X] not in self.keys:
                self._skip()

        # Fx__ misc (and the xo-chip 4-byte / plane / audio ops)
        elif top == 0xF000:
            if opcode == 0xF000:
                # i := long NNNN — the only 4-byte instruction
                self.I = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
                self.pc += 2
            elif opcode == 0xF002:
                # load 16-byte audio pattern from I (stored, playback stays a beep)
                self.audio_buffer = bytes(self.memory[self.I:self.I + 16])
            elif kk == 0x01:
                # plane n — select which planes drawing affects
                self.plane = X & 0x3
            elif kk == 0x3A:
                self.pitch = self.V[X]
            elif kk == 0x07:
                self.V[X] = self.delay_timer
            elif kk == 0x0A:
                self.waiting_for_key = True
                self.waiting_register = X
            elif kk == 0x15:
                self.delay_timer = self.V[X]
            elif kk == 0x18:
                self.sound_timer = self.V[X]
            elif kk == 0x1E:
                self.I = (self.I + self.V[X]) & 0xFFFF
            elif kk == 0x29:
                self.I = 0x50 + self.V[X] * 5
            elif kk == 0x30:
                self.I = 0xA0 + self.V[X] * 10
            elif kk == 0x33:
                self.memory[self.I] = self.V[X] // 100
                self.memory[self.I + 1] = (self.V[X] // 10) % 10
                self.memory[self.I + 2] = self.V[X] % 10
            elif kk == 0x55:
                self.memory[self.I:self.I + X + 1] = self.V[0:X + 1]
                if self.quirks["memory_increment"]:
                    self.I = (self.I + X + 1) & 0xFFFF
            elif kk == 0x65:
                self.V[0:X + 1] = self.memory[self.I:self.I + X + 1]
                if self.quirks["memory_increment"]:
                    self.I = (self.I + X + 1) & 0xFFFF

        else:
            print(f"unknown: {opcode:04x}")
