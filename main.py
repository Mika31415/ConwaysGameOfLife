# Base Modules
import pygame
import math
import numpy as np
from collections import deque
import tkinter as tk

# Own Modules
import modules.ux.settings_window as settings_window

'''
WHAT TO ADD:
    1. Numpy Vectors (Done ig)
    2. Chunk-System
    3. Multi-Threading/Processing
    4. HashLife
'''
'''
WHAT TO FIX/OPTIMIZE:
    1. save_rle -> Numpy vectors (makes saving faster)
    2. history_1_step -> Save Deltas (makes history faster)
    3. center_cam -> Update for each add/remove cell instead of every CAM_CENTER_EVERY_GEN (makes it faster)
    4. Use State Enums (makes it cleaner)
    5. Use Modules instead of 1 big File (makes it cleaner)
    6. grow_if_needed -> also shrink when pattern gets smaller (saves memory)
    7. Cache preview/selection Surfaces instead of recreating every frame (makes it faster)
'''

# ---------------------------------- Change freely for Hotkeys etc. -------------------------------------
NUMPAD_HOTKEYS = {
    pygame.K_KP0: "Numpad/gosper_glider_gun.rle", # Hotkey Numpad 0
    pygame.K_KP1: "Numpad/eater.rle", # Hotkey Numpad 1
    pygame.K_KP2: "Numpad/buckaroo.rle", # Hotkey Numpad 2
    pygame.K_KP3: "Numpad/60p_glider_gun.rle", # Hotkey Numpad 3
    pygame.K_KP4: "Numpad/60p_and_gate.rle", # Hotkey Numpad 4
    pygame.K_KP5: "Numpad/60p_not_gate.rle", # Hotkey Numpad 5
    pygame.K_KP6: "Numpad/60p_or_gate.rle", # Hotkey Numpad 6
    pygame.K_KP7: "Numpad/duplicator.rle", # Hotkey Numpad 7
    pygame.K_KP8: "Numpad/60p_xor_gate.rle", # Hotkey Numpad 8
    pygame.K_KP9: "Numpad/"  # Hotkey Numpad 9
}
LOADING_FILE = "RLE/OCTA.rle" # Change if you want a different loaded .rle file
SAVING_FILE = "RLE/game.rle" # Change if you want a different filename for the saved .rle

WIDTH = 1000 # Game Window Width | Base = 1000
HEIGHT = 1000 # Game Window Height | Base = 1000

MIN_ZOOM = 0.055 # Minimum Zoom Level | Base = 0.055
MAX_ZOOM = 10.0 # Maximum Zoom Level | Base = 10.0
CAM_CENTER_EVERY_GEN = 10 # Center the cam every X generations (for performance reasons) | Base = 10

HISTORY_LIMIT = 1000 # Limit of the Undo/Redo History
HISTORY_SAVE_EVERY_GEN = 10 # Save history every X generations (for performance reasons) | Base = 10

GROWTH_MARGIN = 50 # The margin around the alive cells to determine the simulation grid size | Base = 50 
# ------------------------------------------------------------------------------------------------------

# Create Game Window + Base Values / Setup
pygame.init()

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
current_grid = None
grid_offset_x = 0
grid_offset_y = 0
needs_sync = False

# Simulation Grid thingyyyys :333
sim_grid = None
sim_offset_x = 0
sim_offset_y = 0
set_is_old = False

# Copy/Paste Tuffies
alive_selected_cells = set()
clipboard = set()
original_selected_cells = set()
show_preview = False
dragging_selection = False
start_drag_selection = None
was_active_before_edit = False

# Undo/Redo thingy
history = deque(maxlen=HISTORY_LIMIT)
redo_history = deque(maxlen=HISTORY_LIMIT)

# The Copy/Paste/Drag thingys
selecting = False
has_selection = False
start = None
end = None

# Base birth values
birth_values = {3}
survive_values = {2, 3}

# Settings Window function to apply new rules from the settings window
def apply_new_rules(birth, survive):
    global birth_values, survive_values
    birth_values = birth
    survive_values = survive

settings_root = settings_window.create_settings_window(apply_new_rules) # create the root with the settings window

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

