import heapq
import math

# Cardinal (cost 1) + diagonal (cost √2)
_DIRS = [
    ( 0,  1, 1.0),
    ( 0, -1, 1.0),
    ( 1,  0, 1.0),
    (-1,  0, 1.0),
    ( 1,  1, 1.4142),
    ( 1, -1, 1.4142),
    (-1,  1, 1.4142),
    (-1, -1, 1.4142),
]


def is_passable(game, tx, tz):
    tile = game.tiles.get((tx, tz))
    if tile is None:
        return True
    if tile['type'] == 'building' and tile['obj'].name == 'Town Center':
        return True
    return False


def _has_los(game, ax, az, bx, bz):
    """Bresenham line-of-sight: True if every tile on the line is passable."""
    dx = abs(bx - ax)
    dz = abs(bz - az)
    sx = 1 if ax < bx else -1
    sz = 1 if az < bz else -1
    err = dx - dz
    x, z = ax, az
    while (x, z) != (bx, bz):
        if not is_passable(game, x, z):
            return False
        e2 = 2 * err
        if e2 > -dz:
            err -= dz
            x   += sx
        if e2 < dx:
            err += dx
            z   += sz
    return True


def _smooth(game, path):
    """Remove redundant waypoints: keep only those where line-of-sight breaks."""
    if len(path) <= 2:
        return path
    out = [path[0]]
    i = 0
    while i < len(path) - 1:
        # Jump as far ahead as LOS allows
        j = len(path) - 1
        while j > i + 1:
            if _has_los(game, path[i][0], path[i][1], path[j][0], path[j][1]):
                break
            j -= 1
        out.append(path[j])
        i = j
    return out


def find_path(game, sx, sz, ex, ez):
    """
    8-directional A* with post-smoothing.
    Returns a list of (tx, tz) waypoints (excludes start tile).
    """
    start = (round(sx), round(sz))
    end   = (round(ex), round(ez))
    if start == end:
        return []
    if not is_passable(game, end[0], end[1]):
        return []

    def h(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    open_heap = [(h(start, end), 0.0, start)]
    came_from = {}
    g_score   = {start: 0.0}

    while open_heap:
        _, g, cur = heapq.heappop(open_heap)

        if cur == end:
            path = []
            while cur in came_from:
                path.append(cur)
                cur = came_from[cur]
            path.reverse()
            return _smooth(game, [start] + path)[1:]  # strip start, return rest

        if g > g_score.get(cur, float('inf')):
            continue

        for dx, dz, cost in _DIRS:
            nb = (cur[0] + dx, cur[1] + dz)

            # Prevent diagonal corner-cutting through blocked tiles
            if dx != 0 and dz != 0:
                if not is_passable(game, cur[0] + dx, cur[1]):
                    continue
                if not is_passable(game, cur[0], cur[1] + dz):
                    continue

            if not is_passable(game, nb[0], nb[1]):
                continue

            new_g = g_score[cur] + cost
            if new_g < g_score.get(nb, float('inf')):
                came_from[nb] = cur
                g_score[nb]   = new_g
                heapq.heappush(open_heap, (new_g + h(nb, end), new_g, nb))

    return []   # no path found
