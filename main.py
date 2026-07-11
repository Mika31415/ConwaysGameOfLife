import pygame
import json
import random # temp

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
game_running = True
active = True
last_update = pygame.time.get_ticks()

def update_speed(GpS, keys):
    if keys[pygame.K_LEFT] and GpS > 1: # Decrease Speed by 1
        GpS -= 1
    if keys[pygame.K_DOWN] and GpS > 10: # Decrease Speed by 10
        GpS -= 10
    
    if keys[pygame.K_RIGHT] and GpS < 1000: # Increase Speed by 1
        GpS += 1
    if keys[pygame.K_UP] and GpS <= 990: # Increase Speed by 10
        GpS += 10

    return GpS

def save_board(board):
    with open("savedState.txt", "w") as f:
        f.write("[\n")
        for i, row in enumerate(board):
            f.write("    " + json.dumps(row))
            if i < len(board) - 1:
                f.write(",")
            f.write("\n")
        f.write("]\n")

def load_board():
    try:
        with open("savedState.txt", "r") as f:
            content = f.read()

        if content.strip():
            return json.loads(content)

    except FileNotFoundError:
        pass

    size = 100 # change later or del 
    return [[random.randint(0,1) for _ in range(size)] for _ in range(size)] # temp replace later with all 0

board = load_board()

print("Start Board:") # temp
for row in board:
    print(row)

def update_board(board): # The REAL GoL rules
    new_board = [[0 for _ in range(len(board[0]))] for _ in range(len(board))]

    directions = [ # Define every nearby cell 
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),          ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1)
    ]

    for y, row in enumerate(board):
        for x, cell in enumerate(row):
            nearby_active_cells = 0

            for dx, dy in directions: # Loop through every nearby cell
                nx = x + dx
                ny = y + dy

                if 0 <= nx < len(board[0]) and 0 <= ny < len(board):
                    if board[ny][nx] == 1:
                        nearby_active_cells += 1

            if cell == 0: # Birth
                if nearby_active_cells == 3:
                    new_board[y][x] = 1
            else:
                if nearby_active_cells < 2: # Underpopulation
                    new_board[y][x] = 0
                elif nearby_active_cells <= 3: # Survive
                    new_board[y][x] = 1
                else:  # Overpopulation
                    new_board[y][x] = 0

    return new_board

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
            if event.key == pygame.K_s:
                save_board(board)
                print("Saved!")

    # draw board grid
    # get click input and turn them into board pos + color them with board
    # add zoom? 
                
    GpS = update_speed(GpS, keys)

    dt = clock.tick(fps) / 1000
    accumulator += dt * GpS

    while accumulator >= 1: # Run the actual Simulation
        if active:
            gen += 1
            board = update_board(board)
            print(f"\ngen {gen} Board:") # temp
            for row in board:
                print(row)
        accumulator -= 1

    pygame.display.set_caption(f"Conways Game Of Life | Generation = {gen} | GpS = {GpS} | Running = {active}") # Update Data
    clock.tick(fps)

pygame.quit()