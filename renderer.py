import pygame

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60


class Renderer:
    def __init__(self, title="Age of Empires"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)

    def clear(self):
        self.screen.fill((34, 139, 34))  # green background (grass)

    def draw_hud(self, player):
        resources = player.resources
        text = f"Turn | Food: {resources['food']}  Wood: {resources['wood']}  Gold: {resources['gold']}  Stone: {resources['stone']}"
        surface = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(surface, (10, 10))

    def flip(self):
        pygame.display.flip()
        self.clock.tick(FPS)

    def quit(self):
        pygame.quit()
