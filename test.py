import pygame
import math

# --- Configuration ---
RES = WIDTH, HEIGHT = 800, 400
FPS = 60
TILE_SIZE = 50
FOV = math.pi / 3
HALF_FOV = FOV / 2
NUM_RAYS = 120
STEP_ANGLE = FOV / NUM_RAYS
MAX_DEPTH = 800
SCALE = WIDTH // NUM_RAYS

# --- Map (1 = Wall, 2 = Enemy) ---
MAP = [
    [1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 2, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 1],
    [1, 0, 0, 0, 1, 2, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1],
]

class Player:
    def __init__(self):
        self.x, self.y = 150, 150
        self.angle = 0
        self.speed = 3

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]: self.angle -= 0.05
        if keys[pygame.K_RIGHT]: self.angle += 0.05
        
        dx = math.cos(self.angle) * self.speed
        dy = math.sin(self.angle) * self.speed
        
        if keys[pygame.K_w]:
            self.x += dx
            self.y += dy
        if keys[pygame.K_s]:
            self.x -= dx
            self.y -= dy

def raycasting(screen, player):
    start_angle = player.angle - HALF_FOV
    for ray in range(NUM_RAYS):
        for depth in range(1, MAX_DEPTH):
            target_x = player.x + depth * math.cos(start_angle)
            target_y = player.y + depth * math.sin(start_angle)
            
            col = int(target_x / TILE_SIZE)
            row = int(target_y / TILE_SIZE)
            
            if MAP[row][col] != 0:
                # Calculate 3D wall height
                # Use cosine to fix "fish-eye" effect
                depth *= math.cos(player.angle - start_angle)
                wall_height = 21000 / (depth + 0.0001)
                
                # Color logic
                color = (200, 200, 200) if MAP[row][col] == 1 else (255, 0, 0)
                
                # Draw the vertical slice
                pygame.draw.rect(screen, color, (
                    ray * SCALE, 
                    (HEIGHT // 2) - (wall_height // 2), 
                    SCALE, 
                    wall_height
                ))
                break
        start_angle += STEP_ANGLE

# --- Initialization ---
pygame.init()
screen = pygame.display.set_caption("Voxel Raycaster")
screen = pygame.display.set_mode(RES)
clock = pygame.time.Clock()
player = Player()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                print("Pew Pew! (Checking hit...)")
                # Simple hitscan: if ray in the middle hits an enemy (2)
                # You can expand this to remove the '2' from the MAP

    # Background (Floor and Ceiling)
    screen.fill((30, 30, 30)) # Ceiling
    pygame.draw.rect(screen, (70, 70, 70), (0, HEIGHT // 2, WIDTH, HEIGHT // 2)) # Floor

    player.update()
    raycasting(screen, player)
    
    # Crosshair
    pygame.draw.circle(screen, (0, 255, 0), (WIDTH // 2, HEIGHT // 2), 5, 1)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()