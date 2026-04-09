import math

# speed: AoE2 tile/s divided by 60 to get tiles/frame at 60fps
# attack_ticks: attack interval in frames (AoE2 seconds * 60)
# attack_range: 0 = melee, >0 = ranged (in tiles)
# attack: base damage value

UNIT_STATS = {
    # ── Economy ───────────────────────────────────────────────────────── #
    'villager': {
        'max_hp': 25, 'melee_armor': 0, 'pierce_armor': 0,
        'attack': 3, 'attack_ticks': 122, 'attack_range': 0,
        'hunt_range': 4,             # ranged attack used when hunting animals
        'speed': 0.015, 'color': (220, 180, 100),
        'radius': 0.18, 'separation_radius': 0.38,
        'carry_cap': 10, 'gather_ticks': 180,
        'los_range': 4,
        'cost': {'food': 50}, 'min_age': 'dark',
    },

    # ── Infantry (Barracks) ───────────────────────────────────────────── #
    'militia': {
        'max_hp': 40, 'melee_armor': 0, 'pierce_armor': 1,
        'attack': 4, 'attack_ticks': 122, 'attack_range': 0,
        'speed': 0.020, 'color': (180, 180, 180),
        'radius': 0.3, 'separation_radius': 0.55,
        'los_range': 4,
        'cost': {'food': 60, 'gold': 20}, 'min_age': 'dark',
    },
    'man_at_arms': {
        'max_hp': 45, 'melee_armor': 1, 'pierce_armor': 2,
        'attack': 6, 'attack_ticks': 122, 'attack_range': 0,
        'speed': 0.020, 'color': (160, 160, 170),
        'radius': 0.3, 'separation_radius': 0.55,
        'los_range': 5,
        'cost': {'food': 60, 'gold': 20}, 'min_age': 'feudal',
    },
    'long_swordsman': {
        'max_hp': 60, 'melee_armor': 2, 'pierce_armor': 2,
        'attack': 9, 'attack_ticks': 122, 'attack_range': 0,
        'speed': 0.020, 'color': (140, 140, 160),
        'radius': 0.3, 'separation_radius': 0.55,
        'los_range': 5,
        'cost': {'food': 60, 'gold': 20}, 'min_age': 'castle',
    },
    'spearman': {
        'max_hp': 45, 'melee_armor': 0, 'pierce_armor': 0,
        'attack': 3, 'attack_ticks': 182, 'attack_range': 0,
        'speed': 0.020, 'color': (160, 200, 140),
        'radius': 0.3, 'separation_radius': 0.55,
        'los_range': 4,
        'cost': {'food': 35, 'wood': 25}, 'min_age': 'feudal',
    },
    'pikeman': {
        'max_hp': 55, 'melee_armor': 0, 'pierce_armor': 0,
        'attack': 4, 'attack_ticks': 182, 'attack_range': 0,
        'speed': 0.020, 'color': (130, 180, 120),
        'radius': 0.3, 'separation_radius': 0.55,
        'los_range': 4,
        'cost': {'food': 35, 'wood': 25}, 'min_age': 'castle',
    },

    # ── Archery Range ─────────────────────────────────────────────────── #
    'archer': {
        'max_hp': 30, 'melee_armor': 0, 'pierce_armor': 0,
        'attack': 4, 'attack_ticks': 122, 'attack_range': 4,
        'speed': 0.020, 'color': (200, 160, 80),
        'radius': 0.3, 'separation_radius': 0.55,
        'los_range': 4,
        'cost': {'wood': 25, 'gold': 45}, 'min_age': 'feudal',
    },
    'crossbowman': {
        'max_hp': 35, 'melee_armor': 0, 'pierce_armor': 0,
        'attack': 5, 'attack_ticks': 122, 'attack_range': 5,
        'speed': 0.020, 'color': (180, 140, 70),
        'radius': 0.3, 'separation_radius': 0.55,
        'los_range': 5,
        'cost': {'wood': 25, 'gold': 45}, 'min_age': 'castle',
    },
    'skirmisher': {
        'max_hp': 35, 'melee_armor': 0, 'pierce_armor': 3,
        'attack': 2, 'attack_ticks': 182, 'attack_range': 4,
        'speed': 0.020, 'color': (160, 200, 100),
        'radius': 0.3, 'separation_radius': 0.55,
        'los_range': 4,
        'cost': {'food': 25, 'wood': 35}, 'min_age': 'feudal',
    },

    # ── Stable ────────────────────────────────────────────────────────── #
    'scout_cavalry': {
        'max_hp': 45, 'melee_armor': 0, 'pierce_armor': 2,
        'attack': 3, 'attack_ticks': 122, 'attack_range': 0,
        'speed': 0.034, 'color': (200, 130, 80),
        'radius': 0.38, 'separation_radius': 0.65,
        'los_range': 6,
        'cost': {'food': 80}, 'min_age': 'feudal',
    },
    'knight': {
        'max_hp': 100, 'melee_armor': 2, 'pierce_armor': 2,
        'attack': 10, 'attack_ticks': 108, 'attack_range': 0,
        'speed': 0.030, 'color': (160, 100, 60),
        'radius': 0.38, 'separation_radius': 0.65,
        'los_range': 5,
        'cost': {'food': 60, 'gold': 75}, 'min_age': 'castle',
    },
    'cavalier': {
        'max_hp': 120, 'melee_armor': 2, 'pierce_armor': 2,
        'attack': 12, 'attack_ticks': 108, 'attack_range': 0,
        'speed': 0.030, 'color': (140, 85, 50),
        'radius': 0.38, 'separation_radius': 0.65,
        'los_range': 5,
        'cost': {'food': 60, 'gold': 75}, 'min_age': 'castle',
    },

    # ── Animals (neutral) ─────────────────────────────────────────────── #
    'sheep': {
        'max_hp': 8, 'melee_armor': 0, 'pierce_armor': 0,
        'attack': 0, 'attack_ticks': 0, 'attack_range': 0,
        'speed': 0.014, 'color': (230, 230, 220),
        'radius': 0.20, 'separation_radius': 0.25,
        'food_value': 100, 'los_range': 4,
        'cost': {}, 'min_age': 'dark',
    },
    'deer': {
        'max_hp': 4, 'melee_armor': 0, 'pierce_armor': 0,
        'attack': 0, 'attack_ticks': 0, 'attack_range': 0,
        'speed': 0.028, 'color': (180, 130, 70),
        'radius': 0.22, 'separation_radius': 0.30,
        'food_value': 140, 'los_range': 5,
        'cost': {}, 'min_age': 'dark',
    },
    'boar': {
        'max_hp': 45, 'melee_armor': 0, 'pierce_armor': 2,
        'attack': 7, 'attack_ticks': 90, 'attack_range': 0,
        'speed': 0.018, 'color': (110, 75, 45),
        'radius': 0.28, 'separation_radius': 0.38,
        'food_value': 300, 'los_range': 4,
        'cost': {}, 'min_age': 'dark',
    },

    # ── Monastery ─────────────────────────────────────────────────────── #
    'monk': {
        'max_hp': 30, 'melee_armor': 0, 'pierce_armor': 0,
        'attack': 0, 'attack_ticks': 0, 'attack_range': 0,
        'speed': 0.0117, 'color': (210, 190, 130),
        'radius': 0.3, 'separation_radius': 0.55,
        'los_range': 5,
        'cost': {'gold': 100}, 'min_age': 'castle',
    },

    # ── Siege Workshop ────────────────────────────────────────────────── #
    'battering_ram': {
        'max_hp': 175, 'melee_armor': 0, 'pierce_armor': 180,
        'attack': 2, 'attack_ticks': 300, 'attack_range': 0,
        'speed': 0.0083, 'color': (120, 90, 60),
        'radius': 0.45, 'separation_radius': 0.80,
        'los_range': 4,
        'cost': {'wood': 160, 'gold': 75}, 'min_age': 'castle',
    },
    'mangonel': {
        'max_hp': 50, 'melee_armor': 0, 'pierce_armor': 6,
        'attack': 40, 'attack_ticks': 360, 'attack_range': 7,
        'speed': 0.010, 'color': (130, 100, 60),
        'radius': 0.42, 'separation_radius': 0.75,
        'los_range': 7,
        'cost': {'wood': 160, 'gold': 135}, 'min_age': 'castle',
    },
    'trebuchet': {
        'max_hp': 150, 'melee_armor': 2, 'pierce_armor': 8,
        'attack': 200, 'attack_ticks': 360, 'attack_range': 16,
        'speed': 0.0133, 'color': (110, 85, 50),
        'radius': 0.45, 'separation_radius': 0.80,
        'los_range': 16,
        'cost': {'wood': 200, 'gold': 200}, 'min_age': 'imperial',
    },
}


