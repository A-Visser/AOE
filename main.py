import math
import random
import pygame
from pygame.locals import *
from game import Game
from pathfinder import find_path, is_passable, can_see
from building import BUILDING_CONFIGS

FPS        = 60
GAME_SPEED = 2.0   # game time runs this many times faster than real time
GRID_SIZE  = 200
BASE_TW    = 48    # tile diamond width  at zoom=1 (px)
BASE_TH    = 24    # tile diamond height at zoom=1 (px)
CAM_SPEED  = 5     # pixels/frame for arrow-key scroll
EDGE_ZONE  = 120   # px from screen edge before edge-scroll activates
WALL_H     = 14    # building side-wall height at zoom=1 (px)
BOT_HUD_H  = 180   # height of bottom panel
ACT_CELL   = 48    # action button size in px
ACT_PAD    = 4     # gap between action buttons
ACT_MARGIN = 8     # outer margin inside bottom panel
TRAIN_TICKS = 30 * FPS  # frames to train one unit (30 seconds)

# ── State globals ─────────────────────────────────────────────────────── #
zoom       = 1.0
MIN_ZOOM   = 0.25
MAX_ZOOM   = 4.0
offset_x   = 0.0   # pixel position of tile (0,0) top-vertex from screen left
offset_y   = 0.0   # pixel position of tile (0,0) top-vertex from screen top
screen_w   = 1920
screen_h   = 1080
_sprites   = None  # cached tile sprites at current zoom


# ── Helpers ───────────────────────────────────────────────────────────── #

def tw():
    return max(4, int(BASE_TW * zoom))

def th():
    return max(2, int(BASE_TH * zoom))

def world_to_screen(tx, tz):
    w, h = tw(), th()
    return (int((tx - tz) * w / 2 + offset_x),
            int((tx + tz) * h / 2 + offset_y))

def screen_center_tile():
    """Tile coordinate currently shown at the center of the screen."""
    w, h = tw(), th()
    rx = screen_w / 2 - offset_x
    ry = screen_h / 2 - offset_y
    return rx / w + ry / h, ry / h - rx / w

def screen_to_tile(sx, sy):
    """Convert screen pixel position to nearest tile coordinate."""
    w, h = tw(), th()
    rx = sx - offset_x
    ry = sy - offset_y
    tx = rx / w + ry / h
    tz = ry / h - rx / w
    return round(tx), round(tz)


