from chip8.cpu import Chip8

def make_cpu(opcode, **state):
    c = Chip8()
    c.memory[0x200] = opcode >> 8
    c.memory[0x201] = opcode & 0xFF
    for k, v in state.items():
        setattr(c, k, v)
    return c

def test_6xkk_loads_register():
    c = make_cpu(0x6A42)
    c.step()
    assert c.V[0xA] == 0x42
    assert c.pc == 0x202

def test_8xy4_add_with_carry():
    c = make_cpu(0x8014)
    c.V[0] = 200; c.V[1] = 100
    c.step()
    assert c.V[0] == 44        
    assert c.V[0xF] == 1      

def test_8xy5_sub_no_borrow():
    c = make_cpu(0x8015)
    c.V[0] = 10; c.V[1] = 3
    c.step()
    assert c.V[0] == 7
    assert c.V[0xF] == 1      

def test_fx33_bcd():
    c = make_cpu(0xF033)
    c.V[0] = 234
    c.I = 0x300
    c.step()
    assert c.memory[0x300] == 2
    assert c.memory[0x301] == 3
    assert c.memory[0x302] == 4

def test_dxyn_collision_flag():
    c = make_cpu(0xD001)
    c.I = 0x300
    c.memory[0x300] = 0x80    
    c.framebuffer[0][0] = 1    
    c.step()
    assert c.framebuffer[0][0] == 0   
    assert c.V[0xF] == 1 