# Another helpy func with gives the step num
def get_step():
    return max(1, round(cell_size * zoom))

# And another helpy func to calc the min/max cordinates of x and y of the alive cells
def get_min_max_coords(cells):
    if not cells:
        return (0, 0, 0, 0)

    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    return (min_x, max_x, min_y, max_y)

# A lil help function to get the mouse pos in world cordinates
def get_mouse_world_pos():
    step = get_step()
    mx, my = pygame.mouse.get_pos()

    x = math.floor((mx + camera_x) // step)
    y = math.floor((my + camera_y) // step)

    return (x,y)

# Center the cam so you can see every cell 
def center_cam():
    make_set_synced()

    if not alive_cells_on_board: # If everything is dead do nothing
        return

    min_x, max_x, min_y, max_y = get_min_max_coords(alive_cells_on_board)

    pattern_height = (max_y - min_y + 1) * cell_size
    pattern_width = (max_x - min_x + 1) * cell_size

    global zoom, camera_x, camera_y
    zoom = min(MAX_ZOOM, max(MIN_ZOOM, min(WIDTH / pattern_width, HEIGHT / pattern_height) * 0.9)) # Do zoom so it zooms good enough that everything shows + edge empty :3

    center_y = (min_y + max_y + 1) / 2 * cell_size
    center_x = (min_x + max_x + 1) / 2 * cell_size

    camera_x = center_x * zoom - WIDTH / 2
    camera_y = center_y * zoom - HEIGHT / 2

# Save the game state with "s"
def save_rle(file):
    if not alive_cells_on_board:
        return

    min_x, max_x, min_y, max_y = get_min_max_coords(alive_cells_on_board)

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

    try:
        with open(file, "w") as f:
            birth_str = "".join(str(n) for n in sorted(birth_values))
            survive_str = "".join(str(n) for n in sorted(survive_values))
            f.write(f"x = {width}, y = {height}, rule = B{birth_str}/S{survive_str}\n")
            f.write(pattern_str + "\n")
    except (OSError, PermissionError):
        print(f"Couldn't save the file: {file}")

# Load the rle file with "l"
def load_rle(file):
    try:
        global birth_values, survive_values

        new_alive = set()
        x, y = 0, 0

        with open(file, "r") as f: # Read the file
            lines = f.readlines()

        pattern_lines = []
        for line in lines: # Ignore comments
            line = line.strip()
            if line.startswith("#"):
                continue
            if line.startswith("x"): # read the rules
                rules = line.split()[-1]
                birth_rule_str = rules.split("/")[0]
                survive_rule_str = rules.split("/")[1]
                birth_values = {int(char) for char in birth_rule_str if char.isdigit()}
                survive_values = {int(char) for char in survive_rule_str if char.isdigit()}
                print(f"Loading changed rules to: {rules}")
                continue 
            pattern_lines.append(line)

        pattern_str = "".join(pattern_lines) # Make it 1 Line

        count_str = ""
        for char in pattern_str:
            if char.isdigit():
                count_str += char
            elif char == "b" or char == ".":
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

        return new_alive

    except (FileNotFoundError, IsADirectoryError, PermissionError, IndexError):
        print(f"Couldn't load the file: {file}")
        return set() # Else create a empty game state if none exists
    
# Numpad hotkeys:
def numpad(event):
    global clipboard
    if event.type == pygame.KEYDOWN:
        if event.key in NUMPAD_HOTKEYS:
            file = NUMPAD_HOTKEYS[event.key]
            clipboard = load_rle(file)

# Draw the base grid
def draw_grid(line_width):
    step = get_step()
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

# Toggle alive/dead on click
def click_cell():
    global has_selection, dragging_selection, start_drag_selection, was_active_before_edit, active, original_selected_cells
    make_set_synced()

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

# Turn Set in Numpy Array
def cells_to_array(alive_cells, padding=1):
    if not alive_cells:
        return None, 0, 0
    
    coords = np.array(list(alive_cells))  # Shape: (n, 2) -> | 0 = x, | 1 = y
    xs = coords[:, 0]
    ys = coords[:, 1]
    
    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()
    
    width = (x_max - x_min + 1) + 2 * padding
    height = (y_max - y_min + 1) + 2 * padding
    
    grid = np.zeros((height, width), dtype=np.uint8)
    
    grid_x = xs - x_min + padding
    grid_y = ys - y_min + padding
    grid[grid_y, grid_x] = 1 
    
    return grid, x_min - padding, y_min - padding

# Setup Neighbor roll with a dictionary for customablity)

# Update the Neighbors using the Numpy roll
def count_neighbors(grid):
    n = np.zeros_like(grid, dtype=np.uint8)
    offsets = settings_window.give_neighbor_offsets()
    for dx, dy in offsets:
        n += np.roll(np.roll(grid, dy, axis=0), dx, axis=1)
    return n    

def array_update(grid, birth_values, survive_values):
    neighbor_count = count_neighbors(grid)

    birth_mask = np.isin(neighbor_count, list(birth_values)) & (grid == 0)
    survive_mask = np.isin(neighbor_count, list(survive_values)) & (grid == 1)

    return (birth_mask | survive_mask).astype(np.uint8)

# Convert the Numpy Array back in a setty set :P
def array_to_cells(grid, offset_x, offset_y):
    ys, xs = np.where(grid == 1)
    xs = xs + offset_x
    ys = ys + offset_y
    return set(zip(xs.tolist(), ys.tolist()))

# Sync the set with the grid (if it needs to lol)
def make_set_synced():
    global alive_cells_on_board, set_is_old
    if set_is_old: # If its old update
        if sim_grid is not None:
            alive_cells_on_board = array_to_cells(sim_grid, sim_offset_x, sim_offset_y)
        else:
            alive_cells_on_board = set()
        set_is_old = False

# Update the sizes with margin if needed
def grow_if_needed(grid, offset_x, offset_y):
    h, w = grid.shape
    edge_alive = (
        grid[0:2, :].any() or # Top edge
        grid[-2:, :].any() or # Bottom edge
        grid[:, 0:2].any() or # Left edge
        grid[:, -2:].any()    # Right edge
    )
    if not edge_alive:
        return grid, offset_x, offset_y

    new_h, new_w = h + GROWTH_MARGIN * 2, w + GROWTH_MARGIN * 2
    new_grid = np.zeros((new_h, new_w), dtype=np.uint8)
    new_grid[GROWTH_MARGIN:GROWTH_MARGIN + h, GROWTH_MARGIN:GROWTH_MARGIN + w] = grid
    return new_grid, offset_x - GROWTH_MARGIN, offset_y - GROWTH_MARGIN

# Sync the grid
def sync_grid_from_set():
    global sim_grid, sim_offset_x, sim_offset_y, current_grid, grid_offset_x, grid_offset_y, set_is_old
    grid, offset_x, offset_y = cells_to_array(alive_cells_on_board, padding=1)
    sim_grid = grid
    sim_offset_x, sim_offset_y = offset_x, offset_y
    current_grid = grid
    grid_offset_x, grid_offset_y = offset_x, offset_y
    set_is_old = False

# THE ENTIER UPDATE CELLS (just with fast numpy now + faster)
def numpy_update():
    global sim_grid, sim_offset_x, sim_offset_y, set_is_old, current_grid, grid_offset_x, grid_offset_y

    if sim_grid is None:
        return # do nuthing if nuthing there

    sim_grid, sim_offset_x, sim_offset_y = grow_if_needed(sim_grid, sim_offset_x, sim_offset_y)
    sim_grid = array_update(sim_grid, birth_values, survive_values)

    current_grid = sim_grid
    grid_offset_x, grid_offset_y = sim_offset_x, sim_offset_y

    set_is_old = True

# Fast Numpy Draw cells (one big image not many smoll images)
def draw_cells_from_grid():
    if current_grid is None:
        return
    step = get_step()

    grid_h, grid_w = current_grid.shape

    # Visible area
    view_min_x = math.floor(camera_x / step)
    view_max_x = math.ceil((camera_x + WIDTH) / step)
    view_min_y = math.floor(camera_y / step)
    view_max_y = math.ceil((camera_y + HEIGHT) / step)

    # World Cordinates of cells
    x_start = max(0, view_min_x - grid_offset_x)
    x_end = min(grid_w, view_max_x - grid_offset_x)
    y_start = max(0, view_min_y - grid_offset_y)
    y_end = min(grid_h, view_max_y - grid_offset_y)

    if x_start >= x_end or y_start >= y_end:
        return 

    visible_grid = current_grid[y_start:y_end, x_start:x_end]

    scaled = np.kron(visible_grid, np.ones((step, step), dtype=np.uint8))
    cell_color = settings_window.give_cell_color()  # Get the current cell color from settings
    rgb = np.stack([scaled*cell_color[0], scaled*cell_color[1], scaled*cell_color[2]], axis=-1)

    surf = pygame.surfarray.make_surface(rgb.swapaxes(0,1))
    screen_x = round((x_start + grid_offset_x) * step - camera_x)
    screen_y = round((y_start + grid_offset_y) * step - camera_y)
    screen.blit(surf, (screen_x, screen_y))

# Helpy functions for rotate/drag
def get_center_for(thing):
    if not thing:
        return (0, 0)

    xs = [x for x, _ in thing]
    ys = [y for _, y in thing]

    center_x = round((min(xs) + max(xs)) / 2)
    center_y = round((min(ys) + max(ys)) / 2)

    return (center_x, center_y)

def rotate_cells(thing, clockwise=True): # rotate around da center
    if not thing:
        return set()

    center_x, center_y = get_center_for(thing)

    if clockwise:
        return {((y - center_y) + center_x, (-x + center_x) + center_y) for (x, y) in thing}
    else:
        return {((-y + center_y) + center_x, (x - center_x) + center_y) for (x, y) in thing}

def mirror_cells(thing, x_axis=True): # mirror around the center
    if not thing:
        return set()

    center_x, center_y = get_center_for(thing)

    if x_axis:
        return {(2 * center_x - x, y) for (x, y) in thing}
    else:
        return {(x, 2 * center_y - y) for (x, y) in thing}
    
def select_field(event):
    global selecting, has_selection, dragging_selection, start, end, alive_selected_cells, clipboard, start_drag_selection, was_active_before_edit, active, original_selected_cells, needs_sync
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
        make_set_synced()
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
            needs_sync = True

    if event.type == pygame.MOUSEMOTION:
        if selecting: # while you hold rightclick select duh
            x, y = get_mouse_world_pos()
            end = (x,y)

    if event.type == pygame.KEYDOWN:
        if has_selection and event.key == pygame.K_BACKSPACE: # Delete Selected
            x_min = min(start[0], end[0])
            y_min = min(start[1], end[1])
            for (dx, dy) in original_selected_cells if dragging_selection else alive_selected_cells:
                alive_cells_on_board.discard((dx + x_min, dy + y_min))
            dragging_selection = False
            has_selection = False
            active = was_active_before_edit
            needs_sync = True

        if event.key == pygame.K_e:
            if dragging_selection and alive_selected_cells: # Rotate the drag | CW
                alive_selected_cells = rotate_cells(alive_selected_cells, clockwise=True)
            elif clipboard: # Rotate the Copy to Paste | CW
                clipboard = rotate_cells(clipboard, clockwise=True)

        if event.key == pygame.K_q:
            if dragging_selection and alive_selected_cells: # Rotate the drag | CCW
                alive_selected_cells = rotate_cells(alive_selected_cells, clockwise=False)
            elif clipboard: # Rotate the Copy to Paste | CCW
                clipboard = rotate_cells(clipboard, clockwise=False)

        if event.key == pygame.K_w:
            if dragging_selection and alive_selected_cells: # Mirror the drag left right
                alive_selected_cells = mirror_cells(alive_selected_cells, x_axis=False)
            elif clipboard: # Mirror the Copy to Paste left right
                clipboard = mirror_cells(clipboard, x_axis=False)

        if event.key == pygame.K_2:
            if dragging_selection and alive_selected_cells: # Mirror the drag up down
                alive_selected_cells = mirror_cells(alive_selected_cells, x_axis=True)
            elif clipboard: # Mirror the Copy to Paste up down
                clipboard = mirror_cells(clipboard, x_axis=True)

# draw the select rect with start(x,y) and end(x,y)
def draw_selection():
    step = get_step()
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
    make_set_synced()
    x_min = min(start[0], end[0])
    y_min = min(start[1], end[1])
    
    return {(x - x_min, y - y_min) for (x, y) in alive_cells_on_board if point_in_selection(x, y)}

# Paste the clipboard
def paste_cells():
    make_set_synced()
    x, y = get_mouse_world_pos()

    cordinates_clipboard = {(dx + x, dy + y) for (dx, dy) in clipboard}

    alive_cells_on_board.update(cordinates_clipboard)

# Draw a lil preview where/what you will paste
def draw_paste_preview():
    step = get_step()
    x, y = get_mouse_world_pos()

    preview_cells = {(dx + x, dy + y) for (dx, dy) in clipboard}

    for dx, dy in preview_cells:
        fill_surface = pygame.Surface((round(step), round(step)), pygame.SRCALPHA)
        cell_color_rgb = settings_window.give_cell_color()
        cell_color_rgba = (*cell_color_rgb, 80)
        fill_surface.fill(cell_color_rgba)  # RGBA color_hex
        
        screen.blit(fill_surface, (round(dx*step - camera_x), round(dy*step - camera_y)))

def draw_drag_preview():
    if dragging_selection:
        step = get_step()
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
            cell_color_rgb = settings_window.give_cell_color()
            cell_color_rgba = (*cell_color_rgb, 80)
            fill_surface.fill(cell_color_rgba)  # RGBA color_hex
            screen.blit(fill_surface, (round(new_x*step - camera_x), round(new_y*step - camera_y)))

def history_1_step(): # update history if 1 single step
    global history, redo_history
    make_set_synced()
    history.append((gen, frozenset(alive_cells_on_board)))
    redo_history.clear()

def history_undo(): # update history if undo
    global history, redo_history, gen, alive_cells_on_board, needs_sync
    if history:
        redo_history.append((gen, frozenset(alive_cells_on_board)))
        gen, state = history.pop()
        alive_cells_on_board = set(state)
        needs_sync = True

def history_redo(): # update history if redo
    global history, redo_history, gen, alive_cells_on_board, needs_sync
    if redo_history:
        history.append((gen, frozenset(alive_cells_on_board)))
        gen, state = redo_history.pop()
        alive_cells_on_board = set(state)
        needs_sync = True

def manage_history(action):
    global gen, history, redo_history, needs_sync
    if action == "step":
        if gen % HISTORY_SAVE_EVERY_GEN == 0:  # Save history every 10 generations
            history_1_step()
        gen += 1
    elif action == "undo":
        history_undo()
    elif action == "redo":
        history_redo()
    elif action == "reset":
        history.clear()
        redo_history.clear()
        gen = 0
        needs_sync = True
    
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
print("  'Backspace + Selected' = Delete")
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

    try:
        settings_root.update()
    except tk.TclError:
        pass

    keys = pygame.key.get_pressed() # Setup the key events

    screen.fill((0, 0, 0)) # Make everything black

    for event in pygame.event.get(): 
        if event.type == pygame.QUIT: # So you can close the Window lol
            game_running = False

        if event.type == pygame.KEYDOWN: # Toggle active
            if event.key == pygame.K_SPACE and not has_selection and not selecting and not dragging_selection:
                active = not active
            if event.key == pygame.K_s: # Save
                make_set_synced()
                save_rle(SAVING_FILE)
                print("Saved .rle!")
            if event.key == pygame.K_l: # Load
                set_is_old = False
                make_set_synced()
                alive_cells_on_board = load_rle(LOADING_FILE) 
                manage_history("reset")
                center_cam()
                print("Loaded .rle!")
                if has_selection or selecting or dragging_selection:
                    has_selection = False
                    selecting = False
                    dragging_selection = False
                    active = was_active_before_edit
            if event.key == pygame.K_n and not active and not has_selection and not selecting and not dragging_selection: # +1 Step
                manage_history("step")
                numpy_update()
                if cam_in_center and gen % CAM_CENTER_EVERY_GEN == 0: # Only center cam every CAM_CENTER_EVERY_GEN for performance
                    center_cam()
            if event.key == pygame.K_r: # Clear / Reset
                alive_cells_on_board.clear()
                set_is_old = False
                make_set_synced()
                manage_history("reset")
                if has_selection or selecting or dragging_selection:
                    has_selection = False
                    selecting = False
                    dragging_selection = False
                    active = was_active_before_edit

            if event.key == pygame.K_z and event.mod & pygame.KMOD_CTRL: # Undo by 1 History step (1 * HISTORY_SAVE_EVERY_GEN) on ctrl + z press 
                manage_history("undo")

            if event.key == pygame.K_u and event.mod & pygame.KMOD_CTRL: # Undo by 10 History steps (10 * HISTORY_SAVE_EVERY_GEN) on ctrl + u press
                steps = min(10, len(history))

                for _ in range(steps):
                    manage_history("undo")

            if event.key == pygame.K_y and event.mod & pygame.KMOD_CTRL: # Redo by 1 History step (1 * HISTORY_SAVE_EVERY_GEN) on ctrl + y press
                manage_history("redo")

            if event.key == pygame.K_x and event.mod & pygame.KMOD_CTRL: # Redo by 10 History steps (10 * HISTORY_SAVE_EVERY_GEN) on ctrl + x press
                steps = min(10, len(redo_history))

                for _ in range(steps):
                    manage_history("redo")

            if event.key == pygame.K_c and event.mod & pygame.KMOD_CTRL and not dragging_selection: # Copy
                if has_selection:
                    clipboard = alive_selected_cells.copy()
                    has_selection = False
                    active = was_active_before_edit

            if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL and not has_selection and not selecting and not dragging_selection: # Paste
                paste_cells()
                needs_sync = True

            if event.key == pygame.K_p:
                show_preview = not show_preview

            if event.key == pygame.K_g: # Toggle center cam with 'g'
                cam_in_center = not cam_in_center

            if event.key == pygame.K_f: # Center cam once with 'f'
                center_cam()

        if event.type == pygame.MOUSEBUTTONDOWN: # get click input and turn them into board pos + color them with board
            if event.button == 1:  # Leftclick
                click_cell()
                needs_sync = True
            if event.button == 2: # Middle Drag Cam
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

            zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))

            camera_x = world_x * zoom - mouse_x
            camera_y = world_y * zoom - mouse_y

        select_field(event)
        numpad(event)

    if needs_sync: # Syncs if manual changed before
        sync_grid_from_set()
        needs_sync = False

    draw_cells_from_grid() # draw each cell

    if show_preview: # Draw the preview if Toggled True
        draw_paste_preview()

    draw_drag_preview() # Draw the drag preview if dragging selection

    if cell_size  * zoom >= 4:
        draw_grid(line_width) # draw board grid above

    draw_selection() # draw the selection rect (right click stuffy) if selecting or has selection

    GpS = update_speed(GpS, keys)

    dt = clock.tick(fps) / 1000
    accumulator += dt * GpS
    accumulator = min(accumulator, 10)

    while accumulator >= 1:
        pygame.event.pump()
        if active:
            manage_history("step")
            numpy_update()
            if cam_in_center and gen % CAM_CENTER_EVERY_GEN == 0: # Only center cam every CAM_CENTER_EVERY_GEN for performance
                center_cam()

        accumulator -= 1

    birth_str = "".join(str(n) for n in sorted(birth_values))
    survive_str = "".join(str(n) for n in sorted(survive_values))
    pygame.display.set_caption(f"Rule = B{birth_str}/S{survive_str} | Gen = {gen} | Alive={int(sim_grid.sum()) if sim_grid is not None else 0} | GpS = {GpS} | FPS = {clock.get_fps():.1f} | Running = {active} | Cam centered = {cam_in_center} | Show Preview = {show_preview}") # Update Data
    pygame.display.flip()

pygame.quit()