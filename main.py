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
with open("roms/test_opcode.ch8", 'rb') as f:
    rom = f.read()
    memory[pc:pc + len(rom)] = rom #assigning ROM to the Memory location 0x200 - end of ROM 0xFFF


print(memory[pc:pc+20].hex())

framebuffer = []
for _ in range(32):
    row = [0] * 64
    framebuffer.append(row)


# while running:
#     for event in pygame.event.get():
#         if event.type == pygame.QUIT:
#             running = False

#     screen.fill("black")

#     for y in range(0,32):
#         for x in range(0,64):
#             if framebuffer[y][x] == 1:
#                 pygame.draw.rect(screen, (0,255,0), (x * SCALE, y * SCALE, SCALE, SCALE))


#     pygame.display.flip()
#     clock.tick(60)

# pygame.quit()

