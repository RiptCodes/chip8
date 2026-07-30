# Attempting to make a chip 8 emulator with additional improvements and features without going over memory budget
import sys
import pygame
import random
import numpy as np

SCALE = 10

pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
pygame.init()

screen = pygame.display.set_mode((640, 320))
clock = pygame.time.Clock()

# Sound
sample_rate = 22050
freq = 440
duration = 1.0
amplitude = 4000
n_samples = int(sample_rate * duration)
t = np.arange(n_samples)
wave = (amplitude * np.sign(np.sin(2 * np.pi * freq * t / sample_rate))).astype(np.int16)
wave = np.column_stack([wave, wave])
beep_sound = pygame.sndarray.make_sound(wave)

running = True

# CPU / Memory
memory = bytearray(4096)
V = bytearray(16)
I = 0
pc = 0x200
stack = []
delay_timer = 0
sound_timer = 0
is_beeping = False
waiting_for_key = False
waiting_register = 0
pause = False


# log message
def log(text_to_log):
    pass

def reset():
    global memory, V, I, pc, stack, delay_timer, sound_timer
    global waiting_for_key, is_beeping, framebuffer
    memory = bytearray(4096)
    memory[0x50:0x50 + len(FONT)] = FONT
    with open(rom_path, 'rb') as f:
        rom = f.read()
    memory[0x200:0x200 + len(rom)] = rom
    V = bytearray(16)
    I = 0
    pc = 0x200
    stack = []
    delay_timer = 0
    sound_timer = 0
    waiting_for_key = False
    is_beeping = False
    framebuffer = [[0]*64 for _ in range(32)]
    beep_sound.stop()

# Keyboard
KEYMAP = {
    pygame.K_1: 0x1, pygame.K_2: 0x2, pygame.K_3: 0x3, pygame.K_4: 0xC,
    pygame.K_q: 0x4, pygame.K_w: 0x5, pygame.K_e: 0x6, pygame.K_r: 0xD,
    pygame.K_a: 0x7, pygame.K_s: 0x8, pygame.K_d: 0x9, pygame.K_f: 0xE,
    pygame.K_z: 0xA, pygame.K_x: 0x0, pygame.K_c: 0xB, pygame.K_v: 0xF,
}

# Fonts
FONT = bytes([
    # 0
    0xF0, 0x90, 0x90, 0x90, 0xF0,
    # 1
    0x20, 0x60, 0x20, 0x20, 0x70,
    # 2
    0xF0, 0x10, 0xF0, 0x80, 0xF0,
    # 3
    0xF0, 0x10, 0xF0, 0x10, 0xF0,
    # 4
    0x90, 0x90, 0xF0, 0x10, 0x10,
    # 5
    0xF0, 0x80, 0xF0, 0x10, 0xF0,
    # 6
    0xF0, 0x80, 0xF0, 0x90, 0xF0,
    # 7
    0xF0, 0x10, 0x20, 0x40, 0x40,
    # 8
    0xF0, 0x90, 0xF0, 0x90, 0xF0,
    # 9
    0xF0, 0x90, 0xF0, 0x10, 0xF0,
    # A
    0xF0, 0x90, 0xF0, 0x90, 0x90,
    # B
    0xE0, 0x90, 0xE0, 0x90, 0xE0,
    # C
    0xF0, 0x80, 0x80, 0x80, 0xF0,
    # D
    0xE0, 0x90, 0x90, 0x90, 0xE0,
    # E
    0xF0, 0x80, 0xF0, 0x80, 0xF0,
    # F
    0xF0, 0x80, 0xF0, 0x80, 0x80,
])

# Themes
THEMES = [
    ("phosphor", (0, 0, 0),     (0, 255, 65)),
    ("amber",    (0, 0, 0),     (255, 176, 0)),
    ("gameboy",  (155, 188, 15),(15, 56, 15)),
    ("ibm",      (30, 30, 60),  (200, 220, 255)),
]
theme_idx = 0


# loading Fonts
memory[0x50:0x50 + len(FONT)] = FONT

# ROM Load
if len(sys.argv) > 1:
    rom_path = sys.argv[1]
else:
    rom_path = "roms/Pong.ch8"
with open(rom_path, 'rb') as f:
    rom = f.read()

memory[0x200:0x200 + len(rom)] = rom #assigning ROM to the Memory location 0x200 - end of ROM 0xFFF


# print(memory[pc:pc+20].hex())