def _make_sprites():
    w, h = tw(), th()
    result = []
    for color in [(56, 158, 56), (43, 128, 43)]:
        surf = pygame.Surface((w + 1, h + 1), pygame.SRCALPHA)
        pts  = [(w // 2, 0), (w, h // 2), (w // 2, h), (0, h // 2)]
        pygame.draw.polygon(surf, color, pts)
        result.append(surf)
    return result

def set_zoom(new_zoom):
    global zoom, offset_x, offset_y, _sprites
    cx, cz = screen_center_tile()
    zoom = max(MIN_ZOOM, min(MAX_ZOOM, new_zoom))
    w, h = tw(), th()
    offset_x = screen_w / 2 - (cx - cz) * w / 2
    offset_y = screen_h / 2 - (cx + cz) * h / 2
    _sprites = _make_sprites()

def edge_speed(dist_from_edge):
    if dist_from_edge >= EDGE_ZONE:
        return 0.0
    t = 1.0 - dist_from_edge / EDGE_ZONE
    return CAM_SPEED * (0.2 + 4.8 * t * t)


# ── Drawing ───────────────────────────────────────────────────────────── #

def draw_plane(surface):
    w, h = tw(), th()
    half = GRID_SIZE // 2
    sw, sh = surface.get_width(), surface.get_height()

    # Only iterate over diagonals (tx+tz) that are on-screen
    d_min = max(-2 * half, int((-offset_y - h) * 2 / h) - 1)
    d_max = min( 2 * half, int((sh - offset_y + h) * 2 / h) + 1)

    for d in range(d_min, d_max + 1):
        sy = int(d * h / 2 + offset_y)
        for tx in range(max(-half, d - half), min(half, d + half) + 1):
            tz = d - tx
            if not (-half <= tz < half):
                continue
            sx = int((tx - tz) * w / 2 + offset_x)
            if sx + w < 0 or sx - w > sw:
                continue
            surface.blit(_sprites[(tx + tz) & 1], (sx - w // 2, sy))


def _diamond(sx, sy):
    w, h = tw(), th()
    return [(sx, sy), (sx + w//2, sy + h//2),
            (sx, sy + h), (sx - w//2, sy + h//2)]


def draw_entities(surface, resources, buildings, font):
    """Draw resources and buildings sorted back-to-front together."""
    w, h = tw(), th()
    wh = max(2, int(WALL_H * zoom))
    sw, sh = surface.get_width(), surface.get_height()

    # Build a unified sorted list: (depth_key, type, obj)
    items = []
    for r in resources:
        items.append((r.tile_x + r.tile_z, 'res', r))
    for b in buildings:
        items.append((b.tile_x + b.tile_z + b.width + b.depth - 1, 'bld', b))
    items.sort(key=lambda x: x[0])

    for _, kind, obj in items:
        if kind == 'res':
            sx, sy = world_to_screen(obj.tile_x, obj.tile_z)
            if sx + w < 0 or sx - w > sw or sy + h < 0 or sy > sh:
                continue
            color = tuple(int(c * 255) for c in obj.color)
            pygame.draw.polygon(surface, color, _diamond(sx, sy))
            if w >= 20:
                lbl = font.render(str(obj.amount), True, (255, 255, 255))
                surface.blit(lbl, (sx - lbl.get_width() // 2,
                                   sy + h // 2 - lbl.get_height() // 2))

        else:  # building
            b = obj
            A = world_to_screen(b.tile_x,           b.tile_z)
            B = world_to_screen(b.tile_x + b.width,  b.tile_z)
            C = world_to_screen(b.tile_x + b.width,  b.tile_z + b.depth)
            D = world_to_screen(b.tile_x,            b.tile_z + b.depth)

            # Rough cull
            min_sx = min(A[0], B[0], C[0], D[0])
            max_sx = max(A[0], B[0], C[0], D[0])
            min_sy = min(A[1], B[1], C[1], D[1])
            max_sy = max(A[1], B[1], C[1], D[1]) + wh
            if max_sx < 0 or min_sx > sw or max_sy < 0 or min_sy > sh:
                continue

            color  = tuple(int(c * 255) for c in b.color)
            dark   = tuple(max(0, c - 60) for c in color)
            darker = tuple(max(0, c - 90) for c in color)

            # SE wall (right face)
            pygame.draw.polygon(surface, dark,
                [B, C, (C[0], C[1] + wh), (B[0], B[1] + wh)])
            # SW wall (left face)
            pygame.draw.polygon(surface, darker,
                [D, C, (C[0], C[1] + wh), (D[0], D[1] + wh)])
            # Top face (desaturated gray if under construction)
            if b.under_construction:
                t = b.build_ticks_done / max(b.build_ticks_total, 1)
                top_color = tuple(int(c * (0.4 + 0.6 * t)) for c in color)
            else:
                top_color = color
            pygame.draw.polygon(surface, top_color, [A, B, C, D])

            # Construction progress bar
            if b.under_construction and b.build_ticks_total > 0:
                prog = b.build_ticks_done / b.build_ticks_total
                bar_y = (A[1] + C[1]) // 2
                bar_x = (A[0] + C[0]) // 2
                bw = max(20, int(b.width * w / 2))
                pygame.draw.rect(surface, (40, 40, 40),
                                 (bar_x - bw // 2, bar_y - 3, bw, 6))
                pygame.draw.rect(surface, (80, 200, 80),
                                 (bar_x - bw // 2, bar_y - 3,
                                  int(bw * prog), 6))

            if b.label and w >= 14:
                cx = (A[0] + C[0]) // 2
                cy = (A[1] + C[1]) // 2
                lbl = font.render(b.label, True, (255, 255, 255))
                surface.blit(lbl, (cx - lbl.get_width() // 2,
                                   cy - lbl.get_height() // 2))


def draw_units(surface, units):
    w, h = tw(), th()
    for unit in units:
        sx, sy = world_to_screen(unit.x, unit.z)
        # Centre of diamond
        cx = sx
        cy = sy + h // 2
        r  = max(4, int(w * unit.radius))
        pygame.draw.circle(surface, unit.color, (cx, cy), r)
        if unit.selected:
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), r + 2, 2)


def unit_at_screen(units, sx, sy):
    """Return the unit closest to screen position (sx, sy), or None."""
    w, h = tw(), th()
    best, best_dist = None, float('inf')
    for unit in units:
        ux, uy = world_to_screen(unit.x, unit.z)
        uy += h // 2
        d = math.hypot(sx - ux, sy - uy)
        r = max(4, int(w * unit.radius))
        if d <= r + 4 and d < best_dist:
            best, best_dist = unit, d
    return best


HUD_H = 52   # height of the top bar in pixels

_POP_CAP_PER_BUILDING = {'Town Center': 5, 'Castle': 20, 'House': 5}

_ANIMAL_TYPES = {'sheep', 'deer', 'boar'}

def compute_pop_cap(buildings):
    return sum(_POP_CAP_PER_BUILDING.get(b.name, 0) for b in buildings)

def compute_pop(units):
    return sum(1 for u in units if u.unit_type not in _ANIMAL_TYPES)

_RES_ORDER  = ['food', 'wood', 'gold', 'stone']
_RES_COLORS = {
    'food':  (100, 200,  70),
    'wood':  (160, 100,  40),
    'gold':  (220, 185,  35),
    'stone': (160, 160, 160),
}

def draw_hud(surface, player, buildings, units, elapsed_secs, hud_font, bold_font):
    w = surface.get_width()

    # Background bar
    bar = pygame.Surface((w, HUD_H), pygame.SRCALPHA)
    bar.fill((12, 12, 22, 220))
    surface.blit(bar, (0, 0))
    pygame.draw.line(surface, (60, 60, 90), (0, HUD_H - 1), (w, HUD_H - 1), 1)

    cy = HUD_H // 2

    # ── Resources (left) ──────────────────────────────────────────────── #
    x = 18
    for res in _RES_ORDER:
        color  = _RES_COLORS[res]
        amount = player.resources.get(res, 0)
        icon_r = pygame.Rect(x, cy - 8, 16, 16)
        pygame.draw.rect(surface, color, icon_r)
        pygame.draw.rect(surface, (200, 200, 200), icon_r, 1)
        txt = hud_font.render(str(amount), True, (230, 230, 230))
        surface.blit(txt, (x + 20, cy - txt.get_height() // 2))
        x += 20 + txt.get_width() + 24

    # ── Centre: name placeholder + population ─────────────────────────── #
    pop     = compute_pop(units)
    cap     = compute_pop_cap(buildings)
    pop_col = (255, 120, 80) if pop >= cap else (200, 200, 200)
    centre_txt = bold_font.render("—  —", True, (160, 160, 180))
    pop_txt    = hud_font.render(f"Pop: {pop}/{cap}", True, pop_col)
    total_w    = centre_txt.get_width() + 12 + pop_txt.get_width()
    cx0 = w // 2 - total_w // 2
    surface.blit(centre_txt, (cx0, cy - centre_txt.get_height() // 2))
    surface.blit(pop_txt,    (cx0 + centre_txt.get_width() + 12,
                               cy - pop_txt.get_height() // 2))

    # ── Timer (right) ─────────────────────────────────────────────────── #
    mins, secs = divmod(elapsed_secs, 60)
    timer_txt = bold_font.render(f"{mins:02d}:{secs:02d}", True, (220, 220, 220))
    surface.blit(timer_txt, (w - timer_txt.get_width() - 18,
                              cy - timer_txt.get_height() // 2))


# ── Bottom HUD ────────────────────────────────────────────────────────── #

_HOTKEY_MAP = {
    K_q:(0,0), K_w:(1,0), K_e:(2,0), K_r:(3,0), K_t:(4,0),
    K_a:(0,1), K_s:(1,1), K_d:(2,1), K_f:(3,1), K_g:(4,1),
    K_z:(0,2), K_x:(1,2), K_c:(2,2), K_v:(3,2), K_b:(4,2),
}
_HOTKEY_LABEL = {v: k_name for k_name, (k, v) in {
    'Q':(K_q,(0,0)),'W':(K_w,(1,0)),'E':(K_e,(2,0)),'R':(K_r,(3,0)),'T':(K_t,(4,0)),
    'A':(K_a,(0,1)),'S':(K_s,(1,1)),'D':(K_d,(2,1)),'F':(K_f,(3,1)),'G':(K_g,(4,1)),
    'Z':(K_z,(0,2)),'X':(K_x,(1,2)),'C':(K_c,(2,2)),'V':(K_v,(3,2)),'B':(K_b,(4,2)),
}.items()}

from player import AGES, TEAMS  # age ordering, team data

def _is_unlocked(action, player, game):
    """Return True if the action is available to the player right now.

    Checks (in order):
      1. min_age           – player must be at least this age
      2. max_age           – player must not have exceeded this age
      3. requires_bld      – list of building names; at least one of each must
                             exist (completed) among game.buildings
      4. requires_bld_count– minimum number of non-TC completed buildings
    """
    age_idx = AGES.index(player.age)
    min_age = action.get('min_age', 'dark')
    if age_idx < AGES.index(min_age):
        return False

    max_age = action.get('max_age')
    if max_age and age_idx > AGES.index(max_age):
        return False

    for bld_name in action.get('requires_bld', []):
        if not any(b.name == bld_name and not b.under_construction
                   for b in game.buildings):
            return False

    min_count = action.get('requires_bld_count', 0)
    if min_count > 0:
        count = sum(1 for b in game.buildings
                    if b.name != 'Town Center' and not b.under_construction)
        if count < min_count:
            return False

    return True


def _filter_actions(action_list, player, game=None):
    """Return only unlocked actions."""
    if game is None:
        # fallback: age-only filter (used in contexts without game ref)
        return [a for a in action_list
                if AGES.index(player.age) >= AGES.index(a.get('min_age', 'dark'))]
    return [a for a in action_list if _is_unlocked(a, player, game)]


_BUILDING_ACTIONS = {
    'Town Center': [
        {'pos': (0, 0), 'label': 'V',  'action': 'train_villager',  'min_age': 'dark'},
        {'pos': (0, 1), 'label': 'F↑', 'action': 'age_up:feudal',   'min_age': 'dark',   'max_age': 'dark',
         'requires_bld_count': 2, 'bg': (30, 60, 100)},
        {'pos': (0, 1), 'label': 'C↑', 'action': 'age_up:castle',   'min_age': 'feudal', 'max_age': 'feudal',
         'bg': (30, 60, 100)},
        {'pos': (0, 1), 'label': 'I↑', 'action': 'age_up:imperial', 'min_age': 'castle', 'max_age': 'castle',
         'bg': (30, 60, 100)},
    ],
    'Barracks': [
        {'pos': (0, 0), 'label': 'Mi', 'action': 'train_militia',  'min_age': 'dark'},
    ],
    'Archery Range': [
        {'pos': (0, 0), 'label': 'Ar', 'action': 'train_archer',   'min_age': 'feudal'},
    ],
    'Stable': [
        {'pos': (0, 0), 'label': 'Sc', 'action': 'train_scout',    'min_age': 'feudal'},
    ],
}

_UNIT_ACTIONS = {
    'villager': [
        {'pos': (0, 0), 'label': 'R', 'action': 'build_resource', 'min_age': 'dark'},
        {'pos': (1, 0), 'label': 'M', 'action': 'build_military', 'min_age': 'dark'},
    ],
}

_BACK_BTN = {'pos': (4, 2), 'label': '<', 'action': 'back',
             'bg': (40, 40, 55), 'min_age': 'dark'}

_UNIT_SUBMENUS = {
    'build_resource': [
        {'pos': (0, 0), 'label': 'H',  'action': 'place_House',        'min_age': 'dark'},
        {'pos': (1, 0), 'label': 'Ml', 'action': 'place_Mill',         'min_age': 'dark',   'bg': (120, 80, 30)},
        {'pos': (2, 0), 'label': 'Mi', 'action': 'place_Mine',         'min_age': 'dark',   'bg': (120, 80, 30)},
        {'pos': (3, 0), 'label': 'LC', 'action': 'place_Lumber Camp',  'min_age': 'dark',   'bg': (120, 80, 30)},
        {'pos': (4, 0), 'label': 'Fa', 'action': 'place_Farm',         'min_age': 'dark',   'bg': (100, 90, 20),
         'requires_bld': ['Mill']},
        _BACK_BTN,
    ],
    'build_military': [
        {'pos': (0, 0), 'label': 'B',  'action': 'place_Barracks',     'min_age': 'dark',   'bg': (100, 40, 40)},
        {'pos': (1, 0), 'label': 'AR', 'action': 'place_Archery Range','min_age': 'feudal', 'bg': (100, 70, 30)},
        {'pos': (2, 0), 'label': 'St', 'action': 'place_Stable',       'min_age': 'feudal', 'bg': (80, 55, 20)},
        _BACK_BTN,
    ],
}

# Buildings that trigger instant resource deposit when a villager is assigned to build them
_RESOURCE_BUILDINGS = {'Mill', 'Mine', 'Lumber Camp', 'Farm'}

# Resource types each building auto-sends builders to gather after completion
_BUILDING_AUTO_GATHER = {
    'Mill':        {'berries'},
    'Mine':        {'gold', 'stone'},
    'Lumber Camp': {'wood'},
}


def _find_spawn_tile(game, b):
    """Find empty tile adjacent to building b, preferring the side nearest the rally point."""
    candidates = []
    for dx in range(b.width):
        candidates.append((b.tile_x + dx, b.tile_z - 1))
        candidates.append((b.tile_x + dx, b.tile_z + b.depth))
    for dz in range(b.depth):
        candidates.append((b.tile_x - 1,       b.tile_z + dz))
        candidates.append((b.tile_x + b.width,  b.tile_z + dz))

    empty = [pos for pos in candidates if game.is_tile_empty(*pos)]
    if not empty:
        return None

    if b.rally_x is not None:
        empty.sort(key=lambda p: math.hypot(p[0] - b.rally_x, p[1] - b.rally_z))

    return empty[0]


def update_production(game, player):
    pop_cap = compute_pop_cap(game.buildings)
    pop     = compute_pop(game.units)
    for b in game.buildings:
        if b.under_construction or not b.queue:
            b.queue_ticks = 0
            continue
        cur = b.queue[0]
        # Pause unit training (but not age-ups) when at pop cap
        if not cur.startswith('age_up:') and pop >= pop_cap:
            continue
        # Determine ticks needed for the current queue head
        cur_total = AGE_UP_DATA[cur]['ticks'] if cur.startswith('age_up:') else TRAIN_TICKS
        b.queue_ticks += 1
        if b.queue_ticks >= cur_total:
            item = b.queue.pop(0)
            b.queue_ticks = 0
            if item.startswith('age_up:'):
                player.age = AGE_UP_DATA[item]['target']
                continue
            unit_type = item
            spawn = _find_spawn_tile(game, b)
            if spawn:
                unit = game.add_unit(unit_type, spawn[0], spawn[1], team=b.team)
                if b.rally_x is not None:
                    rally_tile = game.get_tile(b.rally_x, b.rally_z)
                    if rally_tile and rally_tile['type'] == 'resource':
                        gather_resource(game, [unit], rally_tile['obj'])
                    elif rally_tile and rally_tile['type'] == 'building':
                        rally_bld = rally_tile['obj']
                        if rally_bld.under_construction and unit.carry_cap > 0:
                            _assign_builder(unit, rally_bld, game)
                        else:
                            path = find_path(game, spawn[0], spawn[1],
                                             b.rally_x, b.rally_z)
                            if path:
                                unit.set_path(path)
                    else:
                        path = find_path(game, spawn[0], spawn[1],
                                         b.rally_x, b.rally_z)
                        if path:
                            unit.set_path(path)


# Resources are deposited as this type (berries → food)
_DEPOSIT_AS = {'berries': 'food'}

# Buildings that accept drop-off for each resource type
_DROP_ACCEPTS = {
    'Town Center':   {'wood', 'gold', 'stone', 'food', 'berries'},
    'Mine':          {'gold', 'stone'},
    'Lumber Camp':   {'wood'},
    'Mill':          {'food', 'berries'},
}


def _find_drop_building(game, unit, res_type):
    """Nearest building that accepts drop-off for res_type."""
    best, best_dist = None, float('inf')
    for b in game.buildings:
        if res_type not in _DROP_ACCEPTS.get(b.name, set()):
            continue
        bc_x = b.tile_x + b.width  / 2.0
        bc_z = b.tile_z + b.depth  / 2.0
        d = math.hypot(unit.x - bc_x, unit.z - bc_z)
        if d < best_dist:
            best, best_dist = b, d
    return best


def _gather_adj_tile(game, res):
    """Find a passable tile adjacent to a resource tile."""
    tx, tz = res.tile_x, res.tile_z
    for pos in [(tx+1,tz),(tx-1,tz),(tx,tz+1),(tx,tz-1),
                (tx+1,tz+1),(tx+1,tz-1),(tx-1,tz+1),(tx-1,tz-1)]:
        if is_passable(game, pos[0], pos[1]):
            return pos
    return (tx + 1, tz)


def _start_return(game, unit):
    drop = _find_drop_building(game, unit, unit.carried_type)
    if drop is None:
        unit.state = 'idle'
        return
    unit.drop_building = drop
    unit.state = 'return_move'
    edge = _find_building_edge_tile(game, drop, unit)
    if edge:
        path = find_path(game, unit.x, unit.z, edge[0], edge[1])
        if path:
            unit.set_path(path)


def gather_resource(game, units, res):
    """Issue a gather command to all gatherer units."""
    for unit in units:
        if unit.carry_cap == 0:
            continue
        unit.role = res.res_type   # persist gathering role
        unit.build_target = None
        unit.action_queue = []
        adj = _gather_adj_tile(game, res)
        path = find_path(game, unit.x, unit.z, adj[0], adj[1])
        unit.gather_target = res
        unit.gather_timer  = 0
        if path:
            unit.state = 'gather_move'
            unit.set_path(path)
        else:
            unit.state = 'gathering'   # already adjacent


def slaughter_sheep(game, player, villagers, sheep):
    """Send villagers to slaughter a sheep. When close, sheep dies and becomes food."""
    for unit in villagers:
        unit.role          = 'shepherd'
        unit.build_target  = None
        unit.action_queue  = []
        unit.gather_target = sheep        # sheep Unit acts as target
        unit.gather_timer  = 0
        path = find_path(game, unit.x, unit.z, round(sheep.x), round(sheep.z))
        if path:
            unit.state = 'slaughter_move'
            unit.set_path(path)
        else:
            unit.state = 'slaughtering'


def _convert_sheep_to_food(game, player, sheep):
    """Remove sheep unit, place two food ResourceTiles at its location."""
    from resource import ResourceTile
    if sheep in game.units:
        game.units.remove(sheep)
    tx, tz = round(sheep.x), round(sheep.z)

    candidates = [(tx, tz), (tx+1, tz), (tx-1, tz), (tx, tz+1), (tx, tz-1),
                  (tx+1, tz+1), (tx-1, tz+1), (tx+1, tz-1), (tx-1, tz-1)]
    placed = []
    half = max(1, sheep.food_value // 2)
    for pos in candidates:
        if not game.tiles.get(pos):
            tile = ResourceTile('berries', pos[0], pos[1], half, (0.85, 0.85, 0.80))
            game.resources.append(tile)
            game.tiles[pos] = {'type': 'resource', 'obj': tile}
            placed.append(tile)
            if len(placed) == 2:
                break

    return placed[0] if placed else None


def start_hunt(game, villagers, animal):
    """Send villagers to hunt an animal (boar/deer) using ranged attack."""
    for unit in villagers:
        unit.build_target  = None
        unit.action_queue  = []
        unit.hunt_target   = animal
        unit.attack_timer  = 0
        path = find_path(game, unit.x, unit.z, round(animal.x), round(animal.z))
        unit.state = 'hunt_move'
        if path:
            unit.set_path(path)


def _animal_to_food(game, animal):
    """Remove a dead animal and place a food ResourceTile at its position."""
    from resource import ResourceTile
    if animal in game.units:
        game.units.remove(animal)
    tx, tz = round(animal.x), round(animal.z)
    for ddx, ddz in [(0,0),(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1)]:
        if not game.tiles.get((tx + ddx, tz + ddz)):
            tile = ResourceTile('berries', tx + ddx, tz + ddz,
                                animal.food_value, (0.88, 0.80, 0.55))
            game.resources.append(tile)
            game.tiles[(tx + ddx, tz + ddz)] = {'type': 'resource', 'obj': tile}
            return tile
    return None


def update_hunt(game, player):
    """Handle hunt_move/hunting states for villagers and boar/deer AI."""
    dead = []

    for unit in list(game.units):
        # ── Villager hunting ─────────────────────────────────────────── #
        if unit.state in ('hunt_move', 'hunting'):
            target = unit.hunt_target
            if target is None or target not in game.units:
                unit.hunt_target = None
                unit.state = 'idle'
                continue
            dist = math.hypot(unit.x - target.x, unit.z - target.z)
            if unit.state == 'hunt_move':
                if dist <= unit.hunt_range:
                    unit.state = 'hunting'
                    unit.set_path([])
                    unit.attack_timer = 0
                elif not unit.path:
                    path = find_path(game, unit.x, unit.z,
                                     round(target.x), round(target.z))
                    if path:
                        unit.set_path(path)
            else:  # hunting
                if dist > unit.hunt_range + 1.5:
                    unit.state = 'hunt_move'
                    continue
                unit.attack_timer += 1
                if unit.attack_timer >= unit.attack_ticks:
                    unit.attack_timer = 0
                    dmg = max(0, unit.attack - target.pierce_armor)
                    target.hp -= dmg
                    if target.hp <= 0 and target not in dead:
                        dead.append(target)
                        continue
                    # Trigger animal reaction on first hit
                    if target.aggro_target is None:
                        target.aggro_target = unit
                        if target.unit_type == 'boar':
                            target.state = 'charging'
                        elif target.unit_type == 'deer':
                            target.state = 'fleeing'

        # ── Boar AI ──────────────────────────────────────────────────── #
        elif unit.unit_type == 'boar' and unit.state in ('charging', 'boar_attack'):
            target = unit.aggro_target
            if target is None or target not in game.units:
                unit.aggro_target = None
                unit.state = 'idle'
                continue
            dist = math.hypot(unit.x - target.x, unit.z - target.z)
            if unit.state == 'charging':
                if dist <= 1.2:
                    unit.state = 'boar_attack'
                    unit.attack_timer = 0
                elif not unit.path:
                    path = find_path(game, unit.x, unit.z,
                                     round(target.x), round(target.z))
                    if path:
                        unit.set_path(path)
            else:  # boar_attack
                if dist > 1.8:
                    unit.state = 'charging'
                    continue
                unit.attack_timer += 1
                if unit.attack_timer >= unit.attack_ticks:
                    unit.attack_timer = 0
                    dmg = max(0, unit.attack - target.pierce_armor)
                    target.hp -= dmg
                    # Villager death (just idle them for now; full death TBD)
                    if target.hp <= 0:
                        target.hp = 0
                        target.state = 'idle'

        # ── Deer AI ──────────────────────────────────────────────────── #
        elif unit.unit_type == 'deer' and unit.state == 'fleeing':
            attacker = unit.aggro_target
            if attacker is None or attacker not in game.units:
                unit.aggro_target = None
                unit.state = 'idle'
                continue
            if not unit.path:
                dx = unit.x - attacker.x
                dz = unit.z - attacker.z
                d  = math.hypot(dx, dz) or 1.0
                half = GRID_SIZE // 2
                nx = round(unit.x + dx / d * 12)
                nz = round(unit.z + dz / d * 12)
                nx = max(-half + 2, min(half - 2, nx))
                nz = max(-half + 2, min(half - 2, nz))
                path = find_path(game, unit.x, unit.z, nx, nz)
                if path:
                    unit.set_path(path)
                else:
                    unit.aggro_target = None
                    unit.state = 'idle'

    # Convert dead animals to food and notify hunters
    for animal in dead:
        food_tile = _animal_to_food(game, animal)
        for u in game.units:
            if u.hunt_target is animal:
                u.hunt_target = None
                if food_tile:
                    gather_resource(game, [u], food_tile)
                else:
                    _start_next_action(u, game, player)


def update_gathering(game, player):
    for unit in game.units:
        if unit.carry_cap == 0 or unit.state not in (
                'gather_move', 'gathering', 'return_move',
                'slaughter_move', 'slaughtering'):
            continue

        if unit.state == 'gather_move':
            if not unit.path:
                if unit.gather_target and unit.gather_target.amount > 0:
                    rx = unit.gather_target.tile_x
                    rz = unit.gather_target.tile_z
                    if math.hypot(unit.x - rx, unit.z - rz) < 2.0:
                        unit.state = 'gathering'
                        unit.gather_timer = 0

        elif unit.state == 'gathering':
            if unit.gather_target is None or unit.gather_target.amount <= 0:
                if unit.carried > 0:
                    _start_return(game, unit)
                else:
                    unit.gather_target = None
                    _start_next_action(unit, game, player)
                continue
            unit.gather_timer += 1
            if unit.gather_timer >= unit.gather_ticks:
                unit.gather_timer = 0
                take = min(1, unit.gather_target.amount,
                           unit.carry_cap - unit.carried)
                unit.gather_target.amount -= take
                unit.carried              += take
                unit.carried_type          = unit.gather_target.res_type
                if unit.carried >= unit.carry_cap:
                    _start_return(game, unit)

        elif unit.state == 'return_move':
            if not unit.path and unit.drop_building:
                if near_building(unit, unit.drop_building):
                    res_key = _DEPOSIT_AS.get(unit.carried_type, unit.carried_type)
                    player.resources[res_key] = \
                        player.resources.get(res_key, 0) + unit.carried
                    unit.carried = 0
                    if unit.gather_target and unit.gather_target.amount > 0:
                        adj = _gather_adj_tile(game, unit.gather_target)
                        path = find_path(game, unit.x, unit.z, adj[0], adj[1])
                        unit.state = 'gather_move'
                        if path:
                            unit.set_path(path)
                        else:
                            unit.state = 'gathering'
                    else:
                        unit.gather_target = None
                        _start_next_action(unit, game, player)

        elif unit.state in ('slaughter_move', 'slaughtering'):
            sheep = unit.gather_target
            if sheep is None or sheep not in game.units:
                unit.state = 'idle'
                unit.gather_target = None
                continue
            if math.hypot(unit.x - sheep.x, unit.z - sheep.z) <= 1.5:
                # Close enough — convert immediately
                food_tile = _convert_sheep_to_food(game, player, sheep)
                unit.gather_target = None
                if food_tile:
                    gather_resource(game, [unit], food_tile)
                else:
                    _start_next_action(unit, game, player)
            elif not unit.path:
                # Path to a tile adjacent to the sheep, not on top of it
                adj = _gather_adj_tile(game, type('_', (), {
                    'tile_x': round(sheep.x), 'tile_z': round(sheep.z)})())
                path = find_path(game, unit.x, unit.z, adj[0], adj[1])
                unit.state = 'slaughter_move'
                if path:
                    unit.set_path(path)


def near_building(unit, b, margin=1.5):
    """True if unit is within margin tiles of the building footprint.
    General utility used for: resource drop-off, construction start, combat.
    """
    nx = max(b.tile_x, min(b.tile_x + b.width  - 1, unit.x))
    nz = max(b.tile_z, min(b.tile_z + b.depth - 1, unit.z))
    return math.hypot(unit.x - nx, unit.z - nz) < margin


def _find_building_edge_tile(game, b, unit):
    """Nearest passable tile just outside the building boundary to unit."""
    best, best_d = None, float('inf')
    candidates = []
    for dx in range(b.width):
        candidates.append((b.tile_x + dx, b.tile_z - 1))
        candidates.append((b.tile_x + dx, b.tile_z + b.depth))
    for dz in range(b.depth):
        candidates.append((b.tile_x - 1,          b.tile_z + dz))
        candidates.append((b.tile_x + b.width,     b.tile_z + dz))
    for pos in candidates:
        if is_passable(game, pos[0], pos[1]):
            d = math.hypot(unit.x - pos[0], unit.z - pos[1])
            if d < best_d:
                best_d, best = d, pos
    return best


def action_at_screen(sx, sy):
    """Return (col, row) of the action button under (sx, sy), or None."""
    bx = ACT_MARGIN
    by = screen_h - BOT_HUD_H + ACT_MARGIN
    col = (sx - bx) // (ACT_CELL + ACT_PAD)
    row = (sy - by) // (ACT_CELL + ACT_PAD)
    if 0 <= col < 5 and 0 <= row < 3:
        lx = (sx - bx) % (ACT_CELL + ACT_PAD)
        ly = (sy - by) % (ACT_CELL + ACT_PAD)
        if lx < ACT_CELL and ly < ACT_CELL:
            return int(col), int(row)
    return None


_TRAIN_ACTIONS = {
    'train_villager': 'villager',
    'train_militia':  'militia',
    'train_archer':   'archer',
    'train_scout':    'scout_cavalry',
}

# age_up:<target> → cost, duration (ticks), display label, target age key
AGE_UP_DATA = {
    'age_up:feudal':   {'cost': {'food': 500},              'ticks': 130*FPS, 'label': 'F↑', 'target': 'feudal'},
    'age_up:castle':   {'cost': {'food': 800, 'gold': 200}, 'ticks': 160*FPS, 'label': 'C↑', 'target': 'castle'},
    'age_up:imperial': {'cost': {'food': 1000,'gold': 800}, 'ticks': 190*FPS, 'label': 'I↑', 'target': 'imperial'},
}


def _fire_action(pos, selected_building, selected_unit, action_submenu,
                 player, game, placement_mode=None):
    """Execute the action at grid position pos.
    Returns a command tuple or None:
      ('set_submenu', name)  – open a submenu
      ('place', bld_name)    – enter placement mode
      None                   – action fired inline (or nothing to do)
    """
    if placement_mode:
        if pos == (4, 2):
            return ('cancel_place', None)
        return None

    if selected_building:
        for a in _filter_actions(_BUILDING_ACTIONS.get(selected_building.name, []), player, game):
            if a['pos'] == pos:
                act = a['action']
                if act.startswith('age_up:'):
                    data = AGE_UP_DATA[act]
                    cost = data['cost']
                    if any(q.startswith('age_up:') for q in selected_building.queue):
                        return None  # already queued
                    if all(player.resources.get(r, 0) >= amt for r, amt in cost.items()):
                        for r, amt in cost.items():
                            player.resources[r] -= amt
                        selected_building.queue.append(act)
                    return None
                unit_type = _TRAIN_ACTIONS.get(act)
                if unit_type:
                    from unit import UNIT_STATS
                    cost = UNIT_STATS[unit_type].get('cost', {})
                    if all(player.resources.get(r, 0) >= amt
                           for r, amt in cost.items()):
                        for r, amt in cost.items():
                            player.resources[r] -= amt
                        selected_building.queue.append(unit_type)
                return None
        return None

    if selected_unit:
        raw = (_UNIT_SUBMENUS.get(action_submenu, []) if action_submenu
               else _UNIT_ACTIONS.get(selected_unit.unit_type, []))
        for a in _filter_actions(raw, player, game):
            if a['pos'] == pos:
                act = a['action']
                if act in ('build_resource', 'build_military'):
                    return ('set_submenu', act)
                if act == 'back':
                    return ('back', None)
                if act.startswith('place_'):
                    bld_name = act[len('place_'):]
                    if not can_afford(player, bld_name):
                        return None   # silently do nothing
                    return ('place', bld_name)
                return None
    return None


def _assign_builder(unit, building, game):
    """Send a villager to build a building."""
    unit.action_queue  = []   # direct command clears queue
    unit.state         = 'build_move'
    unit.build_target  = building
    unit.gather_target = None

    if near_building(unit, building):
        unit.state = 'building'
        return

    # Collect all passable edge tiles sorted nearest-first
    candidates = []
    for dx in range(building.width):
        for pos in [(building.tile_x + dx, building.tile_z - 1),
                    (building.tile_x + dx, building.tile_z + building.depth)]:
            if is_passable(game, pos[0], pos[1]):
                candidates.append(pos)
    for dz in range(building.depth):
        for pos in [(building.tile_x - 1,             building.tile_z + dz),
                    (building.tile_x + building.width, building.tile_z + dz)]:
            if is_passable(game, pos[0], pos[1]):
                candidates.append(pos)
    candidates.sort(key=lambda p: math.hypot(unit.x - p[0], unit.z - p[1]))

    for pos in candidates:
        path = find_path(game, unit.x, unit.z, pos[0], pos[1])
        if path:
            unit.set_path(path)
            return


def can_afford(player, bld_name):
    """Return True if player has enough resources to place bld_name."""
    cost = BUILDING_CONFIGS.get(bld_name, {}).get('cost', {})
    return all(player.resources.get(res, 0) >= amt
               for res, amt in cost.items())


_PRODUCTION_BUILDINGS = {
    'Town Center', 'Barracks', 'Archery Range', 'Stable',
    'Monastery', 'Castle', 'Siege Workshop',
}


def place_building(game, player, bld_name, tx, tz, builders):
    """Deduct cost, create building under construction, assign builders.
    Returns the new Building, or None if the player can't afford it.
    """
    if not can_afford(player, bld_name):
        return None
    cost = BUILDING_CONFIGS[bld_name].get('cost', {})
    for res, amt in cost.items():
        player.resources[res] -= amt
    cfg   = BUILDING_CONFIGS[bld_name]
    b = game.add_building(bld_name, tx, tz,
                          cfg['size'], cfg['size'],
                          cfg['color'], cfg['label'], team=player.team)
    b.under_construction = True
    # Set default rally point one tile past the front edge, centered
    if bld_name in _PRODUCTION_BUILDINGS:
        b.rally_x = tx + cfg['size'] // 2
        b.rally_z = tz + cfg['size'] + 1
    is_resource_bld = bld_name in _RESOURCE_BUILDINGS
    for unit in builders:
        if is_resource_bld and unit.carried > 0:
            res_key = _DEPOSIT_AS.get(unit.carried_type, unit.carried_type)
            if res_key:
                player.resources[res_key] = player.resources.get(res_key, 0) + unit.carried
            unit.carried = 0
            unit.carried_type = None
        _assign_builder(unit, b, game)
    return b


def update_builders(game, player):
    """Advance build_move → building state for units near their build target."""
    for unit in game.units:
        if unit.state == 'build_move':
            if not unit.path and unit.build_target:
                if near_building(unit, unit.build_target, margin=2.5):
                    unit.state = 'building'
        elif unit.state == 'building':
            if unit.build_target and not unit.build_target.under_construction:
                unit.build_target = None
                _start_next_action(unit, game, player)


def _find_nearest_resource(game, unit, res_types):
    best, best_d = None, float('inf')
    for r in game.resources:
        if r.res_type in res_types and r.amount > 0:
            d = math.hypot(unit.x - r.tile_x, unit.z - r.tile_z)
            if d < best_d:
                best_d, best = d, r
    return best


def _find_nearest_sheep(game, unit):
    """Return the nearest sheep that belongs to this unit's team (or unconverted)."""
    best, best_d = None, float('inf')
    for u in game.units:
        if u.unit_type == 'sheep' and (u.team is None or u.team == unit.team):
            d = math.hypot(unit.x - u.x, unit.z - u.z)
            if d < best_d:
                best_d, best = d, u
    return best


# Maps gather role → resource types to search for
_ROLE_RES_TYPES = {
    'wood':    {'wood'},
    'gold':    {'gold'},
    'stone':   {'stone'},
    'berries': {'berries'},
}


def update_construction(game, player):
    """Advance construction progress; log-scaled speed with multiple builders."""
    farms_to_convert = []
    for b in game.buildings:
        if not b.under_construction:
            continue
        n = sum(1 for u in game.units
                if u.state == 'building' and u.build_target is b)
        if n == 0:
            continue
        # log2(n+1) workers equivalent: 1→1x, 2→1.58x, 4→2.32x
        b.build_ticks_done += math.log2(n + 1)
        if b.build_ticks_done >= b.build_ticks_total:
            b.under_construction = False
            if b.name == 'Farm':
                farms_to_convert.append(b)
                continue
            auto_res = _BUILDING_AUTO_GATHER.get(b.name)
            for u in game.units:
                if u.build_target is b:
                    u.build_target = None
                    if auto_res:
                        res = _find_nearest_resource(game, u, auto_res)
                        if res:
                            gather_resource(game, [u], res)
                            continue
                    _start_next_action(u, game, player)

    # Convert completed farms into food resource tiles
    from resource import ResourceTile
    for b in farms_to_convert:
        game.buildings.remove(b)
        for dx in range(b.width):
            for dz in range(b.depth):
                game.tiles.pop((b.tile_x + dx, b.tile_z + dz), None)
        farm_tile = ResourceTile('berries', b.tile_x, b.tile_z, 250,
                                 (0.76, 0.66, 0.12))
        game.resources.append(farm_tile)
        game.tiles[(b.tile_x, b.tile_z)] = {'type': 'resource', 'obj': farm_tile}
        for u in game.units:
            if u.build_target is b:
                u.build_target = None
                gather_resource(game, [u], farm_tile)


def _sheep_at_tile(game, tx, tz, radius=0.5):
    """Return a sheep unit whose position is within radius of (tx, tz), or None."""
    for u in game.units:
        if u.unit_type == 'sheep' and math.hypot(u.x - tx, u.z - tz) <= radius:
            return u
    return None


_HUNT_ANIMALS = {'boar', 'deer'}

def _hunt_animal_at_tile(game, tx, tz, radius=1.2):
    """Return a huntable animal (boar/deer) near (tx, tz), or None."""
    for u in game.units:
        if u.unit_type in _HUNT_ANIMALS and math.hypot(u.x - tx, u.z - tz) <= radius:
            return u
    return None


_SHEEP_CONVERT_RADIUS = 3.0   # tiles — any friendly unit within this range claims a sheep
_SHEEP_KILL_RADIUS    = 0.8   # tiles — unit must be this close to "kill" and collect food

def any_friendly_can_see(game, player, tx, tz):
    """True if any unit on the player's team has LOS to tile (tx, tz)."""
    for unit in game.units:
        if unit.team == player.team:
            if can_see(game, unit.x, unit.z, tx, tz, unit.los_range):
                return True
    return False


def update_sheep(game, player):
    """Convert neutral sheep to player's team when a friendly unit has LOS.
    Sheep with food_value that reach 0 hp drop food into the player's stockpile
    and are removed.
    """
    dead = []
    for unit in game.units:
        if unit.unit_type != 'sheep':
            continue

        # Conversion: neutral sheep → team of the first friendly unit with LOS
        if unit.team is None:
            for other in game.units:
                if other is unit or other.unit_type == 'sheep':
                    continue
                if can_see(game, other.x, other.z, unit.x, unit.z, other.los_range):
                    unit.team = other.team
                    break

        # Death check: hp <= 0 → add food
        if unit.hp <= 0:
            if unit.food_value > 0:
                # Award food to the team that owns (or converted) the sheep
                player.resources['food'] = player.resources.get('food', 0) + unit.food_value
            dead.append(unit)

    for unit in dead:
        game.units.remove(unit)


def cleanup_resources(game):
    """Remove depleted resource tiles from the map."""
    depleted = [r for r in game.resources if r.amount <= 0]
    for r in depleted:
        game.resources.remove(r)
        game.tiles.pop((r.tile_x, r.tile_z), None)
        # Clear any unit gather_targets pointing to this tile
        for u in game.units:
            if u.gather_target is r:
                u.gather_target = None


def draw_placement_ghost(surface, bld_name, mx, my, game, player):
    """Draw a semi-transparent building footprint under the cursor."""
    cfg  = BUILDING_CONFIGS.get(bld_name)
    if not cfg:
        return
    size = cfg['size']
    tx, tz = screen_to_tile(mx, my)

    tiles_clear = all(game.is_tile_empty(tx + dx, tz + dz)
                      for dx in range(size) for dz in range(size))
    valid = tiles_clear and can_afford(player, bld_name)

    A = world_to_screen(tx,        tz)
    B = world_to_screen(tx + size, tz)
    C = world_to_screen(tx + size, tz + size)
    D = world_to_screen(tx,        tz + size)

    min_x = min(A[0], B[0], C[0], D[0]) - 4
    min_y = min(A[1], B[1], C[1], D[1]) - 4
    max_x = max(A[0], B[0], C[0], D[0]) + 4
    max_y = max(A[1], B[1], C[1], D[1]) + 4
    gw, gh = max(1, max_x - min_x), max(1, max_y - min_y)

    ghost = pygame.Surface((gw, gh), pygame.SRCALPHA)
    pts   = [(p[0] - min_x, p[1] - min_y) for p in (A, B, C, D)]
    fill   = (160, 160, 160, 110) if valid else (200, 50, 50, 110)
    border = (200, 200, 200, 220) if valid else (220, 80, 80, 220)
    pygame.draw.polygon(ghost, fill,   pts)
    pygame.draw.polygon(ghost, border, pts, 2)
    surface.blit(ghost, (min_x, min_y))


def _draw_team_badge(surface, obj, player, x, y, font):
    """Draw a small color swatch + team name + relationship label."""
    team_key = getattr(obj, 'team', None)
    if team_key is None:
        return
    tdata = TEAMS.get(team_key, {})
    tc = tdata.get('color', (128, 128, 128))
    tname = tdata.get('display', team_key.capitalize())

    if team_key == player.team:
        rel = 'You'
        rel_col = (100, 200, 100)
    else:
        rel = 'Enemy'
        rel_col = (220, 80, 80)

    # Color swatch
    pygame.draw.rect(surface, tc, (x, y, 12, 12))
    pygame.draw.rect(surface, (200, 200, 200), (x, y, 12, 12), 1)
    # Team name
    t = font.render(f"{tname} — {rel}", True, rel_col)
    surface.blit(t, (x + 16, y))


def draw_bot_hud(surface, selected_bld, selected_unit, sel_count,
                 selected_res, action_submenu, placement_mode,
                 player, game, hud_font, bold_font):
    panel_y = screen_h - BOT_HUD_H
    sw = surface.get_width()

    # Background panel
    panel = pygame.Surface((sw, BOT_HUD_H), pygame.SRCALPHA)
    panel.fill((10, 10, 18, 230))
    surface.blit(panel, (0, panel_y))
    pygame.draw.line(surface, (60, 60, 90), (0, panel_y), (sw, panel_y), 1)

    # ── Action grid (5×3) ─────────────────────────────────────────────── #
    if placement_mode:
        actions = [{'pos': (4, 2), 'label': 'X', 'action': 'cancel_place',
                    'bg': (100, 30, 30), 'min_age': 'dark'}]
    elif selected_bld:
        actions = _filter_actions(
            _BUILDING_ACTIONS.get(selected_bld.name, []), player, game)
    elif selected_unit:
        raw = (_UNIT_SUBMENUS.get(action_submenu, []) if action_submenu
               else _UNIT_ACTIONS.get(selected_unit.unit_type, []))
        actions = _filter_actions(raw, player, game)
    else:
        actions = []
    action_map = {a['pos']: a for a in actions}

    for row in range(3):
        for col in range(5):
            bx = ACT_MARGIN + col * (ACT_CELL + ACT_PAD)
            by = panel_y + ACT_MARGIN + row * (ACT_CELL + ACT_PAD)
            act = action_map.get((col, row))
            if act:
                bg = act.get('bg', (28, 28, 36))
            else:
                bg = (14, 14, 20)
            pygame.draw.rect(surface, bg, (bx, by, ACT_CELL, ACT_CELL))
            pygame.draw.rect(surface, (70, 70, 90), (bx, by, ACT_CELL, ACT_CELL), 1)
            if act:
                lbl = bold_font.render(act['label'], True, (220, 220, 180))
                surface.blit(lbl, (bx + ACT_CELL // 2 - lbl.get_width() // 2,
                                   by + ACT_CELL // 2 - lbl.get_height() // 2))
            # Hotkey label (bottom-right corner, always shown)
            hk = _HOTKEY_LABEL.get((col, row), '')
            if hk:
                hk_surf = hud_font.render(hk, True, (90, 90, 110))
                surface.blit(hk_surf, (bx + ACT_CELL - hk_surf.get_width() - 3,
                                       by + ACT_CELL - hk_surf.get_height() - 2))

    # ── Info / queue panel (beige box) ────────────────────────────────── #
    grid_w = ACT_MARGIN + 5 * (ACT_CELL + ACT_PAD) - ACT_PAD + ACT_MARGIN
    info_x = grid_w
    info_y = panel_y + ACT_MARGIN
    info_w = 420
    info_h = BOT_HUD_H - 2 * ACT_MARGIN
    pygame.draw.rect(surface, (210, 190, 140), (info_x, info_y, info_w, info_h))
    pygame.draw.rect(surface, (140, 120,  80), (info_x, info_y, info_w, info_h), 2)

    if selected_bld:
        name_txt = bold_font.render(selected_bld.name, True, (40, 30, 10))
        surface.blit(name_txt, (info_x + 8, info_y + 6))
        _draw_team_badge(surface, selected_bld, player,
                         info_x + 8, info_y + 20, hud_font)

        # Queue item icons
        for i, item in enumerate(selected_bld.queue):
            qr = pygame.Rect(info_x + 8 + i * 38, info_y + 30, 34, 34)
            is_age = item.startswith('age_up:')
            bg_col = (30, 55, 90) if is_age else (80, 60, 30)
            pygame.draw.rect(surface, bg_col, qr)
            pygame.draw.rect(surface, (160, 130, 70), qr, 1)
            lbl_str = AGE_UP_DATA[item]['label'] if is_age else item[0].upper()
            ql = hud_font.render(lbl_str, True, (180, 210, 255) if is_age else (220, 200, 140))
            surface.blit(ql, (qr.x + 17 - ql.get_width() // 2,
                              qr.y + 17 - ql.get_height() // 2))

        # Training/research progress bar
        if selected_bld.queue:
            cur_item = selected_bld.queue[0]
            cur_total = AGE_UP_DATA[cur_item]['ticks'] if cur_item.startswith('age_up:') else TRAIN_TICKS
            prog = selected_bld.queue_ticks / cur_total
            bar = pygame.Rect(info_x + 8, info_y + info_h - 14, info_w - 16, 8)
            pygame.draw.rect(surface, (80, 65, 40), bar)
            pygame.draw.rect(surface, (180, 140, 60),
                             (bar.x, bar.y, int(bar.w * prog), bar.h))
            pygame.draw.rect(surface, (140, 110, 60), bar, 1)

    elif selected_unit:
        if sel_count > 1:
            header = f"{sel_count} {selected_unit.unit_type.capitalize()}s"
        else:
            header = selected_unit.unit_type.capitalize()
        name_txt = bold_font.render(header, True, (40, 30, 10))
        surface.blit(name_txt, (info_x + 8, info_y + 6))
        _draw_team_badge(surface, selected_unit, player,
                         info_x + 8, info_y + 20, hud_font)
        if sel_count == 1:
            # HP bar only meaningful for a single unit
            hp_w = min(info_w - 16, 160)
            hp_rect = pygame.Rect(info_x + 8, info_y + 38, hp_w, 10)
            pygame.draw.rect(surface, (80, 30, 30), hp_rect)
            fill = int(hp_w * selected_unit.hp / selected_unit.max_hp)
            pygame.draw.rect(surface, (60, 180, 60),
                             (hp_rect.x, hp_rect.y, fill, hp_rect.h))
            pygame.draw.rect(surface, (100, 80, 50), hp_rect, 1)
            hp_lbl = hud_font.render(
                f"{selected_unit.hp} / {selected_unit.max_hp}", True, (40, 30, 10))
            surface.blit(hp_lbl, (info_x + 8, info_y + 54))

    elif selected_res:
        name_txt = bold_font.render(selected_res.res_type.capitalize(),
                                    True, (40, 30, 10))
        surface.blit(name_txt, (info_x + 8, info_y + 6))
        amt_lbl = hud_font.render(f"Amount: {selected_res.amount}",
                                  True, (40, 30, 10))
        surface.blit(amt_lbl, (info_x + 8, info_y + 28))


def draw_rally_flags(surface, buildings):
    """Draw a flagpole at the rally point of every production building."""
    h = th()
    for b in buildings:
        if b.rally_x is None:
            continue
        sx, sy = world_to_screen(b.rally_x, b.rally_z)
        cy = sy + h // 2
        pole_h = max(10, int(16 * zoom))
        pole_w = max(1, int(2 * zoom))
        flag_w = max(6, int(9 * zoom))
        flag_h = max(4, int(7 * zoom))
        pygame.draw.line(surface, (200, 170, 90),
                         (sx, cy), (sx, cy - pole_h), pole_w)
        pygame.draw.rect(surface, (220, 40, 40),
                         (sx + pole_w, cy - pole_h, flag_w, flag_h))


def units_in_box(units, x1, y1, x2, y2):
    """Return all units whose screen position falls inside the drag rectangle."""
    left, right = min(x1, x2), max(x1, x2)
    top, bottom = min(y1, y2), max(y1, y2)
    h = th()
    result = []
    for unit in units:
        sx, sy = world_to_screen(unit.x, unit.z)
        sy += h // 2
        if left <= sx <= right and top <= sy <= bottom:
            result.append(unit)
    return result


# Spread pattern for group move destinations
_SPREAD = [(0,0),(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1),
           (2,0),(-2,0),(0,2),(0,-2),(2,1),(2,-1),(-2,1),(-2,-1)]

def _start_next_action(unit, game, player):
    """Pop and execute the next action from unit.action_queue, or resume role."""
    if not unit.action_queue:
        # Persist role: find the next target automatically
        if unit.role == 'shepherd':
            sheep = _find_nearest_sheep(game, unit)
            if sheep:
                slaughter_sheep(game, player, [unit], sheep)
                return
        elif unit.role in _ROLE_RES_TYPES:
            res = _find_nearest_resource(game, unit, _ROLE_RES_TYPES[unit.role])
            if res:
                gather_resource(game, [unit], res)
                return
        unit.state = 'idle'
        return
    action = unit.action_queue.pop(0)
    atype = action['type']
    if atype == 'move':
        tx, tz = action['dest']
        path = find_path(game, unit.x, unit.z, tx, tz)
        if path:
            unit.state = 'moving'
            unit.set_path(path)
        else:
            _start_next_action(unit, game, player)  # skip unreachable
    elif atype == 'gather':
        gather_resource(game, [unit], action['target'])
    elif atype == 'build':
        tgt = action['target']
        if tgt.name in _RESOURCE_BUILDINGS and unit.carried > 0:
            res_key = _DEPOSIT_AS.get(unit.carried_type, unit.carried_type)
            if res_key:
                player.resources[res_key] = player.resources.get(res_key, 0) + unit.carried
            unit.carried = 0
            unit.carried_type = None
        _assign_builder(unit, tgt, game)
    elif atype == 'slaughter':
        sheep = action['target']
        if sheep in game.units:
            slaughter_sheep(game, player, [unit], sheep)
        else:
            _start_next_action(unit, game, player)
    elif atype == 'hunt':
        animal = action['target']
        if animal in game.units:
            start_hunt(game, [unit], animal)
        else:
            _start_next_action(unit, game, player)


def update_movement(game, player):
    """Transition units from 'moving' to idle/next-action when path completes."""
    for unit in game.units:
        if unit.state == 'moving' and not unit.path:
            _start_next_action(unit, game, player)


def move_group(game, units, tx, tz):
    for i, unit in enumerate(units):
        unit.action_queue  = []   # new command clears any pending queue
        unit.gather_target = None
        unit.build_target  = None
        ox, oz = _SPREAD[i % len(_SPREAD)]
        path = find_path(game, unit.x, unit.z, tx + ox, tz + oz)
        if not path:
            path = find_path(game, unit.x, unit.z, tx, tz)
        if path:
            unit.state = 'moving'
            unit.set_path(path)
        else:
            unit.state = 'idle'


# ── Main ──────────────────────────────────────────────────────────────── #

def main():
    global offset_x, offset_y, zoom, _sprites, screen_w, screen_h

    pygame.init()
    info = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), FULLSCREEN)
    screen_w, screen_h = screen.get_size()
    pygame.display.set_caption("Age of Empires")
    clock     = pygame.time.Clock()
    font      = pygame.font.SysFont(None, 14)
    hud_font  = pygame.font.SysFont(None, 20)
    bold_font = pygame.font.SysFont(None, 22, bold=True)

    game = Game()
    game.add_player("Player 1", (0, 0, 255))
    game.start()
    game_start_ticks = pygame.time.get_ticks()
    player = game.players[0]
    game.generate_base(GRID_SIZE, team=player.team)

    # Spawn 3 villagers just outside the TC
    for i in range(3):
        game.add_unit('villager', -44 + i * 2, 52, team=player.team)

    # Spawn 1 scout cavalry at a random position 10-18 tiles from TC
    _scout_angle = random.uniform(0, 2 * math.pi)
    _scout_r     = random.uniform(10, 18)
    game.add_unit('scout_cavalry',
                  round(-52 + _scout_r * math.cos(_scout_angle)),
                  round( 52 + _scout_r * math.sin(_scout_angle)),
                  team=player.team)

    # Spawn 4 neutral sheep near the TC
    for i in range(4):
        angle = i * math.pi / 2 + math.pi / 4
        sx = round(-52 + 8 * math.cos(angle))
        sz = round( 52 + 8 * math.sin(angle))
        game.add_unit('sheep', sx, sz, team=None)

    # Spawn deer and boars scattered further out (neutral hunt)
    import random as _rnd2
    _rnd2.seed()
    for i in range(5):   # 5 deer
        angle = _rnd2.uniform(0, 2 * math.pi)
        r     = _rnd2.uniform(18, 35)
        game.add_unit('deer', round(-52 + r * math.cos(angle)),
                              round( 52 + r * math.sin(angle)), team=None)
    for i in range(3):   # 3 boars
        angle = _rnd2.uniform(0, 2 * math.pi)
        r     = _rnd2.uniform(22, 40)
        game.add_unit('boar', round(-52 + r * math.cos(angle)),
                              round( 52 + r * math.sin(angle)), team=None)

    # Center the view on the TC
    tc_cx, tc_cz = -52.0, 52.0
    w, h = tw(), th()
    offset_x = screen_w / 2 - (tc_cx - tc_cz) * w / 2
    offset_y = screen_h / 2 - (tc_cx + tc_cz) * h / 2
    _sprites = _make_sprites()

    # Drag-select state
    drag_start        = None
    drag_end          = None
    is_dragging       = False
    selected_building = None
    selected_unit     = None
    selected_resource = None
    action_submenu    = None   # active unit action submenu name, or None
    placement_mode    = None   # building name being placed, or None
    DRAG_THRESH       = 6

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                if placement_mode or action_submenu:
                    placement_mode = None
                    action_submenu = None
                else:
                    running = False
            if event.type == KEYDOWN and event.key in _HOTKEY_MAP:
                pos = _HOTKEY_MAP[event.key]
                cmd = _fire_action(pos, selected_building, selected_unit,
                                   action_submenu, player, game, placement_mode)
                if cmd:
                    if cmd[0] == 'set_submenu':
                        action_submenu = cmd[1]
                    elif cmd[0] == 'place':
                        placement_mode = cmd[1]
                    elif cmd[0] == 'back':
                        action_submenu = None
                    elif cmd[0] == 'cancel_place':
                        placement_mode = None
            if event.type == MOUSEWHEEL:
                set_zoom(zoom + event.y * 0.15)

            # ── Left button down: place building OR begin drag ───────── #
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if placement_mode and event.pos[1] < screen_h - BOT_HUD_H:
                    tx, tz = screen_to_tile(event.pos[0], event.pos[1])
                    cfg  = BUILDING_CONFIGS[placement_mode]
                    size = cfg['size']
                    if (all(game.is_tile_empty(tx + dx, tz + dz)
                            for dx in range(size) for dz in range(size))
                            and can_afford(game.players[0], placement_mode)):
                        builders = [u for u in game.units
                                    if u.selected and u.carry_cap > 0]
                        place_building(game, game.players[0],
                                       placement_mode, tx, tz, builders)
                        placement_mode = None
                        action_submenu = None
                elif not placement_mode and event.pos[1] < screen_h - BOT_HUD_H:
                    drag_start  = event.pos
                    drag_end    = event.pos
                    is_dragging = False

            # ── Mouse motion: extend drag rect ──────────────────────── #
            if event.type == MOUSEMOTION and drag_start:
                drag_end = event.pos
                if (abs(drag_end[0] - drag_start[0]) > DRAG_THRESH or
                        abs(drag_end[1] - drag_start[1]) > DRAG_THRESH):
                    is_dragging = True

            # ── Left button up: action buttons OR map selection ──────── #
            if event.type == MOUSEBUTTONUP and event.button == 1:
                if event.pos[1] >= screen_h - BOT_HUD_H:
                    # Click inside bottom HUD — fire action if any
                    if not is_dragging:
                        act = action_at_screen(event.pos[0], event.pos[1])
                        if act:
                            cmd = _fire_action(act, selected_building,
                                               selected_unit, action_submenu,
                                               player, game, placement_mode)
                            if cmd:
                                if cmd[0] == 'set_submenu':
                                    action_submenu = cmd[1]
                                elif cmd[0] == 'place':
                                    placement_mode = cmd[1]
                                elif cmd[0] == 'back':
                                    action_submenu = None
                                elif cmd[0] == 'cancel_place':
                                    placement_mode = None
                else:
                    # Click on map — handle selection
                    for u in game.units:
                        u.selected = False
                    if is_dragging and drag_start:
                        sel = [u for u in units_in_box(game.units,
                                           drag_start[0], drag_start[1],
                                           drag_end[0],   drag_end[1])
                               if u.team == player.team]
                        for u in sel:
                            u.selected = True
                        selected_building = None
                        selected_unit     = sel[0] if sel else None
                        selected_resource = None
                    else:
                        clicked = unit_at_screen(
                            game.units, event.pos[0], event.pos[1])
                        if clicked and clicked.team == player.team:
                            clicked.selected = True
                            selected_unit     = clicked
                            selected_building = None
                            selected_resource = None
                        else:
                            tx, tz = screen_to_tile(
                                event.pos[0], event.pos[1])
                            tile = game.get_tile(tx, tz)
                            if tile and tile['type'] == 'building':
                                selected_building = tile['obj']
                                selected_unit     = None
                                selected_resource = None
                            elif tile and tile['type'] == 'resource':
                                selected_resource = tile['obj']
                                selected_building = None
                                selected_unit     = None
                            else:
                                selected_building = None
                                selected_unit     = None
                                selected_resource = None
                drag_start  = None
                is_dragging = False

            # ── Right click: cancel placement, rally, gather, or move ── #
            if event.type == MOUSEBUTTONDOWN and event.button == 3:
                if placement_mode or action_submenu:
                    placement_mode = None
                    action_submenu = None
                elif event.pos[1] < screen_h - BOT_HUD_H:
                    tx, tz = screen_to_tile(event.pos[0], event.pos[1])
                    if selected_building and selected_building.rally_x is not None:
                        selected_building.rally_x = tx
                        selected_building.rally_z = tz
                    else:
                        sel = [u for u in game.units if u.selected and u.team == player.team]
                        shift = pygame.key.get_mods() & KMOD_SHIFT
                        if sel:
                            tile   = game.get_tile(tx, tz)
                            sheep  = _sheep_at_tile(game, tx, tz)
                            animal = _hunt_animal_at_tile(game, tx, tz)
                            vills  = [u for u in sel if u.unit_type == 'villager']
                            if shift:
                                # Shift+right-click: append to queue (no limit)
                                for unit in sel:
                                    if animal and unit.unit_type == 'villager':
                                        unit.action_queue.append(
                                            {'type': 'hunt', 'target': animal})
                                    elif sheep and unit.unit_type == 'villager':
                                        unit.action_queue.append(
                                            {'type': 'slaughter', 'target': sheep})
                                    elif tile and tile['type'] == 'resource':
                                        unit.action_queue.append(
                                            {'type': 'gather', 'target': tile['obj']})
                                    else:
                                        unit.action_queue.append(
                                            {'type': 'move', 'dest': (tx, tz)})
                                    # If idle, kick off immediately
                                    if unit.state == 'idle':
                                        _start_next_action(unit, game, player)
                            else:
                                # Normal right-click: replace current task
                                if animal and vills:
                                    start_hunt(game, vills, animal)
                                elif sheep and vills:
                                    slaughter_sheep(game, player, vills, sheep)
                                elif tile and tile['type'] == 'resource':
                                    gather_resource(game, sel, tile['obj'])
                                else:
                                    move_group(game, sel, tx, tz)

        keys = pygame.key.get_pressed()
        mx, my = pygame.mouse.get_pos()

        offset_x += (  CAM_SPEED * keys[K_LEFT]  + edge_speed(mx)
                      - CAM_SPEED * keys[K_RIGHT] - edge_speed(screen_w - 1 - mx))
        offset_y += (  CAM_SPEED * keys[K_UP]    + edge_speed(max(0, my - HUD_H))
                      - CAM_SPEED * keys[K_DOWN]  - edge_speed(screen_h - 1 - my))

        for _ in range(int(GAME_SPEED)):
            game.update_units()
            update_production(game, player)
            update_gathering(game, player)
            update_hunt(game, player)
            update_builders(game, player)
            update_construction(game, player)
            update_movement(game, player)
            update_sheep(game, player)
            cleanup_resources(game)

        elapsed_secs = int((pygame.time.get_ticks() - game_start_ticks) * GAME_SPEED // 1000)

        screen.fill((20, 20, 30))
        draw_plane(screen)
        draw_entities(screen, game.resources, game.buildings, font)
        draw_rally_flags(screen, game.buildings)
        draw_units(screen, game.units)

        # ── Draw drag-select box ─────────────────────────────────────── #
        if is_dragging and drag_start and drag_end:
            rx = min(drag_start[0], drag_end[0])
            ry = min(drag_start[1], drag_end[1])
            rw = abs(drag_end[0] - drag_start[0])
            rh = abs(drag_end[1] - drag_start[1])
            if rw > 0 and rh > 0:
                box = pygame.Surface((rw, rh), pygame.SRCALPHA)
                box.fill((100, 180, 255, 45))
                pygame.draw.rect(box, (100, 180, 255, 210), box.get_rect(), 2)
                screen.blit(box, (rx, ry))

        if placement_mode:
            draw_placement_ghost(screen, placement_mode, mx, my,
                                 game, game.players[0])
        draw_hud(screen, game.players[0], game.buildings, game.units,
                 elapsed_secs, hud_font, bold_font)
        sel_count = sum(1 for u in game.units if u.selected)
        draw_bot_hud(screen, selected_building, selected_unit, sel_count,
                     selected_resource, action_submenu, placement_mode,
                     game.players[0], game, hud_font, bold_font)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
