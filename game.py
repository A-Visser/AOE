import math
import random
from player import Player
from building import Building
from resource import ResourceTile

RESOURCE_CONFIGS = {
    'wood':    {'amount': 50,  'color': (0.35, 0.20, 0.05)},
    'gold':    {'amount': 500, 'color': (0.90, 0.75, 0.10)},
    'stone':   {'amount': 500, 'color': (0.60, 0.60, 0.60)},
    'berries': {'amount': 100, 'color': (0.80, 0.15, 0.30)},
}

class Game:
    def __init__(self):
        self.players = []
        self.buildings = []
        self.resources = []
        self.tiles = {}     # (tx, tz) -> {'type': 'building'|'resource', 'obj': <object>}
        self.turn = 0
        self.running = False

    def get_tile(self, tx, tz):
        return self.tiles.get((tx, tz))

    def is_tile_empty(self, tx, tz):
        return (tx, tz) not in self.tiles

    def add_player(self, name, color):
        player = Player(name, color)
        self.players.append(player)
        return player

    def add_building(self, name, tile_x, tile_z, width, depth, color, label=""):
        b = Building(name, tile_x, tile_z, width, depth, color, label)
        self.buildings.append(b)
        for dx in range(width):
            for dz in range(depth):
                self.tiles[(tile_x + dx, tile_z + dz)] = {'type': 'building', 'obj': b}
        return b

    def start(self):
        self.running = True
        self.turn = 1

    def next_turn(self):
        self.turn += 1

    def is_over(self):
        return not self.running

    # ------------------------------------------------------------------ #

    def _add_resource_tile(self, res_type, tx, tz):
        cfg = RESOURCE_CONFIGS[res_type]
        tile = ResourceTile(res_type, tx, tz, cfg['amount'], cfg['color'])
        self.resources.append(tile)
        self.tiles[(tx, tz)] = {'type': 'resource', 'obj': tile}

    def _grow_cluster(self, cx, cz, size):
        """Random flood-fill cluster of `size` tiles starting near (cx, cz)."""
        cluster = set()
        frontier = [(cx, cz)]
        while len(cluster) < size and frontier:
            pos = frontier.pop(random.randrange(len(frontier)))
            if pos in self.tiles or pos in cluster:
                continue
            cluster.add(pos)
            x, z = pos
            neighbors = [(x+1,z),(x-1,z),(x,z+1),(x,z-1)]
            random.shuffle(neighbors)
            for nb in neighbors:
                if nb not in self.tiles and nb not in cluster:
                    frontier.append(nb)
        return cluster

    def generate_base(self, grid_size):
        """
        Place player starting base in the bottom-left sector.
        TC at center (-26, 26), resources spread in a ring ~20 tiles out.
        """
        half = grid_size // 2

        # ── Town Center ──────────────────────────────────────────────── #
        # Coordinates are in tiles. With TILE_SIZE=0.5, double all values
        # so world positions match the original layout.
        tc_cx, tc_cz = -52, 52          # logical center of the TC (tile coords)
        tc_tx = tc_cx - 4               # top-left tile (8×8 tiles = 4×4 world units)
        tc_tz = tc_cz - 4
        self.add_building("Town Center", tc_tx, tc_tz, 8, 8,
                          (0.6, 0.4, 0.1), label="TC")

        # ── 6 isolated wood tiles close to TC ────────────────────────── #
        placed = 0
        for _ in range(300):
            if placed >= 6:
                break
            angle = random.uniform(0, 2 * math.pi)
            dist  = random.uniform(8, 16)           # 4–8 world units
            tx = round(tc_cx + dist * math.cos(angle))
            tz = round(tc_cz + dist * math.sin(angle))
            if (tx, tz) not in self.tiles:
                self._add_resource_tile('wood', tx, tz)
                placed += 1

        # ── Resource ring ~40 tiles out (= 20 world units) ───────────── #
        ring_entries = [
            ('stone',    10),
            ('berries',  10),
            ('gold',     10),
            ('wood',     12),   # small
            ('wood',     40),   # large
            ('wood',     12),   # small
            ('wood',     40),   # large
            ('wood',     12),   # small
            ('wood',     40),   # large
        ]

        n = len(ring_entries)
        for i, (res_type, size) in enumerate(ring_entries):
            base_angle = (2 * math.pi * i / n)
            angle  = base_angle + random.uniform(-0.15, 0.15)
            radius = 40 + random.uniform(-4, 4)     # ~20 world units
            cx = round(tc_cx + radius * math.cos(angle))
            cz = round(tc_cz + radius * math.sin(angle))
            cx = max(-half + 5, min(half - 5, cx))
            cz = max(-half + 5, min(half - 5, cz))

            cluster = self._grow_cluster(cx, cz, size)
            for (tx, tz) in cluster:
                self._add_resource_tile(res_type, tx, tz)
