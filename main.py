import pygame
import json
import math
from collections import defaultdict
from collections import deque

'''
WHAT TO ADD:
    1. B/S-Rules with Txt-Input before start (Default is B3/S23)
    2. Pattern bib with 0-9 num pad (customize with .rle in folder)
    3. Numpy Vectors
    4. Chunk-System
    5. Multi-Threading/Processing
    6. HashLife
'''

# Create Game Window + Base Values / Setup
pygame.init()

WIDTH = 900
HEIGHT = 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Basic GoL stuffies :3
gen = 0
accumulator = 0
GpS = 1
fps = 60
game_running = True
active = True

# Cam stuff
camera_x = 0.0
camera_y = 0.0
zoom = 1.0
dragging = False
cam_in_center = False
last_mouse_pos = (0, 0)

# Grid/Cell shtuff
line_width = 1
cell_size = 10
alive_cells_on_board = set()

# Copy/Paste Tuffies
alive_selected_cells = set()
clipboard = set()
original_selected_cells = set()
show_preview = False
dragging_selection = False
start_drag_selection = None
was_active_before_edit = False

# Undo/Redo thingy
history = deque(maxlen=1000)
redo_history = []

# Update the GpS on Key Input
def update_speed(GpS, keys):
    if keys[pygame.K_LEFT] and GpS > 1: # Decrease Speed by 1
        GpS -= 1
    if keys[pygame.K_DOWN]: # Decrease Speed by 10 or lower
        for _ in range(10):
            if GpS == 1:
                break
            GpS -= 1
    if keys[pygame.K_RIGHT] and GpS < 1000: # Increase Speed by 1
        GpS += 1
    if keys[pygame.K_UP]: # Increase Speed by 10 or lower
        for _ in range(10):
            if GpS == 1000:
                break
            GpS += 1

    return GpS

