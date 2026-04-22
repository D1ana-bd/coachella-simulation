import pygame

# init
pygame.init()

# config
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Teste Sprite")

# load imagem
img = pygame.image.load("stage.png").convert_alpha()

# escala (ajusta como quiseres)
img = pygame.transform.scale(img, (400, 250))

# loop
running = True
while running:
    screen.fill((255, 255, 255))  # fundo branco

    # desenhar no centro
    rect = img.get_rect(center=(WIDTH//2, HEIGHT//2))
    screen.blit(img, rect)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    pygame.display.flip()

pygame.quit()