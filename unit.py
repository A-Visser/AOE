import math

UNIT_STATS = {
    # ── Economy ───────────────────────────────────────────────────────── #
    'villager': {
        'max_hp': 25, 'melee_armor': 0, 'pierce_armor': 0,
        'speed': 0.10, 'color': (220, 180, 100),
        'radius': 0.3, 'separation_radius': 0.55,
        'carry_cap': 10, 'gather_ticks': 180,
        'cost': {'food': 50},
    },

    # ── Infantry (Barracks) ───────────────────────────────────────────── #
    'militia': {
        'max_hp': 40, 'melee_armor': 0, 'pierce_armor': 1,
        'speed': 0.10, 'color': (180, 180, 180),
        'radius': 0.3, 'separation_radius': 0.55,
        'cost': {'food': 60, 'gold': 20},
    },
    'man_at_arms': {
        'max_hp': 45, 'melee_armor': 1, 'pierce_armor': 2,
        'speed': 0.10, 'color': (160, 160, 170),
        'radius': 0.3, 'separation_radius': 0.55,
        'cost': {'food': 60, 'gold': 20},
    },
    'long_swordsman': {
        'max_hp': 60, 'melee_armor': 1, 'pierce_armor': 2,
        'speed': 0.10, 'color': (140, 140, 160),
        'radius': 0.3, 'separation_radius': 0.55,
        'cost': {'food': 60, 'gold': 20},
    },
    'spearman': {
        'max_hp': 45, 'melee_armor': 0, 'pierce_armor': 0,
        'speed': 0.10, 'color': (160, 200, 140),
        'radius': 0.3, 'separation_radius': 0.55,
        'cost': {'food': 35, 'wood': 25},
    },
    'pikeman': {
        'max_hp': 55, 'melee_armor': 0, 'pierce_armor': 0,
        'speed': 0.10, 'color': (130, 180, 120),
        'radius': 0.3, 'separation_radius': 0.55,
        'cost': {'food': 35, 'wood': 25},
    },

    # ── Archery Range ─────────────────────────────────────────────────── #
    'archer': {
        'max_hp': 30, 'melee_armor': 0, 'pierce_armor': 0,
        'speed': 0.10, 'color': (200, 160, 80),
        'radius': 0.3, 'separation_radius': 0.55,
        'cost': {'wood': 25, 'gold': 45},
    },
    'crossbowman': {
        'max_hp': 35, 'melee_armor': 0, 'pierce_armor': 0,
        'speed': 0.10, 'color': (180, 140, 70),
        'radius': 0.3, 'separation_radius': 0.55,
        'cost': {'wood': 25, 'gold': 45},
    },
    'skirmisher': {
        'max_hp': 35, 'melee_armor': 0, 'pierce_armor': 3,
        'speed': 0.10, 'color': (160, 200, 100),
        'radius': 0.3, 'separation_radius': 0.55,
        'cost': {'food': 25, 'wood': 35},
    },

    # ── Stable ────────────────────────────────────────────────────────── #
    'scout_cavalry': {
        'max_hp': 45, 'melee_armor': 0, 'pierce_armor': 2,
        'speed': 0.18, 'color': (200, 130, 80),
        'radius': 0.38, 'separation_radius': 0.65,
        'cost': {'food': 80},
    },
    'knight': {
        'max_hp': 100, 'melee_armor': 2, 'pierce_armor': 3,
        'speed': 0.15, 'color': (160, 100, 60),
        'radius': 0.38, 'separation_radius': 0.65,
        'cost': {'food': 60, 'gold': 75},
    },
    'cavalier': {
        'max_hp': 120, 'melee_armor': 2, 'pierce_armor': 4,
        'speed': 0.15, 'color': (140, 85, 50),
        'radius': 0.38, 'separation_radius': 0.65,
        'cost': {'food': 60, 'gold': 75},
    },

    # ── Monastery ─────────────────────────────────────────────────────── #
    'monk': {
        'max_hp': 30, 'melee_armor': 0, 'pierce_armor': 0,
        'speed': 0.09, 'color': (210, 190, 130),
        'radius': 0.3, 'separation_radius': 0.55,
        'cost': {'gold': 100},
    },

    # ── Siege Workshop ────────────────────────────────────────────────── #
    'battering_ram': {
        'max_hp': 175, 'melee_armor': 180, 'pierce_armor': 180,
        'speed': 0.05, 'color': (120, 90, 60),
        'radius': 0.45, 'separation_radius': 0.80,
        'cost': {'wood': 160, 'gold': 75},
    },
    'mangonel': {
        'max_hp': 50, 'melee_armor': 0, 'pierce_armor': 6,
        'speed': 0.06, 'color': (130, 100, 60),
        'radius': 0.42, 'separation_radius': 0.75,
        'cost': {'wood': 160, 'gold': 135},
    },
    'trebuchet': {
        'max_hp': 150, 'melee_armor': 2, 'pierce_armor': 8,
        'speed': 0.05, 'color': (110, 85, 50),
        'radius': 0.45, 'separation_radius': 0.80,
        'cost': {'wood': 200, 'gold': 200},
    },
}


class Unit:
    def __init__(self, unit_type, tile_x, tile_z):
        stats             = UNIT_STATS[unit_type]
        self.unit_type    = unit_type
        self.x            = float(tile_x)
        self.z            = float(tile_z)
        self.hp           = stats['max_hp']
        self.max_hp       = stats['max_hp']
        self.melee_armor  = stats['melee_armor']
        self.pierce_armor = stats['pierce_armor']
        self.speed        = stats['speed']
        self.color             = stats['color']
        self.radius            = stats['radius']
        self.separation_radius = stats['separation_radius']
        self.carry_cap    = stats.get('carry_cap', 0)
        self.gather_ticks = stats.get('gather_ticks', 180)
        self.path         = []
        self.selected     = False
        # Gathering state
        self.state          = 'idle'
        self.gather_target  = None
        self.gather_timer   = 0
        self.carried        = 0
        self.carried_type   = None
        self.drop_building  = None
        self.build_target   = None
        self.action_queue   = []      # pending actions: [{'type':..., ...}, ...]

    def set_path(self, path):
        self.path = list(path)

    def update(self):
        if not self.path:
            return
        target_x, target_z = self.path[0]
        dx   = target_x - self.x
        dz   = target_z - self.z
        dist = math.hypot(dx, dz)
        if dist <= self.speed:
            self.x = float(target_x)
            self.z = float(target_z)
            self.path.pop(0)
        else:
            self.x += dx / dist * self.speed
            self.z += dz / dist * self.speed
