import pygame
import json
import math
from collections import defaultdict
from collections import deque

'''
WHAT TO ADD:
    1. Copy/Paste/Drag system with RightClick select 
        ctrl + c = copy | ctrl + v = paste | Left click + move on selected Area to drag
    2. Chuck System
    3. HashLife
'''


# Create Game Window + Base Values / Setup
pygame.init()

WIDTH = 900
HEIGHT = 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

gen = 0
accumulator = 0
GpS = 1
fps = 60

camera_x = 0.0
camera_y = 0.0
zoom = 1.0
dragging = False
last_mouse_pos = (0, 0)

line_width = 1
cell_size = 10 # The size of one cell
alive_cells_on_board = set()

game_running = True
active = True
history = deque(maxlen=100)
redo_history = []

def update_speed(GpS, keys): # Update the GpS on Key Input
    if keys[pygame.K_LEFT] and GpS > 1: # Decrease Speed by 1
        GpS -= 1
    if keys[pygame.K_DOWN] and GpS > 10: # Decrease Speed by 10
        GpS -= 10
    
    if keys[pygame.K_RIGHT] and GpS < 1000: # Increase Speed by 1
        GpS += 1
    if keys[pygame.K_UP] and GpS <= 990: # Increase Speed by 10
        GpS += 10

    return GpS

def save_board(): # Save the game state with "s"
    with open("savedState.txt", "w") as f:
        json.dump(list(alive_cells_on_board), f)

def load_board():
    try:
        with open("savedState.txt", "r") as f:
            return set(tuple(cell) for cell in json.load(f)) # Load the game state with "l"

    except (FileNotFoundError, json.JSONDecodeError):
        return set() # Else create a empty game state if none exists