framebuffer = []
for _ in range(32):
    row = [0] * 64
    framebuffer.append(row)


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if waiting_for_key and event.key in KEYMAP:
                V[waiting_register] = KEYMAP[event.key]
                waiting_for_key = False
            if event.key == pygame.K_TAB:
                theme_idx = (theme_idx + 1) % len(THEMES)
            if event.key == pygame.K_p:
                pause = not pause
            if event.key == pygame.K_r:
                reset()

    name, bg, fg = THEMES[theme_idx]

    screen.fill(bg)

    if delay_timer > 0:
        delay_timer -= 1
    if sound_timer > 0:
        sound_timer -= 1
    if sound_timer > 0 and not is_beeping:
        beep_sound.play(loops=-1)
        is_beeping = True
    elif sound_timer == 0 and is_beeping:
        beep_sound.stop()
        is_beeping = False


    keys = pygame.key.get_pressed()
    chip8_keys = {chip8_key for pyk, chip8_key in KEYMAP.items() if keys[pyk]}

    # fetching and shifting Opcode and decoding
    for _ in range(10):
        if pause or waiting_for_key:
            break
        opcode = memory[pc] << 8 | memory[pc + 1]
        pc += 2
        # For opcode 00E0
        if opcode == 0x00E0:
            framebuffer = [[0]*64 for _ in range(32)]
        
        elif opcode == 0x00EE:
            pc = stack.pop()

        # JUMP
        elif (opcode & 0xF000) == 0x1000:
            pc = opcode & 0x0FFF

        # push to stack
        elif (opcode & 0xF000) == 0x2000:
            stack.append(pc)
            pc = opcode & 0x0FFF

        # Set I
        elif (opcode & 0xF000) == 0xA000:
            I = opcode & 0x0FFF

        # set V[x]
        elif (opcode & 0xF000) == 0x6000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            V[X] = kk 

        # add to V[x]
        elif (opcode & 0xF000) == 0x7000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            V[X] = (V[X] + kk) & 0xFF
        
        # Skip an instruction
        elif (opcode & 0xF000) == 0x3000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            if V[X] == kk:
                pc += 2 # skip the next instruction
        
        #skip if not equal
        elif (opcode & 0xF000) == 0x4000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            if V[X] != kk:
                pc += 2

        #skip if not equal 5xy0
        elif (opcode & 0xF000) == 0x5000:
            X = (opcode & 0x0F00) >> 8
            Y = (opcode & 0x00F0) >> 4
            if V[X] == V[Y]:
                pc += 2
        
        #skip if not equal 9xy0
        elif (opcode & 0xF000) == 0x9000:
            X = (opcode & 0x0F00) >> 8
            Y = (opcode & 0x00F0) >> 4
            if V[X] != V[Y]:
                pc += 2
        
        elif (opcode & 0xF000) == 0x8000:
            X = (opcode & 0x0F00) >> 8
            Y = (opcode & 0x00F0) >> 4
            op = opcode & 0x000F
            # 8xy0
            if op == 0x0:
                V[X] = V[Y]
            # 8xy1
            elif op == 0x1:
                V[X] |= V[Y]
            # 8xy2
            elif op == 0x2:
                V[X] &= V[Y]
            # 8xy3
            elif op == 0x3:
                V[X] ^= V[Y]
            # 8xy4
            elif op == 0x4:
                total = V[X] + V[Y]
                V[X] = total & 0xFF
                if total > 0xFF:
                    V[0xF] = 1
                else:
                    V[0xF] = 0
            # 8xy5
            elif op == 0x5:
                original_x = V[X]
                original_y = V[Y]
                V[X] = (original_x - original_y) & 0xFF
                if original_x > original_y:
                    V[0xF] = 1
                else:
                   V[0xF] = 0  
            # 8xy6
            elif op == 0x6:
                bit = V[X] & 0x01
                V[X] >>= 1
                V[0xF] = bit
            # 8xy7
            elif op == 0x7:
                original_x = V[X]
                original_y = V[Y]
                V[X] = (original_y - original_x) & 0xFF
                if original_y > original_x:
                    V[0xF] = 1
                else:
                   V[0xF] = 0  
            # 8xyE
            elif op == 0xE:
                bit = (V[X] & 0x80) >> 7
                V[X] = (V[X] << 1) & 0xFF
                V[0xF] = bit


        # showing sprite on screen
        elif (opcode & 0xF000) == 0xD000:
            X = (opcode & 0x0F00) >> 8
            Y = (opcode & 0x00F0) >> 4
            n = opcode & 0x000F
            sprite_x = V[X]
            sprite_y = V[Y]
            V[0xF] = 0
            for row in range(n):
                byte = memory[I + row]
                for col in range(8):
                    bit = (byte >> (7 - col)) & 1
                    if bit == 0:
                        continue
                    target_x = (sprite_x + col) % 64
                    target_y = (sprite_y + row) % 32
                    if framebuffer[target_y][target_x] == 1:
                        V[0xF] = 1

                    framebuffer[target_y][target_x] ^= bit

        elif (opcode & 0xF000) == 0xC000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            V[X] = random.randint(0,255) & kk

        elif (opcode & 0xF000) == 0xF000:
            X = (opcode & 0x0F00) >> 8
            kk = opcode & 0x00FF
            if kk == 0x07:
                V[X] = delay_timer
            elif kk == 0x15:
                delay_timer = V[X]
            elif kk == 0x18:
                sound_timer = V[X]
            elif kk == 0x0A:
                waiting_for_key = True
                waiting_register = X
            elif kk == 0x1E:
                I += V[X]
            elif kk == 0x33:
                hundreds = V[X] // 100
                tens = (V[X] // 10) % 10
                units = V[X] % 10
                memory[I] = hundreds
                memory[I + 1] = tens
                memory[I + 2] = units
            elif kk == 0x29:
                I = 0x50 + V[X] * 5
            elif kk == 0x55:
                memory[I:I + X + 1] = V[0:X + 1]
            elif kk == 0x65:
                V[0:X + 1] = memory[I:I + X + 1]

        elif (opcode & 0xF0FF) == 0xE09E:
            X = (opcode & 0x0F00) >> 8
            if V[X] in chip8_keys:
                pc += 2

        elif (opcode & 0xF0FF) == 0xE0A1:
            X = (opcode & 0x0F00) >> 8
            if V[X] not in chip8_keys:
                pc += 2


        else:
            print(f"unknown: {opcode:04x}")



    for y in range(0,32):
        for x in range(0,64):
            if framebuffer[y][x] == 1:
                pygame.draw.rect(screen, fg, (x * SCALE, y * SCALE, SCALE, SCALE))


    pygame.display.flip()
    clock.tick(60)

pygame.quit()

