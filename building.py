class Building:
    def __init__(self, name, tile_x, tile_z, width, depth, color, label=""):
        self.name = name
        self.tile_x = tile_x    # top-left tile position
        self.tile_z = tile_z
        self.width = width      # in tiles
        self.depth = depth      # in tiles
        self.color = color      # (r, g, b) floats 0-1
        self.label = label      # short text shown on tile
        self.tex_id = None
