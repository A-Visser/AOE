import math
import random
from player import Player
from building import Building
from resource import ResourceTile
from unit import Unit

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
        self.units = []
        self.tiles = {}     # (tx, tz) -> {'type': 'building'|'resource', 'obj': <object>}
        self._buffer = set()  # tiles blocked for resource spawning but free to build on
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

    def add_unit(self, unit_type, tile_x, tile_z):
        unit = Unit(unit_type, tile_x, tile_z)
        self.units.append(unit)
        return unit

    def update_units(self):
        for unit in self.units:
            unit.update()
        self.apply_separation()

    def apply_separation(self):
        units = self.units
        for i in range(len(units)):
            for j in range(i + 1, len(units)):
                a, b = units[i], units[j]
                min_dist = a.separation_radius + b.separation_radius
                dx = a.x - b.x
                dz = a.z - b.z
                dist = math.hypot(dx, dz)
                if 0 < dist < min_dist:
                    push = (min_dist - dist) / dist * 0.5
                    a.x += dx * push
                    a.z += dz * push
                    b.x -= dx * push
                    b.z -= dz * push

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

    def _mark_buffer(self, cluster, radius=3):
        """Mark tiles within manhattan radius of a cluster as spawn-blocked."""
        for (tx, tz) in cluster:
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if abs(dx) + abs(dz) <= radius:
                        self._buffer.add((tx + dx, tz + dz))

    def _grow_cluster(self, cx, cz, size):
        """Random flood-fill cluster of `size` tiles starting near (cx, cz)."""
        cluster = set()
        frontier = [(cx, cz)]
        while len(cluster) < size and frontier:
            pos = frontier.pop(random.randrange(len(frontier)))
            if pos in self.tiles or pos in self._buffer or pos in cluster:
                continue
            cluster.add(pos)
            x, z = pos
            neighbors = [(x+1,z),(x-1,z),(x,z+1),(x,z-1)]
            random.shuffle(neighbors)
            for nb in neighbors:
                if nb not in self.tiles and nb not in self._buffer and nb not in cluster:
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
        tc = self.add_building("Town Center", tc_tx, tc_tz, 8, 8,
                               (0.6, 0.4, 0.1), label="TC")
        tc.rally_x = tc_tx + 4     # center-front, one tile past the edge
        tc.rally_z = tc_tz + 9

        # ── 6 isolated wood tiles in a concentric circle ~6 tiles from TC ─ #
        for i in range(6):
            base_angle = i * math.pi / 3          # evenly spaced at 60° intervals
            for attempt in range(20):
                angle = base_angle + random.uniform(-0.15, 0.15)
                dist  = 12 + random.uniform(-1, 1) # ~6 world units from TC center
                tx = round(tc_cx + dist * math.cos(angle))
                tz = round(tc_cz + dist * math.sin(angle))
                if (tx, tz) not in self.tiles and (tx, tz) not in self._buffer:
                    self._add_resource_tile('wood', tx, tz)
                    self._mark_buffer({(tx, tz)}, radius=2)
                    break

        # ── Resource ring ~40 tiles out (= 20 world units) ───────────── #
        # Stone, berries, gold at fixed positions (every 120°).
        # Large wood lines fill the gaps evenly (6 clusters).
        # Small wood fills remaining gaps (3 clusters).
        fixed_resources = [
            (0.0,              'stone',    10),
            (2 * math.pi / 3,  'berries',  10),
            (4 * math.pi / 3,  'gold',     10),
        ]
        # 6 large wood lines, evenly spaced, offset 60° from the fixed resources
        large_wood_angles = [math.pi / 3 + i * math.pi / 3 for i in range(6)]
        # 3 small wood clusters between the large ones
        small_wood_angles = [math.pi / 6 + i * 2 * math.pi / 3 for i in range(3)]

        # radius_center: non-wood closer (~24-28), wood farther (~38-42)
        all_entries = (
            [(fixed_resources[0][0], 'stone',   10, 26)] +
            [(fixed_resources[1][0], 'berries', 10, 24)] +
            [(fixed_resources[2][0], 'gold',    10, 28)] +
            [(a, 'wood', random.randint(55, 75), 42) for a in large_wood_angles] +
            [(a, 'wood', 14,                     38) for a in small_wood_angles]
        )

        for base_angle, res_type, size, r_center in all_entries:
            angle  = base_angle + random.uniform(-0.12, 0.12)
            radius = r_center + random.uniform(-4, 4)
            cx = round(tc_cx + radius * math.cos(angle))
            cz = round(tc_cz + radius * math.sin(angle))
            cx = max(-half + 5, min(half - 5, cx))
            cz = max(-half + 5, min(half - 5, cz))

            cluster = self._grow_cluster(cx, cz, size)
            for (tx, tz) in cluster:
                self._add_resource_tile(res_type, tx, tz)
            self._mark_buffer(cluster)
