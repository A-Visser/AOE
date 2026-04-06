import math
import pygame
from pygame.locals import *
from OpenGL.GL import *
from game import Game

FPS = 60

GRID_SIZE = 200      # number of tiles per side
TILE_SIZE = 0.5

# Camera (fixed angle, pan + zoom)
CAM_ANGLE_X = 35     # fixed tilt
cam_distance = 30
cam_speed = 0.2

cam_x = 0.0          # pan position
cam_z = 0.0


def draw_plane():
    """Render a checkerboard green grid as the game board."""
    glBegin(GL_QUADS)
    half = GRID_SIZE // 2
    for x in range(-half, half):
        for z in range(-half, half):
            if (x + z) % 2 == 0:
                glColor3f(0.22, 0.62, 0.22)
            else:
                glColor3f(0.17, 0.50, 0.17)
            glVertex3f(x * TILE_SIZE,       0, z * TILE_SIZE)
            glVertex3f((x + 1) * TILE_SIZE, 0, z * TILE_SIZE)
            glVertex3f((x + 1) * TILE_SIZE, 0, (z + 1) * TILE_SIZE)
            glVertex3f(x * TILE_SIZE,       0, (z + 1) * TILE_SIZE)
    glEnd()


def create_resource_textures(resources):
    font = pygame.font.SysFont(None, 18)
    for tile in resources:
        surf = font.render(str(tile.amount), True, (255, 255, 255))
        data = pygame.image.tostring(surf, "RGBA", False)
        w, h = surf.get_size()
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        tile.tex_id = tex_id


def draw_resources(resources):
    # Colored quads
    for tile in resources:
        glColor3f(*tile.color)
        x = tile.tile_x * TILE_SIZE
        z = tile.tile_z * TILE_SIZE
        y = 0.02
        t = TILE_SIZE
        glBegin(GL_QUADS)
        glVertex3f(x,     y, z)
        glVertex3f(x + t, y, z)
        glVertex3f(x + t, y, z + t)
        glVertex3f(x,     y, z + t)
        glEnd()

    # Text labels
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1, 1, 1, 1)
    for tile in resources:
        if tile.tex_id is None:
            continue
        glBindTexture(GL_TEXTURE_2D, tile.tex_id)
        x = tile.tile_x * TILE_SIZE + TILE_SIZE * 0.1
        z = tile.tile_z * TILE_SIZE + TILE_SIZE * 0.1
        y = 0.03
        s = TILE_SIZE * 0.8
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(x,     y, z)
        glTexCoord2f(1, 0); glVertex3f(x + s, y, z)
        glTexCoord2f(1, 1); glVertex3f(x + s, y, z + s)
        glTexCoord2f(0, 1); glVertex3f(x,     y, z + s)
        glEnd()
    glDisable(GL_BLEND)
    glDisable(GL_TEXTURE_2D)


def create_building_textures(buildings):
    font = pygame.font.SysFont(None, 22)
    for b in buildings:
        if not b.label:
            continue
        surf = font.render(b.label, True, (255, 255, 255))
        data = pygame.image.tostring(surf, "RGBA", False)
        w, h = surf.get_size()
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        b.tex_id = tex_id


def draw_buildings(buildings):
    # Colored footprints
    for b in buildings:
        glColor3f(*b.color)
        x = b.tile_x * TILE_SIZE
        z = b.tile_z * TILE_SIZE
        w = b.width  * TILE_SIZE
        d = b.depth  * TILE_SIZE
        y = 0.02
        glBegin(GL_QUADS)
        glVertex3f(x,     y, z)
        glVertex3f(x + w, y, z)
        glVertex3f(x + w, y, z + d)
        glVertex3f(x,     y, z + d)
        glEnd()

    # Labels
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1, 1, 1, 1)
    for b in buildings:
        if not b.tex_id:
            continue
        glBindTexture(GL_TEXTURE_2D, b.tex_id)
        # Center label on the building footprint
        cx = (b.tile_x + b.width  / 2) * TILE_SIZE
        cz = (b.tile_z + b.depth / 2) * TILE_SIZE
        s  = min(b.width, b.depth) * TILE_SIZE * 0.6
        y  = 0.03
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(cx - s/2, y, cz - s/2)
        glTexCoord2f(1, 0); glVertex3f(cx + s/2, y, cz - s/2)
        glTexCoord2f(1, 1); glVertex3f(cx + s/2, y, cz + s/2)
        glTexCoord2f(0, 1); glVertex3f(cx - s/2, y, cz + s/2)
        glEnd()
    glDisable(GL_BLEND)
    glDisable(GL_TEXTURE_2D)


def setup_gl(width, height):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    near, far, fov = 0.1, 200.0, 45.0
    top = near * math.tan(math.radians(fov / 2))
    right = top * (width / height)
    glFrustum(-right, right, -top, top, near, far)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.47, 0.65, 0.85, 1.0)  # sky blue


def main():
    global cam_distance, cam_x, cam_z

    pygame.init()
    info = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), DOUBLEBUF | OPENGL | FULLSCREEN)
    width, height = screen.get_size()
    pygame.display.set_caption("Age of Empires")
    clock = pygame.time.Clock()

    setup_gl(width, height)
    EDGE_ZONE = 120  # pixel zone near edge where scrolling activates

    def edge_scroll_speed(dist_from_edge):
        """Returns scroll speed based on how close cursor is to edge (0 = no scroll)."""
        if dist_from_edge >= EDGE_ZONE:
            return 0.0
        t = 1.0 - (dist_from_edge / EDGE_ZONE)   # 0 at zone boundary, 1 at very edge
        return cam_speed * (0.2 + 4.8 * t * t)   # quadratic ramp: slow near zone, fast at edge

    game = Game()
    game.add_player("Player 1", (0, 0, 255))
    game.start()

    game.generate_base(GRID_SIZE)
    create_building_textures(game.buildings)
    create_resource_textures(game.resources)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                running = False
            if event.type == MOUSEWHEEL:
                cam_distance = max(5, min(50, cam_distance - event.y * 0.5))

        keys = pygame.key.get_pressed()
        mx, my = pygame.mouse.get_pos()
        cam_z -= cam_speed * keys[K_UP]   + edge_scroll_speed(my)
        cam_z += cam_speed * keys[K_DOWN]  + edge_scroll_speed(height - 1 - my)
        cam_x -= cam_speed * keys[K_LEFT]  + edge_scroll_speed(mx)
        cam_x += cam_speed * keys[K_RIGHT] + edge_scroll_speed(width - 1 - mx)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, -cam_distance)
        glRotatef(CAM_ANGLE_X, 1, 0, 0)
        glTranslatef(-cam_x, 0, -cam_z)

        draw_plane()
        draw_resources(game.resources)
        draw_buildings(game.buildings)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