class Unit:
    def __init__(self, unit_type, tile_x, tile_z, team=None):
        stats             = UNIT_STATS[unit_type]
        self.unit_type    = unit_type
        self.team         = team
        self.x            = float(tile_x)
        self.z            = float(tile_z)
        self.hp           = stats['max_hp']
        self.max_hp       = stats['max_hp']
        self.melee_armor  = stats['melee_armor']
        self.pierce_armor = stats['pierce_armor']
        self.attack       = stats.get('attack', 0)
        self.attack_ticks = stats.get('attack_ticks', 120)
        self.attack_range = stats.get('attack_range', 0)
        self.speed             = stats['speed']
        self.color             = stats['color']
        self.radius            = stats['radius']
        self.separation_radius = stats['separation_radius']
        self.los_range         = stats.get('los_range', 4)
        self.carry_cap    = stats.get('carry_cap', 0)
        self.gather_ticks = stats.get('gather_ticks', 180)
        self.food_value   = stats.get('food_value', 0)   # >0 for animals
        self.hunt_range   = stats.get('hunt_range', self.attack_range)
        self.role         = None    # persistent job: 'shepherd', etc.
        self.hunt_target  = None    # animal being hunted
        self.aggro_target = None    # unit this animal is chasing/attacking
        self.attack_timer = 0
        self.path         = []
        self.selected     = False
        # State machine
        self.state          = 'idle'
        self.gather_target  = None
        self.gather_timer   = 0
        self.carried        = 0
        self.carried_type   = None
        self.drop_building  = None
        self.build_target   = None
        self.action_queue   = []

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
