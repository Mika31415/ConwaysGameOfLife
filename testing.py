import modules.simulation.chunk_grid as chunk_grid
import cProfile
import random

survive_values = {2,3}
birth_values = {3}

cells = [(random.randrange(-10000,10000),random.randrange(-10000,10000)) for _ in range(100000)]
print("CELLS CREATED")
chunk_grid.set_cells(cells, 1)
cProfile.run('for _ in range(1000): chunk_grid.step(birth_values, survive_values)', sort='cumulative')