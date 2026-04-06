class ResourceTile:
    def __init__(self, res_type, tile_x, tile_z, amount, color):
        self.res_type = res_type
        self.tile_x = tile_x
        self.tile_z = tile_z
        self.amount = amount
        self.color = color
        self.tex_id = None  # assigned after OpenGL context is ready
