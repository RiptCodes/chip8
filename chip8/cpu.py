"""CHIP-8 CPU — pure emulation, no I/O, no pygame."""
import random

from chip8.font import FONT


class Chip8:
    def __init__(self):
        self.memory = bytearray(4096)
        self.V = bytearray(16)
        self.I = 0
        self.pc = 0x200
        self.stack = []
        self.delay_timer = 0
        self.sound_timer = 0
        self.waiting_for_key = False
        self.waiting_register = 0
        self.framebuffer = [[0] * 64 for _ in range(32)]
        self.keys = set()
        self.rom_path = None
        self.memory[0x50:0x50 + len(FONT)] = FONT

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

    def step(self):
        if self.waiting_for_key:
            return

        opcode = self.memory[self.pc] << 8 | self.memory[self.pc + 1]
        self.pc += 2

        # 00E0 — clear screen
        if opcode == 0x00E0:
            self.framebuffer = [[0] * 64 for _ in range(32)]

        # 00EE — return
        elif opcode == 0x00EE:
            self.pc = self.stack.pop()

        # 1nnn — jump
        elif (opcode & 0xF000) == 0x1000:
            self.pc = opcode & 0x0FFF

        # 2nnn — call subroutine
        elif (opcode & 0xF000) == 0x2000:
            self.stack.append(self.pc)
            self.pc = opcode & 0x0FFF

        # Annn — set I
        elif (opcode & 0xF000) == 0xA000:
            self.I = opcode & 0x0FFF

        # 6xkk — V[x] = kk
        elif (opcode & 0xF000) == 0x6000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            self.V[X] = kk

        # 7xkk — V[x] += kk (no carry)
        elif (opcode & 0xF000) == 0x7000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            self.V[X] = (self.V[X] + kk) & 0xFF

        # 3xkk — skip if V[x] == kk
        elif (opcode & 0xF000) == 0x3000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            if self.V[X] == kk:
                self.pc += 2

        # 4xkk — skip if V[x] != kk
        elif (opcode & 0xF000) == 0x4000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            if self.V[X] != kk:
                self.pc += 2

        # 5xy0 — skip if V[x] == V[y]
        elif (opcode & 0xF000) == 0x5000:
            X = (opcode & 0x0F00) >> 8
            Y = (opcode & 0x00F0) >> 4
            if self.V[X] == self.V[Y]:
                self.pc += 2

        # 9xy0 — skip if V[x] != V[y]
        elif (opcode & 0xF000) == 0x9000:
            X = (opcode & 0x0F00) >> 8
            Y = (opcode & 0x00F0) >> 4
            if self.V[X] != self.V[Y]:
                self.pc += 2

        # 8xy_ arithmetic family
        elif (opcode & 0xF000) == 0x8000:
            X = (opcode & 0x0F00) >> 8
            Y = (opcode & 0x00F0) >> 4
            op = opcode & 0x000F
            if op == 0x0:
                self.V[X] = self.V[Y]
            elif op == 0x1:
                self.V[X] |= self.V[Y]
            elif op == 0x2:
                self.V[X] &= self.V[Y]
            elif op == 0x3:
                self.V[X] ^= self.V[Y]
            elif op == 0x4:
                total = self.V[X] + self.V[Y]
                self.V[X] = total & 0xFF
                self.V[0xF] = 1 if total > 0xFF else 0
            elif op == 0x5:
                ox, oy = self.V[X], self.V[Y]
                self.V[X] = (ox - oy) & 0xFF
                self.V[0xF] = 1 if ox > oy else 0
            elif op == 0x6:
                bit = self.V[X] & 0x01
                self.V[X] >>= 1
                self.V[0xF] = bit
            elif op == 0x7:
                ox, oy = self.V[X], self.V[Y]
                self.V[X] = (oy - ox) & 0xFF
                self.V[0xF] = 1 if oy > ox else 0
            elif op == 0xE:
                bit = (self.V[X] & 0x80) >> 7
                self.V[X] = (self.V[X] << 1) & 0xFF
                self.V[0xF] = bit

        # Dxyn — draw sprite
        elif (opcode & 0xF000) == 0xD000:
            X = (opcode & 0x0F00) >> 8
            Y = (opcode & 0x00F0) >> 4
            n = opcode & 0x000F
            sprite_x = self.V[X]
            sprite_y = self.V[Y]
            self.V[0xF] = 0
            for row in range(n):
                byte = self.memory[self.I + row]
                for col in range(8):
                    bit = (byte >> (7 - col)) & 1
                    if bit == 0:
                        continue
                    tx = (sprite_x + col) % 64
                    ty = (sprite_y + row) % 32
                    if self.framebuffer[ty][tx] == 1:
                        self.V[0xF] = 1
                    self.framebuffer[ty][tx] ^= bit

        # Cxkk — random
        elif (opcode & 0xF000) == 0xC000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            self.V[X] = random.randint(0, 255) & kk

        # Fx__ misc
        elif (opcode & 0xF000) == 0xF000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            if kk == 0x07:
                self.V[X] = self.delay_timer
            elif kk == 0x15:
                self.delay_timer = self.V[X]
            elif kk == 0x18:
                self.sound_timer = self.V[X]
            elif kk == 0x0A:
                self.waiting_for_key = True
                self.waiting_register = X
            elif kk == 0x1E:
                self.I += self.V[X]
            elif kk == 0x33:
                self.memory[self.I]     = self.V[X] // 100
                self.memory[self.I + 1] = (self.V[X] // 10) % 10
                self.memory[self.I + 2] = self.V[X] % 10
            elif kk == 0x29:
                self.I = 0x50 + self.V[X] * 5
            elif kk == 0x55:
                self.memory[self.I:self.I + X + 1] = self.V[0:X + 1]
            elif kk == 0x65:
                self.V[0:X + 1] = self.memory[self.I:self.I + X + 1]

        # Ex9E — skip if key V[x] is pressed
        elif (opcode & 0xF0FF) == 0xE09E:
            X = (opcode & 0x0F00) >> 8
            if self.V[X] in self.keys:
                self.pc += 2

        # ExA1 — skip if key V[x] is not pressed
        elif (opcode & 0xF0FF) == 0xE0A1:
            X = (opcode & 0x0F00) >> 8
            if self.V[X] not in self.keys:
                self.pc += 2

        else:
            print(f"unknown: {opcode:04x}")