# Base Modules
import pygame
import math
import numpy as np
import random
from collections import deque
import tkinter as tk

# Own Modules
import modules.ux.settings_window as settings_window
import modules.simulation.chunk_grid as chunk_grid

# Ma Todo List for the entier Project :3333
'''
WHAT TO ADD:
    1. Numpy Vectors (Done ig)
    2. Chunk-System NOOWOOWOWOOWOWOWOWWWWWWWWWWWWWWW!!!!! | ONLY HISTORY LEFT
    3. Multi-Threading/Processing
    4. HashLife
'''
'''
WHAT TO FIX/OPTIMIZE:
    1. save_rle -> Numpy vectors (makes saving faster)
    2. history_1_step -> Save Deltas (makes history faster)
    3. center_cam -> Update for each add/remove cell instead of every CAM_CENTER_EVERY_GEN (makes it faster)
    4. Use State Enums (makes it cleaner)
    5. Use Modules instead of 1 big File (makes it cleaner) | Done a bit
    6. Cache preview/selection Surfaces instead of recreating every frame (makes it faster)
'''

# ---------------------------------- Change freely for Hotkeys etc. -------------------------------------
NUMPAD_HOTKEYS = {
    pygame.K_1: "Numpad/gosper_glider_gun.rle", # Hotkey Numpad 1
    pygame.K_2: "Numpad/eater.rle", # Hotkey Numpad 2
    pygame.K_3: "Numpad/buckaroo.rle", # Hotkey Numpad 3
    pygame.K_4: "Numpad/60p_glider_gun.rle", # Hotkey Numpad 4
    pygame.K_5: "Numpad/60p_and_gate.rle", # Hotkey Numpad 5
    pygame.K_6: "Numpad/60p_not_gate.rle", # Hotkey Numpad 6
    pygame.K_7: "Numpad/60p_or_gate.rle", # Hotkey Numpad 7
    pygame.K_8: "Numpad/duplicator.rle", # Hotkey Numpad 8
    pygame.K_9: "Numpad/60p_xor_gate.rle", # Hotkey Numpad 9
    pygame.K_0: "Numpad/"  # Hotkey Numpad 0
}
LOADING_FILE = "RLE/half_adder.rle" # Change if you want a different loaded .rle file
SAVING_FILE = "RLE/game.rle" # Change if you want a different filename for the saved .rle

WIDTH = 1000 # Game Window Width | Base = 1000
HEIGHT = 1000 # Game Window Height | Base = 1000

MIN_ZOOM = 0.055 # Minimum Zoom Level | Base = 0.055
MAX_ZOOM = 10.0 # Maximum Zoom Level | Base = 10.0
CAM_CENTER_EVERY_GEN = 10 # Center the cam every X generations (for performance reasons) | Base = 10

HISTORY_LIMIT = 10000 # Limit of the Undo/Redo History
HISTORY_SAVE_EVERY_GEN = 10 # Save history every X generations (for performance reasons) | Base = 10 | In the Future 1
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
last_mouse_pos = (0, 0)

# Grid/Cell shtuff
line_width = 1
cell_size = 10

# Copy/Paste Tuffies
alive_selected_cells = set()
clipboard = set()
original_selected_cells = set()
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

# IN DA FUTURE MOVE THE 3 HELPY HELPERS HELP FUNCS IN A DIFFERENT MODULE / FILE
# Another helpy func with gives the step num
def get_step():
    return max(1, round(cell_size * zoom))