def draw_grid(cell_size, line_width): # Draw the base grid
    step = cell_size * zoom
    grid_width = max(1, int(line_width * zoom))

    start_x = int(camera_x // step) - 1
    end_x = int(start_x + WIDTH // step + 2)

    for x in range(start_x, end_x): # |
        pos = round(x * step - camera_x)

        pygame.draw.line(screen, (20, 20, 20), (pos, 0), (pos, HEIGHT), grid_width)

    start_y = int(camera_y // step) - 1
    end_y = int(start_y + HEIGHT // step + 2)

    for y in range(start_y, end_y): # -
        pos = round(y * step - camera_y)

        pygame.draw.line(screen, (20, 20, 20), (0, pos), (WIDTH, pos), grid_width)

def draw_cell(cell_size):
    step = cell_size * zoom

    min_x = math.floor(camera_x / step)
    max_x = math.ceil((camera_x + WIDTH) / step)

    min_y = math.floor(camera_y / step)
    max_y = math.ceil((camera_y + HEIGHT) / step)

    for x, y in alive_cells_on_board:
        if min_x <= x <= max_x and min_y <= y <= max_y:
            screen_x = x * step - camera_x
            screen_y = y * step - camera_y

            rect = pygame.Rect(round(screen_x), round(screen_y), round(step), round(step))

            pygame.draw.rect(screen, (255,255,0), rect)

def click_cell(cell_size): # Toggle alive/dead on click
    step = cell_size * zoom
    mx, my = pygame.mouse.get_pos()

    x = math.floor((mx + camera_x) // step)
    y = math.floor((my + camera_y) // step)

    if (x,y) in alive_cells_on_board:
        alive_cells_on_board.discard((x,y))
    else:
        alive_cells_on_board.add((x,y))

DIRECTIONS = [ # Global directions for every nearby cell
    (-1, -1), (-1, 0), (-1, 1),
    ( 0, -1),          ( 0, 1),
    ( 1, -1), ( 1, 0), ( 1, 1)
]

def update(alive): # The REAL GoL rules
    neighbors = defaultdict(int)

    for x, y in alive:
        for dx, dy in DIRECTIONS:
            neighbors[(x+dx, y+dy)] += 1

    new_alive = set()

    for cell, count in neighbors.items():
        if count == 3 or (count == 2 and cell in alive):
            new_alive.add(cell)

    return new_alive

# Print the Controls + Intro
print("Welcome to GoL:\n")
print("Controls:")
print("  's'               = Save")
print("  'l'               = Load")
print("  'r'               = Clear / Reset")
print("  'n'               = Go 1 Step / Gen")
print("  'Right'           = +1 GpS")
print("  'Up'              = +10 GpS")
print("  'Left'            = -1 GpS")
print("  'Down'            = -10 GpS")
print("  'Ctrl + z'        = Undo by 1")
print("  'Ctrl + u'        = Undo by 10")
print("  'Ctrl + y'        = Redo by 1")
print("  'Ctrl + x'        = Redo by 10")
print("  'LeftClick'       = Toggle alive/dead")
print("  'MouseWheel'      = Zoom")
print("  'Hold MouseWheel' = Move cam\n")

# Start of Game
while game_running:
    keys = pygame.key.get_pressed() # Setup the key events

    screen.fill((0, 0, 0)) # Make everything black

    for event in pygame.event.get(): # So you can close the Window lol
        if event.type == pygame.QUIT:
            game_running = False

        if event.type == pygame.KEYDOWN: # Toggle active
            if event.key == pygame.K_SPACE:
                active = not active
            if event.key == pygame.K_s: # Save
                save_board()
                print("Saved!")
            if event.key == pygame.K_l: # Load
                alive_cells_on_board = load_board()
                print("Loaded!")
            if event.key == pygame.K_n and not active: # +1 Step
                history.append(frozenset(alive_cells_on_board))
                redo_history.clear()
                gen += 1
                alive_cells_on_board = update(alive_cells_on_board)
            if event.key == pygame.K_r: # Clear / Reset
                alive_cells_on_board.clear()
                gen = 0
                history.clear()
                redo_history.clear()

            if event.key == pygame.K_z and event.mod & pygame.KMOD_CTRL: # Undo by 1 on ctrl + z press 
                if history:
                    redo_history.append(frozenset(alive_cells_on_board))
                    alive_cells_on_board = set(history.pop())
                    gen = max(0, gen - 1)

            if event.key == pygame.K_u and event.mod & pygame.KMOD_CTRL: # Undo by 10 on ctrl + u press 
                steps = min(10, len(history))

                for _ in range(steps):
                    redo_history.append(frozenset(alive_cells_on_board))
                    alive_cells_on_board = set(history.pop())
                    gen = max(0, gen - 1)

            if event.key == pygame.K_y and event.mod & pygame.KMOD_CTRL: # Redo by 1 on ctrl + y press
                if redo_history:
                    history.append(frozenset(alive_cells_on_board))
                    alive_cells_on_board = set(redo_history.pop())
                    gen += 1

            if event.key == pygame.K_x and event.mod & pygame.KMOD_CTRL: # Redo by 10 on ctrl + x press
                steps = min(10, len(redo_history))

                for _ in range(steps):
                    history.append(frozenset(alive_cells_on_board))

                    alive_cells_on_board = set(redo_history.pop())
                    gen += 1

        if event.type == pygame.MOUSEBUTTONDOWN: # get click input and turn them into board pos + color them with board
            if event.button == 1:  # Leftclick
                click_cell(cell_size)
            if event.button == 2: # Middle Drag
                dragging = True
                last_mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONUP: # Cam drag
            if event.button == 2:
                dragging = False
                
        if event.type == pygame.MOUSEMOTION:
            if dragging:
                mx, my = pygame.mouse.get_pos()

                dx = mx - last_mouse_pos[0]
                dy = my - last_mouse_pos[1]

                camera_x -= dx
                camera_y -= dy

                last_mouse_pos = (mx, my)
        
        if event.type == pygame.MOUSEWHEEL: # Scroll to Zoom relative to the mouse pos
            mouse_x, mouse_y = pygame.mouse.get_pos()

            world_x = (mouse_x + camera_x) / zoom
            world_y = (mouse_y + camera_y) / zoom

            if event.y > 0:
                zoom *= 1.1
            else:
                zoom /= 1.1

            zoom = max(0.1, min(10, zoom))

            camera_x = world_x * zoom - mouse_x
            camera_y = world_y * zoom - mouse_y

    draw_cell(cell_size) # draw each cell

    if cell_size  * zoom >= 4:
        draw_grid(cell_size, line_width) # draw board grid above

    GpS = update_speed(GpS, keys)

    dt = clock.tick(fps) / 1000
    accumulator += dt * GpS
    accumulator = min(accumulator, 10)

    while accumulator >= 1:
        if active:
            history.append(frozenset(alive_cells_on_board))
            redo_history.clear()
            gen += 1
            alive_cells_on_board = update(alive_cells_on_board)

        accumulator -= 1

    pygame.display.set_caption(f"Conways Game Of Life | Gen = {gen} | Alive={len(alive_cells_on_board)} | GpS = {GpS} | FPS = {clock.get_fps():.1f} | Running = {active}") # Update Data
    pygame.display.flip()

pygame.quit()