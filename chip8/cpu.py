"""CHIP-8 CPU — pure emulation, no I/O, no pygame."""
import random

from chip8.font import FONT, FONT_HIGH


class Chip8:
    def __init__(self):
        self.memory = bytearray(4096)
        self.V = bytearray(16)
        self.I = 0
        self.pc = 0x200
        self.stack = []
        self.high_res = False
        self.delay_timer = 0
        self.sound_timer = 0
        self.waiting_for_key = False
        self.waiting_register = 0
        self.framebuffer = [[0] * 128 for _ in range(64)]
        self.keys = set()
        self.rom_path = None
        self.memory[0x50:0x50 + len(FONT)] = FONT
        self.memory[0xA0:0xA0 + len(FONT_HIGH)] = FONT_HIGH

    def load_rom(self, path):
        with open(path, 'rb') as f:
            rom = f.read()
        self.memory[0x200:0x200 + len(rom)] = rom
        self.rom_path = path

    def reset(self):
        path = self.rom_path
        self.__init__()
        if path:
            self.load_rom(path)

    def tick_timers(self):
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1

    def _dims(self):
        return (128, 64) if self.high_res else (64, 32)

    def _clear_screen(self):
        self.framebuffer = [[0] * 128 for _ in range(64)]

    def _draw_sprite(self, X, Y, n):
        w, h = self._dims()
        sprite_x = self.V[X]
        sprite_y = self.V[Y]
        self.V[0xF] = 0

        if n == 0:
            # SCHIP 16x16 sprite: two bytes per row
            rows, cols = 16, 16
        else:
            rows, cols = n, 8

        for row in range(rows):
            if n == 0:
                bits = (self.memory[self.I + row * 2] << 8) | self.memory[self.I + row * 2 + 1]
            else:
                bits = self.memory[self.I + row]
            for col in range(cols):
                bit = (bits >> (cols - 1 - col)) & 1
                if bit == 0:
                    continue
                tx = (sprite_x + col) % w
                ty = (sprite_y + row) % h
                if self.framebuffer[ty][tx]:
                    self.V[0xF] = 1
                self.framebuffer[ty][tx] ^= 1

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
            self._clear_screen()

        # 00FF — high-res mode
        elif opcode == 0x00FF:
            self.high_res = True
            self._clear_screen()

        # 00Cn — scroll display down n pixels
        elif (opcode & 0xFFF0) == 0x00C0:
            _, h = self._dims()
            for y in range(h - 1, -1, -1):
                if y >= n:
                    self.framebuffer[y] = self.framebuffer[y - n][:]
                else:
                    self.framebuffer[y] = [0] * 128

        # 00FB — scroll display right 4 pixels
        elif opcode == 0x00FB:
            w, h = self._dims()
            for y in range(h):
                row = self.framebuffer[y]
                self.framebuffer[y] = [0] * 4 + row[:w - 4] + row[w:]

        # 00FC — scroll display left 4 pixels
        elif opcode == 0x00FC:
            w, h = self._dims()
            for y in range(h):
                row = self.framebuffer[y]
                self.framebuffer[y] = row[4:w] + [0] * 4 + row[w:]

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
                self.pc += 2

        # 4xkk — skip if V[x] != kk
        elif top == 0x4000:
            if self.V[X] != kk:
                self.pc += 2

        # 5xy0 — skip if V[x] == V[y]
        elif top == 0x5000:
            if self.V[X] == self.V[Y]:
                self.pc += 2

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
            elif n == 0x2:
                self.V[X] &= self.V[Y]
            elif n == 0x3:
                self.V[X] ^= self.V[Y]
            elif n == 0x4:
                total = self.V[X] + self.V[Y]
                self.V[X] = total & 0xFF
                self.V[0xF] = 1 if total > 0xFF else 0
            elif n == 0x5:
                ox, oy = self.V[X], self.V[Y]
                self.V[X] = (ox - oy) & 0xFF
                self.V[0xF] = 1 if ox > oy else 0
            elif n == 0x6:
                bit = self.V[X] & 0x01
                self.V[X] >>= 1
                self.V[0xF] = bit
            elif n == 0x7:
                ox, oy = self.V[X], self.V[Y]
                self.V[X] = (oy - ox) & 0xFF
                self.V[0xF] = 1 if oy > ox else 0
            elif n == 0xE:
                bit = (self.V[X] & 0x80) >> 7
                self.V[X] = (self.V[X] << 1) & 0xFF
                self.V[0xF] = bit

        # 9xy0 — skip if V[x] != V[y]
        elif top == 0x9000:
            if self.V[X] != self.V[Y]:
                self.pc += 2

        # Annn — set I
        elif top == 0xA000:
            self.I = nnn

        # Cxkk — random
        elif top == 0xC000:
            self.V[X] = random.randint(0, 255) & kk

        # Dxyn — draw sprite (8xn, or 16x16 when n == 0)
        elif top == 0xD000:
            self._draw_sprite(X, Y, n)

        # Ex9E — skip if key V[x] is pressed
        elif (opcode & 0xF0FF) == 0xE09E:
            if self.V[X] in self.keys:
                self.pc += 2

        # ExA1 — skip if key V[x] is not pressed
        elif (opcode & 0xF0FF) == 0xE0A1:
            if self.V[X] not in self.keys:
                self.pc += 2

        # Fx__ misc
        elif top == 0xF000:
            if kk == 0x07:
                self.V[X] = self.delay_timer
            elif kk == 0x0A:
                self.waiting_for_key = True
                self.waiting_register = X
            elif kk == 0x15:
                self.delay_timer = self.V[X]
            elif kk == 0x18:
                self.sound_timer = self.V[X]
            elif kk == 0x1E:
                self.I = (self.I + self.V[X]) & 0xFFF
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
            elif kk == 0x65:
                self.V[0:X + 1] = self.memory[self.I:self.I + X + 1]

        else:
            print(f"unknown: {opcode:04x}")