# A lil help function to get the mouse pos in world cordinates
def get_mouse_world_pos():
    step = get_step()
    mx, my = pygame.mouse.get_pos()

    x = math.floor((mx + camera_x) // step)
    y = math.floor((my + camera_y) // step)

    return (x,y)

def get_max_min_from_selection():
    x_min, y_min = min(start[0], end[0]), min(start[1], end[1])
    x_max, y_max = max(start[0], end[0]), max(start[1], end[1])
    return (x_min, x_max, y_min, y_max)
# YE THESE 3 FUNCS ABOVE IN THE DIFFERENT MODULE / FILE IN DA FUTURE 

# Center the cam so you can see every cell 
def center_cam():
    global zoom, camera_x, camera_y
    bbox = chunk_grid.global_bbox()
    if not bbox:
        return

    min_x, min_y, max_x, max_y  = bbox

    pattern_height = (max_y - min_y + 1) * cell_size
    pattern_width = (max_x - min_x + 1) * cell_size

    zoom = min(MAX_ZOOM, max(MIN_ZOOM, min(WIDTH / pattern_width, HEIGHT / pattern_height) * 0.9))

    center_y = (min_y + max_y + 1) / 2 * cell_size
    center_x = (min_x + max_x + 1) / 2 * cell_size

    camera_x = center_x * zoom - WIDTH / 2
    camera_y = center_y * zoom - HEIGHT / 2

# Save the game state with "Ctrl + s"
def save_rle(file):
    bbox = chunk_grid.global_bbox()
    if not bbox: # If no alive cells on the board, don't save
        return False

    min_x, min_y, max_x, max_y = bbox

    width = max_x - min_x + 1
    height = max_y - min_y + 1

    lines_out = []
    for y in range(min_y, max_y + 1):
        row_str = ""
        run_char = None
        run_count = 0

        for x in range(min_x, max_x + 1):
            cell_char = "o" if chunk_grid.get_cell(x, y) == 1 else "b"

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
        return True
    except (OSError, PermissionError):
        print(f"Couldn't save the file: {file}")
        return False

# Load the rle file with "Ctrl + l"
def load_rle(file): # CHANGE 2
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
            if line.startswith("x"): # Read the rules
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

    for y in range(start_y, end_y): # ⏤
        pos = round(y * step - camera_y)

        pygame.draw.line(screen, (20, 20, 20), (0, pos), (WIDTH, pos), grid_width)

# Toggle alive/dead on click
def click_cell():
    global has_selection, dragging_selection, start_drag_selection, was_active_before_edit, active, original_selected_cells

    x, y = get_mouse_world_pos()

    if has_selection and not point_in_selection(x,y):
        has_selection = False
        active = was_active_before_edit
        return False
    elif has_selection:
        dragging_selection = True
        start_drag_selection = (x,y)
        original_selected_cells = get_selection()
        return False

    history_1_step() # Checkpoint the pre-edit state so this toggle can be undone
    chunk_grid.set_cell(x, y, 1 - chunk_grid.get_cell(x, y)) # Toggle the cell state
    return True

# Fast Numpy Draw cells (one big image not many smoll images)
def draw_cells_from_grid():
    bbox = chunk_grid.global_bbox()
    if bbox is None:
        return
    step = get_step()

    view_min_x, view_min_y = math.floor(camera_x / step), math.floor(camera_y / step)
    view_max_x, view_max_y = math.ceil((camera_x + WIDTH) / step), math.ceil((camera_y + HEIGHT) / step)

    size = chunk_grid.CHUNK_SIZE
    cx_start, cx_end = view_min_x // size, (view_max_x - 1) // size
    cy_start, cy_end = view_min_y // size, (view_max_y - 1) // size

    cell_color = settings_window.give_cell_color()

    for cx in range(cx_start, cx_end + 1):
        for cy in range(cy_start, cy_end + 1):
            chunk = chunk_grid.chunks.get((cx, cy))
            if chunk is None:
                continue

            chunk_world_x, chunk_world_y = cx * size, cy * size

            x_start = max(0, view_min_x - chunk_world_x)
            x_end = min(size, view_max_x - chunk_world_x)
            y_start = max(0, view_min_y - chunk_world_y)
            y_end = min(size, view_max_y - chunk_world_y)

            if x_start >= x_end or y_start >= y_end:
                continue

            visible = chunk[y_start:y_end, x_start:x_end]
            if not visible.any():
                continue

            scaled = np.kron(visible, np.ones((step, step), dtype=np.uint8))
            rgb = np.stack([scaled*cell_color[0], scaled*cell_color[1], scaled*cell_color[2]], axis=-1)
            surf = pygame.surfarray.make_surface(rgb.swapaxes(0,1))

            screen_x = round((chunk_world_x + x_start) * step - camera_x)
            screen_y = round((chunk_world_y + y_start) * step - camera_y)
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

def rotate_cells(thing, clockwise=True): # Rotate around da center
    if not thing:
        return set()

    center_x, center_y = get_center_for(thing)

    if clockwise:
        return {((y - center_y) + center_x, (-x + center_x) + center_y) for (x, y) in thing}
    else:
        return {((-y + center_y) + center_x, (x - center_x) + center_y) for (x, y) in thing}

def mirror_cells(thing, x_axis=True): # Mirror around the center
    if not thing:
        return set()

    center_x, center_y = get_center_for(thing)

    if x_axis:
        return {(2 * center_x - x, y) for (x, y) in thing}
    else:
        return {(x, 2 * center_y - y) for (x, y) in thing}
    
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
            x_min, _, y_min, _ = get_max_min_from_selection()
            x, y = get_mouse_world_pos()
            delta_x = x - start_drag_selection[0]
            delta_y = y - start_drag_selection[1]

            if delta_x != 0 or delta_y != 0: # Only touch history if the selection actually moved
                old_positions = {(dx + x_min, dy + y_min) for (dx, dy) in original_selected_cells}
                new_positions = {(dx + x_min + delta_x, dy + y_min + delta_y) for (dx, dy) in alive_selected_cells}
                history_1_step() # Checkpoint the pre-drag state so the move can be undone
                chunk_grid.remove_cells(old_positions)
                chunk_grid.set_cells(new_positions, 1)
                redo_history.clear()

            active = was_active_before_edit

    if event.type == pygame.MOUSEMOTION:
        if selecting: # While you hold rightclick select duh
            x, y = get_mouse_world_pos()
            end = (x,y)

    if event.type == pygame.KEYDOWN:
        if has_selection and event.key == pygame.K_BACKSPACE: # Delete Selected
            x_min, _, y_min, _ = get_max_min_from_selection()
            cells_to_delete = original_selected_cells if dragging_selection else alive_selected_cells
            if cells_to_delete: # Only touch history if the selection actually has cells to delete
                history_1_step() # Checkpoint the pre-delete state so the deletion can be undone
                chunk_grid.remove_cells({(dx+x_min, dy+y_min) for (dx,dy) in cells_to_delete})
                redo_history.clear()
            dragging_selection = False
            has_selection = False
            active = was_active_before_edit

        if event.key == pygame.K_a:
            if dragging_selection and alive_selected_cells: # Rotate the drag | CW
                alive_selected_cells = rotate_cells(alive_selected_cells, clockwise=True)
            elif clipboard: # Rotate the Copy to Paste | CW
                clipboard = rotate_cells(clipboard, clockwise=True)

        if event.key == pygame.K_d:
            if dragging_selection and alive_selected_cells: # Rotate the drag | CCW
                alive_selected_cells = rotate_cells(alive_selected_cells, clockwise=False)
            elif clipboard: # Rotate the Copy to Paste | CCW
                clipboard = rotate_cells(clipboard, clockwise=False)

        if event.key == pygame.K_s:
            if dragging_selection and alive_selected_cells: # Mirror the drag up down
                alive_selected_cells = mirror_cells(alive_selected_cells, x_axis=False)
            elif clipboard: # Mirror the Copy to Paste up down
                clipboard = mirror_cells(clipboard, x_axis=False)

        if event.key == pygame.K_w:
            if dragging_selection and alive_selected_cells: # Mirror the drag left right
                alive_selected_cells = mirror_cells(alive_selected_cells, x_axis=True)
            elif clipboard: # Mirror the Copy to Paste left right
                clipboard = mirror_cells(clipboard, x_axis=True)

# Draw the select rect with start(x,y) and end(x,y)
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
        fill_surface.fill((0, 32, 255, 80))  # RGBA for a blue rect
        
        screen.blit(fill_surface, (rect.x, rect.y))

        pygame.draw.rect(screen, (0,32,255), rect, max(1, int(line_width * zoom)))

# Check if the cell is in the rect
def point_in_selection(x,y):
    x_min, x_max, y_min, y_max = get_max_min_from_selection()
    return x_min <= x <= x_max and y_min <= y <= y_max

# Get every alive cell in rect
def get_selection():
    x_min, x_max, y_min, y_max = get_max_min_from_selection()
    alive_rect_cells = chunk_grid.iterate_alive_in_rect(x_min, y_min, x_max, y_max)
    return {(x - x_min, y - y_min) for (x, y) in alive_rect_cells}

# Paste the clipboard
def paste_cells():
    if not clipboard: # Nothing to paste -> don't waste a history slot / wipe redo on a no-op
        return False

    x, y = get_mouse_world_pos()
    cordinates_clipboard = {(dx + x, dy + y) for (dx, dy) in clipboard}
    history_1_step() # Checkpoint the pre-paste state so the paste can be undone
    chunk_grid.set_cells(cordinates_clipboard, 1)
    return True

# Draw a lil preview where/what you will paste
def draw_paste_preview():
    if not clipboard:
        return
    step = get_step()
    x, y = get_mouse_world_pos()
    cell_color_rgb = settings_window.give_cell_color()
    cell_color_rgba = (*cell_color_rgb, 80)

    xs = [dx + x for dx, _ in clipboard]
    ys = [dy + y for _, dy in clipboard]
    min_x, min_y = min(xs), min(ys)
    width = (max(xs) - min_x + 1) * step
    height = (max(ys) - min_y + 1) * step

    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    for dx, dy in clipboard:
        px, py = (dx + x - min_x) * step, (dy + y - min_y) * step
        overlay.fill(cell_color_rgba, pygame.Rect(px, py, step, step))

    screen.blit(overlay, (round(min_x * step - camera_x), round(min_y * step - camera_y)))

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

def _reset_selection_state(): # Clear any selection/drag state so it can't reference a now-stale grid
    global has_selection, selecting, dragging_selection, active
    if has_selection or selecting or dragging_selection:
        has_selection = False
        selecting = False
        dragging_selection = False
        active = was_active_before_edit

# UPDATE HISTORY LATER FOR ACTUAL UNDO ETC
def history_1_step():
    global history, redo_history
    history.append(gen)
    redo_history.clear()
    chunk_grid.clear_dirty()

def history_undo():
    global history, redo_history, gen
    if history:
        redo_history.append(gen)
        gen = history.pop()
        _reset_selection_state()

def history_redo():
    global history, redo_history, gen
    if redo_history:
        history.append(gen)
        gen = redo_history.pop()
        _reset_selection_state()

def manage_history(action):
    global gen, history, redo_history
    if action == "step":
        if gen % HISTORY_SAVE_EVERY_GEN == 0:  # Save history every X generations
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

# Create a random soup fill
def random_fill():
    x_min, x_max, y_min, y_max = get_max_min_from_selection()
    density_percent = settings_window.density_percent  # get desity from settings_window (% value)

    # Convert % in int for the loop
    max_cells = (x_max + 1 - x_min) * (y_max + 1 - y_min)
    density = round(max(1, (max_cells * density_percent) / 100))

    added_cells = {(random.randrange(x_min, x_max + 1),random.randrange(y_min, y_max + 1)) for _ in range(density)} # Add prevention for multiple cells at 1 spot

    history_1_step()
    chunk_grid.set_cells(added_cells, 1)
    redo_history.clear()

# Print the Controls + Intro
print("Welcome to GoL:\n")
print("Controls:")
print("  'Space'                = Pause")
print("  't'                    = Clear / Terminate")
print("  'n'                    = Go 1 Step / Gen")
print("  'f'                    = Center cam once")
print("  'Right'                = +1 GpS")
print("  'Up'                   = +10 GpS")
print("  'Left'                 = -1 GpS")
print("  'Down'                 = -10 GpS")
print("  'Ctrl + k'             = Save .rle file") 
print("  'Ctrl + l'             = Load .rle file")
print("  'Ctrl + z'             = Undo by 1")
print("  'Ctrl + u'             = Undo by 10")
print("  'Ctrl + y'             = Redo by 1")
print("  'Ctrl + x'             = Redo by 10")
print("  'Ctrl + c + Selected'  = Copy")
print("  'Ctrl + v + Selected'  = Paste")
print("  'a + Drag'             = Turn CW")
print("  'd + Drag'             = Turn CCW")
print("  'w + Drag'             = Mirror left right")
print("  's + Drag'             = Mirror up down")
print("  'LeftClick'            = Toggle alive/dead")
print("  'LeftClick + Selected' = Drag")
print("  'Backspace + Selected' = Delete")
print("  'r + Selected'         = Random fill the selected rect")
print("  'Hold Rightclick'      = Select")
print("  'MouseWheel'           = Zoom")
print("  'Hold MouseWheel'      = Move cam")
print("  '0-9'                  = Print hotkeys\n")

# Start of Game / Main Loop
while game_running:
    show_preview, disable_grid, cam_in_center = settings_window.give_checkbox_toggles()
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
            if event.key == pygame.K_k and event.mod & pygame.KMOD_CTRL: # Save
                if save_rle(SAVING_FILE):
                    print("Saved .rle!")
            if event.key == pygame.K_l and event.mod & pygame.KMOD_CTRL: # Load
                chunk_grid.clear_all()
                chunk_grid.set_cells(load_rle(LOADING_FILE), 1) 
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
                chunk_grid.step(birth_values, survive_values)
                if cam_in_center and gen % CAM_CENTER_EVERY_GEN == 0: # Only center cam every CAM_CENTER_EVERY_GEN for performance
                    center_cam()
            if event.key == pygame.K_t: # Clear / Terminate
                chunk_grid.clear_all()
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
                if paste_cells():
                    redo_history.clear()

            if event.key == pygame.K_f: # Center cam once with 'f'
                center_cam()

            if event.key == pygame.K_r:
                if has_selection and not dragging_selection:
                    random_fill()
                    has_selection = False
                    active = was_active_before_edit

        if event.type == pygame.MOUSEBUTTONDOWN: # Get click input and turn them into board pos + color them with board
            if event.button == 1:  # Leftclick
                if click_cell():
                    redo_history.clear()
            if event.button == 2: # Middle Drag Cam
                dragging = True
                last_mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONUP: # Cam drag
            if event.button == 2:
                dragging = False

        if event.type == pygame.MOUSEMOTION:
            if dragging: # Cam drag
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

    draw_cells_from_grid() # draw each cell

    if show_preview: # Draw the preview if Toggled True | CHANGE IN THE SETTINGS
        draw_paste_preview()

    draw_drag_preview() # Draw the drag preview if dragging selection

    if not disable_grid:
        if cell_size * zoom >= 4:
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
            chunk_grid.step(birth_values, survive_values)
            if cam_in_center and gen % CAM_CENTER_EVERY_GEN == 0: # Only center cam every CAM_CENTER_EVERY_GEN for performance
                center_cam()

        accumulator -= 1

    birth_str = "".join(str(n) for n in sorted(birth_values))
    survive_str = "".join(str(n) for n in sorted(survive_values))
    pygame.display.set_caption(f"Rule = B{birth_str}/S{survive_str} | Gen = {gen} | Alive={chunk_grid.total_alive_count()} | GpS = {GpS} | FPS = {clock.get_fps():.1f} | Running = {active}") # Update Data
    pygame.display.flip()

pygame.quit()