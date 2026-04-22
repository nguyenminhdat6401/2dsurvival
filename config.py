# config.py - Global configuration constants

# Screen
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Survival 2D - Wave Survival"

# Colors
BLACK       = (0, 0, 0)
WHITE       = (255, 255, 255)
RED         = (220, 50, 50)
GREEN       = (50, 200, 80)
BLUE        = (50, 100, 220)
YELLOW      = (255, 220, 0)
ORANGE      = (255, 140, 0)
PURPLE      = (160, 32, 240)
CYAN        = (0, 220, 220)
DARK_GREEN  = (20, 80, 30)
DARK_GRAY   = (40, 40, 40)
LIGHT_GRAY  = (180, 180, 180)
DARK_RED    = (140, 20, 20)
GOLD        = (255, 200, 0)
PINK        = (255, 100, 150)

# UI Colors
UI_BG       = (15, 15, 25)
UI_PANEL    = (25, 25, 40)
UI_BORDER   = (60, 60, 100)
UI_ACCENT   = (80, 200, 255)
UI_TEXT     = (220, 220, 240)

# Map / World
TILE_SIZE   = 48
MAP_COLS    = 60
MAP_ROWS    = 60
WORLD_W     = MAP_COLS * TILE_SIZE
WORLD_H     = MAP_ROWS * TILE_SIZE

# Tile types
TILE_GRASS      = 0
TILE_WALL       = 1
TILE_TREE       = 2
TILE_ROCK       = 3
TILE_WATER      = 4
TILE_DARK_GRASS = 5
TILE_SAND       = 6

# Player
PLAYER_HP           = 100
PLAYER_SPEED        = 180
PLAYER_DAMAGE       = 20
PLAYER_ATTACK_RANGE = 55
PLAYER_ATTACK_CD    = 0.45
PLAYER_SIZE         = 20
PLAYER_HP_REGEN     = 0.0   # per second (upgradeable)

# Enemy types
ENEMY_ZOMBIE  = "zombie"
ENEMY_FAST    = "fast"
ENEMY_TANK    = "tank"
ENEMY_SHOOTER = "shooter"

ENEMY_STATS = {
    ENEMY_ZOMBIE:  {"hp": 60,  "speed": 70,  "damage": 8,  "xp": 10, "color": (100, 200, 100), "size": 18},
    ENEMY_FAST:    {"hp": 30,  "speed": 160, "damage": 5,  "xp": 8,  "color": (200, 200, 80),  "size": 14},
    ENEMY_TANK:    {"hp": 200, "speed": 45,  "damage": 18, "xp": 25, "color": (80, 80, 220),   "size": 26},
    ENEMY_SHOOTER: {"hp": 50,  "speed": 80,  "damage": 6,  "xp": 15, "color": (220, 120, 50),  "size": 16},
}

# Boss
BOSS_HP     = 1200
BOSS_SPEED  = 90
BOSS_DAMAGE = 25
BOSS_SIZE   = 42
BOSS_XP     = 300

# Waves
WAVE_DURATION       = 35     # seconds per wave (countdown timer)
BOSS_EVERY_N_WAVES  = 4      # boss appears every N waves
ENEMY_SPAWN_RATE    = 1.4    # seconds between spawns (decreases per wave)
MAX_ENEMIES_ON_MAP  = 60

# XP / Level
XP_PER_LEVEL        = 100    # XP needed for next level (scales)
XP_SCALE_FACTOR     = 1.35   # multiplier each level

# Projectile
BULLET_SPEED        = 520
BULLET_SIZE         = 6
BULLET_LIFETIME     = 1.8

# Skill cooldowns (seconds)
CD_PISTOL       = 0.30
CD_SHOTGUN      = 0.65
CD_RIFLE        = 0.18
CD_LASER        = 2.5
CD_FIREBALL     = 1.0
CD_ICE_NOVA     = 3.5
CD_LIGHTNING    = 2.0
CD_BOMB         = 4.0
CD_ORB          = 0.0   # passive
CD_DASH         = 1.5
CD_MAGNET       = 0.0   # passive

# Item drop chances
DROP_CHANCE_HP      = 0.12
DROP_CHANCE_DAMAGE  = 0.06
DROP_CHANCE_SPEED   = 0.05

# Camera shake
SHAKE_DURATION  = 0.4
SHAKE_INTENSITY = 8

# High score file
HIGHSCORE_FILE = "highscore.txt"