def get_mouse_world_pos():
    step = cell_size * zoom
    mx, my = pygame.mouse.get_pos()

    x = math.floor((mx + camera_x) // step)
    y = math.floor((my + camera_y) // step)

    return (x,y)

# Center the cam so you can see every cell 
def center_cam():
    if not alive_cells_on_board: # If everything is dead do nothing
        return

    every_y = [y for _,y in alive_cells_on_board]
    every_x = [x for x,_ in alive_cells_on_board]

    min_x, max_x = min(every_x), max(every_x)
    min_y, max_y = min(every_y), max(every_y)

    pattern_height = (max_y - min_y + 1) * cell_size
    pattern_width = (max_x - min_x + 1) * cell_size

    global zoom, camera_x, camera_y
    zoom = min(10, max(0.055, min(WIDTH / pattern_width, HEIGHT / pattern_height) * 0.9)) # Do zoom so it zooms good enough that everything shows + edge empty :3

    center_y = (min_y + max_y + 1) / 2 * cell_size
    center_x = (min_x + max_x + 1) / 2 * cell_size

    camera_x = center_x * zoom - WIDTH / 2
    camera_y = center_y * zoom - HEIGHT / 2

# Save the game state with "s"
def save_rle(file):
    if not alive_cells_on_board:
        return

    xe = [x for x,_ in alive_cells_on_board]
    ye = [y for _,y in alive_cells_on_board]
    max_x, min_x = max(xe), min(xe)
    max_y, min_y = max(ye), min(ye)

    width = max_x - min_x + 1
    height = max_y - min_y + 1

    lines_out = []
    for y in range(min_y, max_y + 1):
        row_str = ""
        run_char = None
        run_count = 0

        for x in range(min_x, max_x + 1):
            cell_char = "o" if (x, y) in alive_cells_on_board else "b"

            if cell_char == run_char:
                run_count += 1
            else:
                if run_char is not None:
                    row_str += (str(run_count) if run_count > 1 else "") + run_char
                run_char = cell_char
                run_count = 1

        if run_char == "o": # Add an last alive if alive else dont add dead
            row_str += (str(run_count) if run_count > 1 else "") + run_char

        lines_out.append(row_str)

    pattern_str = "$".join(lines_out) + "!"

    with open(file, "w") as f:
        f.write(f"x = {width}, y = {height}, rule = B3/S23\n") # Change Rule later when you have a B/S mask thingy :3
        f.write(pattern_str + "\n")

# Load the rle file with "l"
def load_rle(file):
    try:
        global alive_cells_on_board, gen

        new_alive = set()
        x, y = 0, 0

        with open(file, "r") as f: # Read the file
            lines = f.readlines()

        pattern_lines = []
        for line in lines: # Ignore comments + the Header (for now)
            line = line.strip()
            if line.startswith("#"):
                continue
            if line.startswith("x"):
                continue
            pattern_lines.append(line)

        pattern_str = "".join(pattern_lines) # Make it 1 Line

        count_str = ""
        for char in pattern_str:
            if char.isdigit():
                count_str += char
            elif char == "b":
                count = int(count_str) if count_str else 1
                x += count
                count_str = ""
            elif char == "o":
                count = int(count_str) if count_str else 1
                for i in range(count):
                    new_alive.add((x + i, y))
                x += count
                count_str = ""
            elif char == "$":
                count = int(count_str) if count_str else 1
                x = 0
                y += count
            elif char == "!":
                break

        alive_cells_on_board = new_alive
        gen = 0
        center_cam()

    except (FileNotFoundError, json.JSONDecodeError):
        return set() # Else create a empty game state if none exists

# Draw the base grid
def draw_grid(cell_size, line_width):
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

# Draw a cell (to Loop over every living cell and draw it)
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

# Toggle alive/dead on click
def click_cell():
    global has_selection, dragging_selection, start_drag_selection, was_active_before_edit, active, original_selected_cells
    
    x, y = get_mouse_world_pos()

    if has_selection and not point_in_selection(x,y):
        has_selection = False
        active = was_active_before_edit
        return
    elif has_selection:
        dragging_selection = True
        start_drag_selection = (x,y)
        original_selected_cells = get_selection()
        return

    if (x,y) in alive_cells_on_board:
        alive_cells_on_board.discard((x,y))
    else:
        alive_cells_on_board.add((x,y))

# Global directions for every nearby cell
DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    ( 0, -1),          ( 0, 1),
    ( 1, -1), ( 1, 0), ( 1, 1)
]

# The REAL GoL B/S rules
def update(alive):
    neighbors = defaultdict(int)

    for x, y in alive:
        for dx, dy in DIRECTIONS:
            neighbors[(x+dx, y+dy)] += 1

    new_alive = set()

    for cell, count in neighbors.items():
        if count == 3 or (count == 2 and cell in alive): # B or S + in alive then add
            new_alive.add(cell)

    return new_alive

# The Copy/Paste/Drag thingys
selecting = False
has_selection = False
start = None
end = None

def select_field(event):
    global selecting, has_selection, dragging_selection, start, end, alive_selected_cells, clipboard, start_drag_selection, was_active_before_edit, active, original_selected_cells
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 3 and not dragging_selection: # Start Selecting
            x, y = get_mouse_world_pos()

            start = (x,y)
            end = start
            has_selection = False
            selecting = True
            was_active_before_edit = active
            active = False

    if event.type == pygame.MOUSEBUTTONUP:
        if event.button == 3: # Stop Selecting
            selecting = False
            has_selection = True
            alive_selected_cells = get_selection()
        if dragging_selection and event.button == 1: # Stop Drag
            dragging_selection = False
            has_selection = False
            x_min = min(start[0], end[0])
            y_min = min(start[1], end[1])
            x, y = get_mouse_world_pos()
            delta_x = x - start_drag_selection[0]
            delta_y = y - start_drag_selection[1]

            old_positions = {
                (dx + x_min, dy + y_min)
                for (dx, dy) in original_selected_cells
            }

            new_positions = {
                (dx + x_min + delta_x, dy + y_min + delta_y)
                for (dx, dy) in alive_selected_cells
            }

            alive_cells_on_board.difference_update(old_positions)
            alive_cells_on_board.update(new_positions)

            active = was_active_before_edit

    if event.type == pygame.MOUSEMOTION:
        if selecting: # while you hold rightclick select duh
            x, y = get_mouse_world_pos()
            end = (x,y)

    if event.type == pygame.KEYDOWN:
        if has_selection and event.key == pygame.K_d: # Delete Selected
            x_min = min(start[0], end[0])
            y_min = min(start[1], end[1])
            for (dx, dy) in original_selected_cells:
                alive_cells_on_board.discard((dx + x_min, dy + y_min))
            dragging_selection = False
            has_selection = False
            active = was_active_before_edit

        if event.key == pygame.K_e:
            if dragging_selection: # Rotate the drag | CW
                xs = [x for x, _ in alive_selected_cells]
                ys = [y for _, y in alive_selected_cells]
                center_x = round((min(xs) + max(xs)) / 2)
                center_y = round((min(ys) + max(ys)) / 2)
                alive_selected_cells = {
                    ((y - center_y) + center_x, (-x + center_x) + center_y)
                    for (x, y) in alive_selected_cells
                }
            elif clipboard: # Rotate the Copy to Paste | CW
                xs = [x for x, _ in clipboard]
                ys = [y for _, y in clipboard]
                center_x = round((min(xs) + max(xs)) / 2)
                center_y = round((min(ys) + max(ys)) / 2)
                clipboard = {
                    ((y - center_y) + center_x, (-x + center_x) + center_y)
                    for (x, y) in clipboard
                }

        if event.key == pygame.K_q:
            if dragging_selection: # Rotate the drag | CCW
                xs = [x for x, _ in alive_selected_cells]
                ys = [y for _, y in alive_selected_cells]
                center_x = round((min(xs) + max(xs)) / 2)
                center_y = round((min(ys) + max(ys)) / 2)
                alive_selected_cells = {
                    ((-y + center_y) + center_x, (x - center_x) + center_y)
                    for (x, y) in alive_selected_cells
                }
            elif clipboard: # Rotate the Copy to Paste | CCW
                xs = [x for x, _ in clipboard]
                ys = [y for _, y in clipboard]
                center_x = round((min(xs) + max(xs)) / 2)
                center_y = round((min(ys) + max(ys)) / 2)
                clipboard = {
                    ((-y + center_y) + center_x, (x - center_x) + center_y)
                    for (x, y) in clipboard
                }

        if event.key == pygame.K_w:
            if dragging_selection: # Mirror the drag left right
                xs = [x for x, _ in alive_selected_cells]
                center_x = round((min(xs) + max(xs)) / 2)
                alive_selected_cells = {
                    (2 * center_x - x, y)
                    for (x, y) in alive_selected_cells
                }
            elif clipboard: # Mirror the Copy to Paste left right
                xs = [x for x, _ in clipboard]
                center_x = round((min(xs) + max(xs)) / 2)
                clipboard = {
                    (2 * center_x - x, y)
                    for (x, y) in clipboard
                }

        if event.key == pygame.K_2:
            if dragging_selection: # Mirror the drag up down
                ys = [y for y, _ in alive_selected_cells]
                center_y = round((min(ys) + max(ys)) / 2)
                alive_selected_cells = {
                    (x, 2 * center_y - y)
                    for (x, y) in alive_selected_cells            
                }
            elif clipboard: # Mirror the Copy to Paste up down
                ys = [y for _, y in clipboard]
                center_y = round((min(ys) + max(ys)) / 2)
                clipboard = {
                    (x, 2 * center_y - y)
                    for (x, y) in clipboard
                }

# draw the select rect with start(x,y) and end(x,y)
def draw_selection():
    step = cell_size * zoom
    if selecting or has_selection:
        x_min = min(start[0], end[0])
        y_min = min(start[1], end[1])
        width = abs(end[0] - start[0]) + 1
        height = abs(end[1] - start[1]) + 1

        rect = pygame.Rect(
            round(x_min * step - camera_x),
            round(y_min * step - camera_y),
            round(width * step),
            round(height * step)
        )

        fill_surface = pygame.Surface((round(width*step), round(height*step)), pygame.SRCALPHA)
        fill_surface.fill((0, 32, 255, 80))  # RGBA
        
        screen.blit(fill_surface, (rect.x, rect.y))

        pygame.draw.rect(screen, (0,32,255), rect, max(1, int(line_width * zoom)))

# Check if the cell is in the rect
def point_in_selection(x,y):
    x_min = min(start[0], end[0])
    y_min = min(start[1], end[1])
    x_max = max(start[0], end[0])
    y_max = max(start[1], end[1])
    return x_min <= x <= x_max and y_min <= y <= y_max

# Get every alive cell in rect
def get_selection():
    x_min = min(start[0], end[0])
    y_min = min(start[1], end[1])
    
    return {(x - x_min, y - y_min) for (x, y) in alive_cells_on_board if point_in_selection(x, y)}

# Paste the clipboard
def paste_cells():
    x, y = get_mouse_world_pos()

    cordinates_clipboard = {(dx + x, dy + y) for (dx, dy) in clipboard}

    alive_cells_on_board.update(cordinates_clipboard)

# Draw a lil preview where/what you will paste
def draw_paste_preview():
    step = cell_size * zoom
    x, y = get_mouse_world_pos()

    preview_cells = {(dx + x, dy + y) for (dx, dy) in clipboard}

    for dx, dy in preview_cells:
        fill_surface = pygame.Surface((round(step), round(step)), pygame.SRCALPHA)
        fill_surface.fill((255, 255, 0, 80))  # RGBA
        
        screen.blit(fill_surface, (round(dx*step - camera_x), round(dy*step - camera_y)))

def draw_drag_preview():
    if dragging_selection:
        step = cell_size * zoom
        x, y = get_mouse_world_pos()
        
        delta_x = x - start_drag_selection[0]
        delta_y = y - start_drag_selection[1]
        x_min = min(start[0], end[0])
        y_min = min(start[1], end[1])

        for (dx, dy) in alive_selected_cells:
            absolute_x = dx + x_min 
            absolute_y = dy + y_min
            new_x = absolute_x + delta_x
            new_y = absolute_y + delta_y

            fill_surface = pygame.Surface((round(step), round(step)), pygame.SRCALPHA)
            fill_surface.fill((255, 255, 0, 80))
            screen.blit(fill_surface, (round(new_x*step - camera_x), round(new_y*step - camera_y)))

    

# Print the Controls + Intro
print("Welcome to GoL:\n")
print("Controls:")
print("  's'                    = Save .rle file")
print("  'l'                    = Load .rle file")
print("  'r'                    = Clear / Reset")
print("  'n'                    = Go 1 Step / Gen")
print("  'f'                    = Center cam once")
print("  'g'                    = Toggle center cam")
print("  'p'                    = Show Paste Preview")
print("  'e'                    = Turn CW")
print("  'q'                    = Turn CCW")
print("  'w'                    = Mirror left right")
print("  '2'                    = Mirror up down")
print("  'd + Selected'         = Delete")
print("  'Right'                = +1 GpS")
print("  'Up'                   = +10 GpS")
print("  'Left'                 = -1 GpS")
print("  'Down'                 = -10 GpS")
print("  'Ctrl + z'             = Undo by 1")
print("  'Ctrl + u'             = Undo by 10")
print("  'Ctrl + y'             = Redo by 1")
print("  'Ctrl + x'             = Redo by 10")
print("  'LeftClick'            = Toggle alive/dead")
print("  'LeftClick + Selected' = Drag")
print("  'Hold Rightclick'      = Select")
print("  'MouseWheel'           = Zoom")
print("  'Hold MouseWheel'      = Move cam\n")

# Start of Game
while game_running:
    keys = pygame.key.get_pressed() # Setup the key events

    screen.fill((0, 0, 0)) # Make everything black

    for event in pygame.event.get(): 
        if event.type == pygame.QUIT: # So you can close the Window lol
            game_running = False

        if event.type == pygame.KEYDOWN: # Toggle active
            if event.key == pygame.K_SPACE and not has_selection and not selecting and not dragging_selection:
                active = not active
            if event.key == pygame.K_s: # Save
                save_rle("RLE/game.rle") # Change if you want a different filename for the saved .rle 
                print("Saved .rle!")
            if event.key == pygame.K_l: # Load
                load_rle("RLE/gosper_glider_gun.rle") # Change if you want a different loaded .rle file
                print("Loaded .rle!")
            if event.key == pygame.K_n and not active and not has_selection and not selecting and not dragging_selection: # +1 Step
                history.append(frozenset(alive_cells_on_board))
                redo_history.clear()
                gen += 1
                alive_cells_on_board = update(alive_cells_on_board)
                if cam_in_center:
                    center_cam()
            if event.key == pygame.K_r: # Clear / Reset
                alive_cells_on_board.clear()
                gen = 0
                history.clear()
                redo_history.clear()
                if has_selection or selecting or dragging_selection:
                    has_selection = False
                    selecting = False
                    dragging_selection = False
                    active = was_active_before_edit

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

            if event.key == pygame.K_c and event.mod & pygame.KMOD_CTRL and not dragging_selection: # Copy
                if has_selection:
                    clipboard = alive_selected_cells.copy()
                    has_selection = False
                    active = was_active_before_edit

            if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL and not has_selection and not selecting and not dragging_selection: # Paste
                paste_cells()

            if event.key == pygame.K_p:
                show_preview = not show_preview

            if event.key == pygame.K_g: # Toggle center cam with 'g'
                cam_in_center = not cam_in_center

            if event.key == pygame.K_f: # Center cam once with 'f'
                center_cam()

        if event.type == pygame.MOUSEBUTTONDOWN: # get click input and turn them into board pos + color them with board
            if event.button == 1:  # Leftclick
                click_cell()
            if event.button == 2: # Middle Drag
                dragging = True
                last_mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONUP: # Cam drag
            if event.button == 2:
                dragging = False

        if event.type == pygame.MOUSEMOTION:
            if dragging: # cam drag
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

            zoom = max(0.055, min(10, zoom))

            camera_x = world_x * zoom - mouse_x
            camera_y = world_y * zoom - mouse_y

        select_field(event)

    if show_preview: # Draw the preview if Toggled True
        draw_paste_preview()

    draw_drag_preview()

    draw_cell(cell_size) # draw each cell

    if cell_size  * zoom >= 4:
        draw_grid(cell_size, line_width) # draw board grid above

    draw_selection()

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
            if cam_in_center:
                    center_cam()

        accumulator -= 1

    pygame.display.set_caption(f"Conways Game Of Life | Gen = {gen} | Alive={len(alive_cells_on_board)} | GpS = {GpS} | FPS = {clock.get_fps():.1f} | Running = {active} | Cam centered = {cam_in_center} | Show Preview = {show_preview}") # Update Data
    pygame.display.flip()

pygame.quit()