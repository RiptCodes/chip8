# Attempting to make a chip 8 emulator with additional improvements and features without going over memory budget

import pygame

SCALE = 10

pygame.init()
screen = pygame.display.set_mode((640, 320))
clock = pygame.time.Clock()
running = True

# CPU / Memory
memory = bytearray(4096)
V = bytearray(16)
I = 0
pc = 0x200
stack = []

# log message
def log(text_to_log):
    pass

# ROM Load
with open("roms/IBM Logo.ch8", 'rb') as f:
    rom = f.read()
    memory[pc:pc + len(rom)] = rom #assigning ROM to the Memory location 0x200 - end of ROM 0xFFF


# print(memory[pc:pc+20].hex())

framebuffer = []
for _ in range(32):
    row = [0] * 64
    framebuffer.append(row)


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill("black")

    # fetching and shifting Opcode and decoding
    for _ in range(10):
        opcode = memory[pc] << 8 | memory[pc + 1]
        print(f"{opcode:04x}")
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
                    
        else:
            print(f"unknown: {opcode:04x}")



    for y in range(0,32):
        for x in range(0,64):
            if framebuffer[y][x] == 1:
                pygame.draw.rect(screen, (0,255,0), (x * SCALE, y * SCALE, SCALE, SCALE))


    pygame.display.flip()
    clock.tick(60)

pygame.quit()

