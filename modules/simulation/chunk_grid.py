# Modules
from collections import defaultdict
import numpy as np

# Custom Modules
import modules.ux.settings_window as settings_window

# Global Variables
chunks = {}
_dirty_chunks = set()

# ---------------- Constants ----------------
CHUNK_SIZE = 64 # smaller for testing purposes, can be set to 32, 64 or 128 for actual use
# -------------------------------------------

# Helper Functions for Chunk System
def _world_to_chunk(x, y):
    cx, local_x = divmod(x, CHUNK_SIZE)
    cy, local_y = divmod(y, CHUNK_SIZE)
    return (cx, cy, local_x, local_y)

def _get_or_create_chunk(cx, cy, create=False):
    if chunks.get((cx, cy)) is not None:
        return chunks[(cx, cy)]
    if create:
        chunks[(cx, cy)] = np.zeros((CHUNK_SIZE, CHUNK_SIZE), dtype=np.uint8)
        return chunks[(cx, cy)]
    return None

def _cleanup_if_empty(cx, cy):
    chunk = chunks.get((cx, cy))
    if chunk is not None and not chunk.any():
        del chunks[(cx, cy)]

# Functions to get and set cell values in the chunk system
def get_cell(x, y):
    cx, cy, local_x, local_y = _world_to_chunk(x, y)
    chunk = _get_or_create_chunk(cx, cy, create=False)
    if chunk is not None:
        return int(chunk[local_y, local_x])
    return 0  # Cell is dead if the chunk doesn't exist

def set_cell(x, y, value):
    cx, cy, local_x, local_y = _world_to_chunk(x, y)
    if value == 0:
        chunk = _get_or_create_chunk(cx, cy, create=False)
        if chunk is not None:
            if int(chunk[local_y, local_x]) != 0:
                chunk[local_y, local_x] = value
                _cleanup_if_empty(cx, cy)
                return True
        return False
    else:
        chunk = _get_or_create_chunk(cx, cy, create=True)
        if int(chunk[local_y, local_x]) != 1:
            chunk[local_y, local_x] = value
            return True
        return False

# Functions to set and remove multiple cells at once
def get_and_remove_cells_help(cells):
    grouped = defaultdict(list)
    for (x, y) in cells:
        cx, cy, local_x, local_y = _world_to_chunk(x, y)
        grouped[(cx, cy)].append((local_x, local_y))

    return grouped

def set_cells(cells, value):
    grouped = get_and_remove_cells_help(cells)
    for (cx, cy), local_cells in grouped.items():
        chunk = _get_or_create_chunk(cx, cy, create=True)
        local_xs, local_ys = zip(*local_cells)
        chunk[list(local_ys), list(local_xs)] = value

def remove_cells(cells):
    grouped = get_and_remove_cells_help(cells)
    for (cx, cy), local_cells in grouped.items():
        chunk = _get_or_create_chunk(cx, cy, create=False)
        if chunk is not None:
            local_xs, local_ys = zip(*local_cells)
            chunk[list(local_ys), list(local_xs)] = 0
            _cleanup_if_empty(cx, cy)

# Function to give each alive cell in a chosen rect
def iterate_alive_in_rect(x0, y0, x1, y1):
    x_min, x_max = min(x0, x1), max(x0, x1)
    y_min, y_max = min(y0, y1), max(y0, y1)

    cx_start,_,_,_ = _world_to_chunk(x_min, y_min)
    cx_end,_,_,_ = _world_to_chunk(x_max, y_max)
    _,cy_start,_,_ = _world_to_chunk(x_min, y_min)
    _,cy_end,_,_ = _world_to_chunk(x_max, y_max)

    alive_cells = set()

    for cx in range(cx_start, cx_end + 1):
        for cy in range(cy_start, cy_end + 1):
            chunk = _get_or_create_chunk(cx, cy, create=False)
            if chunk is not None:
                ys, xs = np.nonzero(chunk)
                world_xs = cx * CHUNK_SIZE + xs
                world_ys = cy * CHUNK_SIZE + ys
                mask = (world_xs >= x_min) & (world_xs <= x_max) & (world_ys >= y_min) & (world_ys <= y_max)
                for wx, wy in zip(world_xs[mask], world_ys[mask]):
                    alive_cells.add((int(wx), int(wy)))

    return alive_cells

# Function to get the min/max box of all alive cells in the chunk system
def global_bbox():
    if not chunks:
        return None  # No alive cells

    # Initialize min/max values to extreme values
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    for (cx, cy), chunk in chunks.items():
        if chunk.any():  # Check if there are any alive cells in the chunk
            ys, xs = np.nonzero(chunk)
            world_xs = cx * CHUNK_SIZE + xs
            world_ys = cy * CHUNK_SIZE + ys
            min_x = min(min_x, int(world_xs.min()))
            max_x = max(max_x, int(world_xs.max()))
            min_y = min(min_y, int(world_ys.min()))
            max_y = max(max_y, int(world_ys.max()))

    return int(min_x), int(min_y), int(max_x), int(max_y)

