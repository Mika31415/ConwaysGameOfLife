import tkinter as tk

# Base themes
THEME = {
    "bg": "#000000",
    "bg_light": "#1a1a1a",
    "bg_lighter": "#2a2a2a",
    "fg": "#e0e0e0",
    "fg_dim": "#888888",
    "accent": "#9a9a9a", 
    "accent_dark": "#6b6b6b",
    "border": "#333333",
    "error": "#ff5555",
    "line": "#141414",
    "middle_cell": "#3D3D3D"
}
DEFAULT_COLOR = "#ffd60a" # Default cell color
# Default settings / Base Values
cell_color_hex = DEFAULT_COLOR
neighbor_state = {}
buttons = {}
neighbor_state_save = {(r, c): True for r in range(3) for c in range(3) if not (r == 1 and c == 1)}
hex_chars = set("0123456789ABCDEF")

def give_neighbor_offsets():
    offsets = [(col - 1, row - 1) for (row, col), on in neighbor_state_save.items() if on]
    return offsets

def give_cell_color():
    cell_color_rgb = tuple(int(cell_color_hex[i:i+2], 16) for i in (1, 3, 5))
    return cell_color_rgb

def create_settings_window(on_apply_callback, initial_birth="3", initial_survive="23", initial_color="#FFFF00"):
    global neighbor_state, buttons
    # Base window
    root = tk.Tk()
    root.title("CA-Sandbox Settings")
    root.geometry("300x500")
    root.configure(bg=THEME["bg"])

    # Birth settings
    tk.Label(root, text="Birth:", bg=THEME["bg"], fg=THEME["fg_dim"]).pack(pady=(10, 0))
    birth_entry = tk.Entry(root, bg=THEME["bg_light"], fg=THEME["fg"],
                            insertbackground=THEME["fg"], highlightthickness=1,
                            highlightbackground=THEME["border"], highlightcolor=THEME["accent"],
                            relief="flat")
    birth_entry.insert(0, initial_birth)
    birth_entry.pack(pady=5, padx=20, fill="x")

    # Survive settings
    tk.Label(root, text="Survive:", bg=THEME["bg"], fg=THEME["fg_dim"]).pack(pady=(10, 0))
    survive_entry = tk.Entry(root, bg=THEME["bg_light"], fg=THEME["fg"],
                              insertbackground=THEME["fg"], highlightthickness=1,
                              highlightbackground=THEME["border"], highlightcolor=THEME["accent"],
                              relief="flat")
    survive_entry.insert(0, initial_survive)
    survive_entry.pack(pady=5, padx=20, fill="x")

    # Color settings
    tk.Label(root, text="Cell Color (Hex):", bg=THEME["bg"], fg=THEME["fg_dim"]).pack(pady=(10, 0))
    color_entry = tk.Entry(root, bg=THEME["bg_light"], fg=THEME["fg"],
                                  insertbackground=THEME["fg"], highlightthickness=1,
                                  highlightbackground=THEME["border"], highlightcolor=THEME["accent"],
                                  relief="flat")
    color_entry.insert(0, initial_color)  # Default color is yellow
    color_entry.pack(pady=5, padx=20, fill="x")

    # Update color error
    def update_color_error(event=None):
        cell_color = color_entry.get().strip()
        is_valid_hex = (
            (cell_color.startswith("#") and len(cell_color) == 7 and all(c.upper() in hex_chars for c in cell_color[1:]))
            or
            (len(cell_color) == 6 and all(c.upper() in hex_chars for c in cell_color))
        )
        color_entry.configure(highlightbackground=THEME["border"] if is_valid_hex else THEME["error"])

    color_entry.bind("<KeyRelease>", update_color_error)

    # Neighbor settings
    tk.Label(root, text="Counting Neighbors:", bg=THEME["bg"], fg=THEME["fg_dim"]).pack(pady=(10, 0))
    # add 3x3 grid of clickable cells (the middle cell is not clickable + dark) to select which neighbors to count

    def toggle_cell(row, col):
        neighbor_state[(row, col)] = not neighbor_state[(row, col)]
        is_on = neighbor_state[(row, col)]
        btn = buttons[(row, col)]
        btn.configure(bg=cell_color_hex if is_on else THEME["bg_light"],
                      fg=THEME["fg"] if is_on else THEME["fg_dim"])

    grid_frame = tk.Frame(root, bg=THEME["bg"])
    grid_frame.pack(padx=20, pady=20)

    for row in range(3):
        for col in range(3):
            if row == 1 and col == 1:
                center_btn = tk.Button(
                    grid_frame, width=4, height=2,
                    bg=THEME["accent_dark"], fg=THEME["bg"],
                    relief="flat", state="disabled",
                    disabledforeground=THEME["bg"],
                    highlightthickness=2,
                    highlightbackground=THEME["line"]
                )
                center_btn.grid(row=row, column=col, padx=2, pady=2)
                continue

            neighbor_state[(row, col)] = True
            btn = tk.Button(
                grid_frame, width=4, height=2,
                bg=cell_color_hex, fg=THEME["bg"],
                relief="flat",
                highlightthickness=2,
                highlightbackground=THEME["line"]
            )
            btn.configure(command=lambda r=row, c=col: toggle_cell(r, c))
            btn.grid(row=row, column=col, padx=2, pady=2)
            buttons[(row, col)] = btn

    # Update everything
    def apply():
        global neighbor_state_save, cell_color_hex
        # Update the cell color
        cell_color = color_entry.get().strip()
        is_valid_hex = (
            (cell_color.startswith("#") and len(cell_color) == 7 and all(c.upper() in hex_chars for c in cell_color[1:]))
            or
            (len(cell_color) == 6 and all(c.upper() in hex_chars for c in cell_color))
        )
        if is_valid_hex:
            cell_color_hex = cell_color if cell_color.startswith("#") else f"#{cell_color}"
        else:
            cell_color_hex = DEFAULT_COLOR

        for x in range(3):
            for y in range(3):
                if x == 1 and y == 1:
                    continue
                buttons[(x, y)].configure(bg=cell_color_hex if neighbor_state[(x, y)] else THEME["bg_light"])

        # Update the neighbor state
        neighbor_state_save = neighbor_state.copy()

        # Update the B/S
        birth = {int(c) for c in birth_entry.get() if c.isdigit()}
        survive = {int(c) for c in survive_entry.get() if c.isdigit()}
        on_apply_callback(birth, survive) # send the B/S sets to the callback func (main.py)

    # Submit button
    tk.Button(root, text="Submit", command=apply,
              bg=THEME["accent"], fg=THEME["bg"],
              activebackground=THEME["accent_dark"], activeforeground=THEME["bg"],
              relief="flat", bd=0, padx=10, pady=5).pack(pady=15)

    return root