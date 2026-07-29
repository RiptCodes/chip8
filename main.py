# Attempting to make a chip 8 emulator with additional improvements and features without going over memory budget

import pygame

SCALE = 10

pygame.init()
screen = pygame.display.set_mode((640, 320))
clock = pygame.time.Clock()
running = True

framebuffer = []
for _ in range(32):
    row = [0] * 64
    framebuffer.append(row)


for i in range(32):
    framebuffer[i][i] = 1

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
    screen.fill("black")

    for y in range(0,32):
        for x in range(0,64):
            if framebuffer[y][x] == 1:
                pygame.draw.rect(screen, (0,255,0), (x * SCALE, y * SCALE, SCALE, SCALE))


    pygame.display.flip()
    clock.tick(60)

pygame.quit()


# Debugging
with open("roms/test_opcode.ch8", 'rb') as f:
    rom = f.read()

print(f"{len(rom)} bytes")
print(rom[:20].hex())