# Function to get the alive cells on the whole grid
def total_alive_count():
    return int(sum(chunk.sum() for chunk in chunks.values()))

# Lookup tables for halo building
_HALO_INDEX = {-1: 0, 0: slice(1, -1), 1: -1}
_NEIGHBOR_INDEX = {-1: -1, 0: slice(None), 1: 0}

# Create an edge for the chunk for neighbor checking
_halo_buffer = np.zeros((CHUNK_SIZE + 2, CHUNK_SIZE + 2), dtype=np.uint8)

def _build_halo(cx, cy, chunk=None):
    halo = _halo_buffer
    halo.fill(0)

    if chunk is None:
        chunk = _get_or_create_chunk(cx, cy, create=False)
    if chunk is None:
        chunk = np.zeros((CHUNK_SIZE, CHUNK_SIZE), dtype=np.uint8)
    halo[1:-1, 1:-1] = chunk

    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            neighbor_chunk = _get_or_create_chunk(cx + dx, cy + dy, create=False)
            if neighbor_chunk is not None:
                halo[_HALO_INDEX[dy], _HALO_INDEX[dx]] = neighbor_chunk[_NEIGHBOR_INDEX[dy], _NEIGHBOR_INDEX[dx]]

    return halo

# Function to check if a chunk has any alive cells on its edges
def has_live_edge(chunk):
    return chunk[0,:].any() or chunk[-1,:].any() or chunk[:,0].any() or chunk[:,-1].any()

# Function to create neighbor chunks to active chunks
def create_neighbor_chunks():
    for (cx, cy), chunk in list(chunks.items()):
        needed = set()
        if chunk[0, :].any(): needed.add((0, -1))
        if chunk[-1, :].any(): needed.add((0, 1))
        if chunk[:, 0].any(): needed.add((-1, 0))
        if chunk[:, -1].any(): needed.add((1, 0))
        if chunk[0, 0]: needed.add((-1, -1))
        if chunk[0, -1]: needed.add((1, -1))
        if chunk[-1, 0]: needed.add((-1, 1))
        if chunk[-1, -1]: needed.add((1, 1))

        for dx, dy in needed:
            _get_or_create_chunk(cx + dx, cy + dy, create=True)

def _isin_small(arr, values):
    result = np.zeros(arr.shape, dtype=bool)
    for v in values:
        result |= (arr == v)
    return result

# Function to count the neighbors of each cell in the grid using the chunk system
def count_neighbors_from_halo(halo, offsets):
    size = halo.shape[0] - 2
    n = np.zeros((size, size), dtype=np.uint8)
    for dx, dy in offsets:
        n += halo[1 + dy : 1 + dy + size, 1 + dx : 1 + dx + size]
    return n

# Function to update the entier grid from the halo
def array_update_from_halo(halo, birth_values, survive_values, offsets):
    current = halo[1:-1, 1:-1]
    neighbor_count = count_neighbors_from_halo(halo, offsets)
    birth_mask = _isin_small(neighbor_count, birth_values) & (current == 0)
    survive_mask = _isin_small(neighbor_count, survive_values) & (current == 1)
    return (birth_mask | survive_mask).astype(np.uint8)

# Function to run 1 single generation of the simulation using the chunk system
def step(birth_values, survive_values):
    create_neighbor_chunks()
    offsets = settings_window.give_neighbor_offsets()

    keys_to_update = list(chunks.keys())
    new_grids = {}
    for key in keys_to_update:
        cx, cy = key
        halo = _build_halo(cx, cy, chunk=chunks[key])
        new_grids[key] = array_update_from_halo(halo, birth_values, survive_values, offsets)

    for key in new_grids.keys():
        if not np.array_equal(new_grids[key], chunks[key]):
            chunks[key] = new_grids[key]
            _dirty_chunks.add(key)
        if chunks[key].sum() == 0:
            del chunks[key]
            _dirty_chunks.add(key)

# Function to get all chunks that changed since the last checkpoint
def get_dirty_since_checkpoint():
    return set(_dirty_chunks)

# Function to clear the dirty tracking after a checkpoint has been saved
def clear_dirty():
    global _dirty_chunks
    _dirty_chunks = set()

# Function to clear every chunk thing
def clear_all():
    chunks.clear()
    _dirty_chunks.clear()

# Add Quiescence Detection Later (if needed) to optimize the simulation by skipping updates for chunks that haven't changed.

