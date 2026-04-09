import math

# Single source of truth for all building properties.
# min_age: earliest age the building can be constructed.
BUILDING_CONFIGS = {
    # ── Economy / base ────────────────────────────────────────────────── #
    'Town Center': {
        'size': 5, 'color': (0.6, 0.4, 0.1), 'label': 'TC',
        'hp': 2400, 'armor': 3, 'build_time': 200, 'pop_cap': 5,
        'cost': {'wood': 275, 'stone': 100}, 'min_age': 'dark',
    },
    'House': {
        'size': 2, 'color': (0.55, 0.55, 0.55), 'label': 'H',
        'hp': 550, 'armor': 1, 'build_time': 25, 'pop_cap': 5,
        'cost': {'wood': 25}, 'min_age': 'dark',
    },
    'Lumber Camp': {
        'size': 2, 'color': (0.40, 0.25, 0.10), 'label': 'LC',
        'hp': 300, 'armor': 1, 'build_time': 30,
        'cost': {'wood': 100}, 'min_age': 'dark',
    },
    'Mine': {
        'size': 2, 'color': (0.50, 0.50, 0.45), 'label': 'Mi',
        'hp': 300, 'armor': 1, 'build_time': 30,
        'cost': {'wood': 100}, 'min_age': 'dark',
    },
    'Mill': {
        'size': 2, 'color': (0.65, 0.50, 0.20), 'label': 'Ml',
        'hp': 300, 'armor': 1, 'build_time': 30,
        'cost': {'wood': 100}, 'min_age': 'dark',
    },
    'Farm': {
        'size': 2, 'color': (0.70, 0.60, 0.20), 'label': 'Fa',
        'hp': 200, 'armor': 0, 'build_time': 15,
        'cost': {'wood': 60}, 'min_age': 'dark',
        'food_amount': 250,
    },
    # ── Military ──────────────────────────────────────────────────────── #
    'Barracks': {
        'size': 4, 'color': (0.50, 0.20, 0.20), 'label': 'Br',
        'hp': 1200, 'armor': 2, 'build_time': 50,
        'cost': {'wood': 175}, 'min_age': 'dark',
    },
    'Archery Range': {
        'size': 4, 'color': (0.45, 0.30, 0.15), 'label': 'AR',
        'hp': 1200, 'armor': 2, 'build_time': 50,
        'cost': {'wood': 175}, 'min_age': 'feudal',
    },
    'Stable': {
        'size': 4, 'color': (0.55, 0.35, 0.10), 'label': 'St',
        'hp': 1200, 'armor': 2, 'build_time': 50,
        'cost': {'wood': 175}, 'min_age': 'feudal',
    },
    'Blacksmith': {
        'size': 3, 'color': (0.30, 0.30, 0.35), 'label': 'Bs',
        'hp': 2100, 'armor': 2, 'build_time': 40,
        'cost': {'wood': 150}, 'min_age': 'feudal',
    },
    'Watch Tower': {
        'size': 2, 'color': (0.60, 0.58, 0.50), 'label': 'WT',
        'hp':  500, 'armor': 4, 'build_time': 25,
        'cost': {'wood': 125, 'stone': 50}, 'min_age': 'feudal',
    },
    'Market': {
        'size': 4, 'color': (0.70, 0.55, 0.15), 'label': 'Mk',
        'hp': 2100, 'armor': 2, 'build_time': 60,
        'cost': {'wood': 175}, 'min_age': 'feudal',
    },
    'Dock': {
        'size': 3, 'color': (0.15, 0.35, 0.60), 'label': 'Dk',
        'hp': 1800, 'armor': 2, 'build_time': 35,
        'cost': {'wood': 150}, 'min_age': 'feudal',
    },
    'Castle': {
        'size': 5, 'color': (0.40, 0.40, 0.50), 'label': 'Ca',
        'hp': 4800, 'armor': 5, 'build_time': 200, 'pop_cap': 20,
        'cost': {'stone': 650}, 'min_age': 'castle',
    },
    'University': {
        'size': 4, 'color': (0.20, 0.35, 0.55), 'label': 'Un',
        'hp': 2100, 'armor': 2, 'build_time': 60,
        'cost': {'wood': 200}, 'min_age': 'castle',
    },
    'Monastery': {
        'size': 4, 'color': (0.45, 0.35, 0.60), 'label': 'Mo',
        'hp': 2100, 'armor': 2, 'build_time': 40,
        'cost': {'wood': 175}, 'min_age': 'castle',
    },
    'Siege Workshop': {
        'size': 4, 'color': (0.35, 0.25, 0.15), 'label': 'SW',
        'hp': 1200, 'armor': 2, 'build_time': 50,
        'cost': {'wood': 200}, 'min_age': 'castle',
    },
    # ── Walls / gates ─────────────────────────────────────────────────── #
    'Stone Wall': {
        'size': 1, 'color': (0.58, 0.56, 0.52), 'label': 'W',
        'hp':  600, 'armor': 8, 'build_time': 10,
        'cost': {'stone': 5}, 'min_age': 'feudal',
    },
    'Gate': {
        'size': 1, 'color': (0.50, 0.48, 0.44), 'label': 'G',
        'hp':  600, 'armor': 8, 'build_time': 10,
        'cost': {'stone': 30, 'wood': 30}, 'min_age': 'feudal',
    },
}

_FPS = 60


class Building:
    def __init__(self, name, tile_x, tile_z, width, depth, color, label="", team=None):
        self.name    = name
        self.tile_x  = tile_x
        self.tile_z  = tile_z
        self.width   = width
        self.depth   = depth
        self.color   = color
        self.label   = label
        self.team    = team

        cfg = BUILDING_CONFIGS.get(name, {})
        self.max_hp  = cfg.get('hp',    500)
        self.hp      = self.max_hp
        self.armor   = cfg.get('armor',   1)

        build_secs             = cfg.get('build_time', 30)
        self.build_ticks_total = int(build_secs * _FPS)
        self.build_ticks_done  = 0
        self.under_construction = False

        self.queue       = []
        self.queue_ticks = 0

        self.rally_x = None
        self.rally_z = None

        self.tex_id  = None
