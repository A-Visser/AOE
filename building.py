import math

# Single source of truth for all building properties
BUILDING_CONFIGS = {
    'Town Center': {
        'size': 8, 'color': (0.6, 0.4, 0.1), 'label': 'TC',
        'hp': 2400, 'armor': 3, 'build_time': 200, 'pop_cap': 5,
        'cost': {'wood': 275, 'stone': 100},
    },
    'House': {
        'size': 2, 'color': (0.55, 0.55, 0.55), 'label': 'H',
        'hp': 550, 'armor': 1, 'build_time': 25, 'pop_cap': 5,
        'cost': {'wood': 25},
    },
    'Lumber Camp': {
        'size': 2, 'color': (0.40, 0.25, 0.10), 'label': 'LC',
        'hp': 300, 'armor': 1, 'build_time': 30,
        'cost': {'wood': 100},
    },
    'Mine': {
        'size': 2, 'color': (0.50, 0.50, 0.45), 'label': 'Mi',
        'hp': 300, 'armor': 1, 'build_time': 30,
        'cost': {'wood': 100},
    },
    'Mill': {
        'size': 2, 'color': (0.65, 0.50, 0.20), 'label': 'Ml',
        'hp': 300, 'armor': 1, 'build_time': 30,
        'cost': {'wood': 100},
    },
    # ── Military ──────────────────────────────────────────────────────── #
    'Barracks': {
        'size': 4, 'color': (0.50, 0.20, 0.20), 'label': 'Br',
        'hp': 1200, 'armor': 2, 'build_time': 50,
        'cost': {'wood': 175},
    },
    'Archery Range': {
        'size': 4, 'color': (0.45, 0.30, 0.15), 'label': 'AR',
        'hp': 1200, 'armor': 2, 'build_time': 50,
        'cost': {'wood': 175},
    },
    'Stable': {
        'size': 4, 'color': (0.55, 0.35, 0.10), 'label': 'St',
        'hp': 1200, 'armor': 2, 'build_time': 50,
        'cost': {'wood': 175},
    },
    'Blacksmith': {
        'size': 3, 'color': (0.30, 0.30, 0.35), 'label': 'Bs',
        'hp': 2100, 'armor': 2, 'build_time': 40,
        'cost': {'wood': 150},
    },
    'Watch Tower': {
        'size': 2, 'color': (0.60, 0.58, 0.50), 'label': 'WT',
        'hp':  500, 'armor': 4, 'build_time': 25,
        'cost': {'wood': 125, 'stone': 50},
    },
    'Castle': {
        'size': 5, 'color': (0.40, 0.40, 0.50), 'label': 'Ca',
        'hp': 4800, 'armor': 5, 'build_time': 200, 'pop_cap': 20,
        'cost': {'stone': 650},
    },
    'University': {
        'size': 4, 'color': (0.20, 0.35, 0.55), 'label': 'Un',
        'hp': 2100, 'armor': 2, 'build_time': 60,
        'cost': {'wood': 200},
    },
    'Monastery': {
        'size': 4, 'color': (0.45, 0.35, 0.60), 'label': 'Mo',
        'hp': 2100, 'armor': 2, 'build_time': 40,
        'cost': {'wood': 175},
    },
    'Market': {
        'size': 4, 'color': (0.70, 0.55, 0.15), 'label': 'Mk',
        'hp': 2100, 'armor': 2, 'build_time': 60,
        'cost': {'wood': 175},
    },
    'Dock': {
        'size': 3, 'color': (0.15, 0.35, 0.60), 'label': 'Dk',
        'hp': 1800, 'armor': 2, 'build_time': 35,
        'cost': {'wood': 150},
    },
    # ── Walls / gates ─────────────────────────────────────────────────── #
    'Stone Wall': {
        'size': 1, 'color': (0.58, 0.56, 0.52), 'label': 'W',
        'hp':  600, 'armor': 8, 'build_time': 10,
        'cost': {'stone': 5},
    },
    'Gate': {
        'size': 1, 'color': (0.50, 0.48, 0.44), 'label': 'G',
        'hp':  600, 'armor': 8, 'build_time': 10,
        'cost': {'stone': 30, 'wood': 30},
    },
}

_FPS = 60   # used only for converting build_time (seconds) → ticks


class Building:
    def __init__(self, name, tile_x, tile_z, width, depth, color, label=""):
        self.name    = name
        self.tile_x  = tile_x
        self.tile_z  = tile_z
        self.width   = width
        self.depth   = depth
        self.color   = color
        self.label   = label

        cfg = BUILDING_CONFIGS.get(name, {})
        self.max_hp  = cfg.get('hp',    500)
        self.hp      = self.max_hp
        self.armor   = cfg.get('armor',   1)

        # Construction
        build_secs         = cfg.get('build_time', 30)
        self.build_ticks_total = int(build_secs * _FPS)
        self.build_ticks_done  = 0
        self.under_construction = False   # set True when placed by a villager

        # Production queue (production buildings only)
        self.queue       = []
        self.queue_ticks = 0

        # Rally point
        self.rally_x = None
        self.rally_z = None

        self.tex_id  = None
