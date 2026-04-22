# skills.py - Skill/weapon system with projectiles, effects, and orbs

import pygame
import math
import random
from config import *


# ─────────────────────────────────────────────────
#  Particle  (visual effect only)
# ─────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime=0.4, size=4):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.lifetime = lifetime
        self.max_life = lifetime
        self.size = size

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 80 * dt   # gravity
        self.lifetime -= dt

    @property
    def alive(self):
        return self.lifetime > 0

    def draw(self, surface, camera):
        # Đảm bảo alpha không bao giờ là số âm hoặc vượt quá 1.0
        alpha = max(0.0, min(1.0, self.lifetime / self.max_life))
        
        sx, sy = camera.world_to_screen(self.x, self.y)
        s = max(1, int(self.size * alpha))
        
        # Tính toán màu sắc dựa trên alpha an toàn
        r = int(self.color[0] * alpha)
        g = int(self.color[1] * alpha)
        b = int(self.color[2] * alpha)
        
        pygame.draw.circle(surface, (r, g, b), (int(sx), int(sy)), s)


# ─────────────────────────────────────────────────
#  Projectile
# ─────────────────────────────────────────────────
class Projectile:
    """
    Generic projectile fired by player skills.
    Carries damage, speed, size, color, and optional special flags.
    """
    def __init__(self, x, y, dx, dy, damage, speed=BULLET_SPEED,
                 size=BULLET_SIZE, color=YELLOW, lifetime=BULLET_LIFETIME,
                 piercing=False, owner="player"):
        self.x, self.y = x, y
        length = math.hypot(dx, dy) or 1
        self.vx = dx / length * speed
        self.vy = dy / length * speed
        self.damage = damage
        self.size = size
        self.color = color
        self.lifetime = lifetime
        self.piercing = piercing
        self.owner = owner
        self.hit_enemies: set = set()

    @property
    def alive(self):
        return self.lifetime > 0

    @property
    def rect(self):
        return pygame.Rect(self.x - self.size, self.y - self.size,
                           self.size * 2, self.size * 2)

    def update(self, dt, game_map):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        # Kill if hits solid tile
        if game_map.is_solid_world(self.x, self.y):
            self.lifetime = 0

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        # Glow effect
        glow_surf = pygame.Surface((self.size * 6, self.size * 6), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 60),
                            (self.size * 3, self.size * 3), self.size * 3)
        surface.blit(glow_surf,
                     (int(sx) - self.size * 3, int(sy) - self.size * 3))
        pygame.draw.circle(surface, self.color,
                            (int(sx), int(sy)), self.size)
        pygame.draw.circle(surface, WHITE,
                            (int(sx), int(sy)), max(1, self.size // 2))


# ─────────────────────────────────────────────────
#  Laser Beam  (continuous hitscan)
# ─────────────────────────────────────────────────
class LaserBeam:
    def __init__(self, x, y, dx, dy, damage):
        self.x, self.y = x, y
        length = math.hypot(dx, dy) or 1
        self.dx = dx / length
        self.dy = dy / length
        self.damage = damage
        self.duration = 0.25
        self.age = 0.0

    @property
    def alive(self):
        return self.age < self.duration

    def update(self, dt, _game_map):
        self.age += dt

    def get_end(self, game_map, max_len=600):
        step = 8
        x, y = self.x, self.y
        for _ in range(max_len // step):
            x += self.dx * step
            y += self.dy * step
            if game_map.is_solid_world(x, y):
                break
        return x, y

    def draw(self, surface, camera, game_map):
        sx1, sy1 = camera.world_to_screen(self.x, self.y)
        ex, ey = self.get_end(game_map)
        sx2, sy2 = camera.world_to_screen(ex, ey)
        alpha = 1 - self.age / self.duration
        w = max(1, int(5 * alpha))
        pygame.draw.line(surface, CYAN, (int(sx1), int(sy1)),
                          (int(sx2), int(sy2)), w + 3)
        pygame.draw.line(surface, WHITE, (int(sx1), int(sy1)),
                          (int(sx2), int(sy2)), max(1, w - 1))


# ─────────────────────────────────────────────────
#  Area-of-Effect zone
# ─────────────────────────────────────────────────
class AOEZone:
    """Lingers on the ground and damages enemies inside it."""
    def __init__(self, x, y, radius, damage_per_sec, color, duration=2.0):
        self.x, self.y = x, y
        self.radius = radius
        self.dps = damage_per_sec
        self.color = color
        self.duration = duration
        self.age = 0.0

    @property
    def alive(self):
        return self.age < self.duration

    def update(self, dt, _game_map):
        self.age += dt

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        alpha = max(0, int(120 * (1 - self.age / self.duration)))
        aoe_surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(aoe_surf, (*self.color, alpha),
                            (self.radius, self.radius), self.radius)
        surface.blit(aoe_surf, (int(sx - self.radius), int(sy - self.radius)))
        pygame.draw.circle(surface, self.color,
                            (int(sx), int(sy)), int(self.radius), 2)


# ─────────────────────────────────────────────────
#  Orbital Orb  (passive)
# ─────────────────────────────────────────────────
class OrbShield:
    """Orbs orbit the player and deal damage on contact."""
    def __init__(self, count=3, damage=15, radius=60):
        self.count = count
        self.damage = damage
        self.radius = radius
        self.angle = 0.0
        self.cooldowns: list[float] = [0.0] * count
        self.orb_cd = 0.5   # seconds between hits per orb

    def update(self, dt, player_x, player_y):
        self.angle += dt * 120   # degrees per second
        for i in range(len(self.cooldowns)):
            if self.cooldowns[i] > 0:
                self.cooldowns[i] -= dt

    def get_orb_positions(self, player_x, player_y):
        positions = []
        for i in range(self.count):
            a = math.radians(self.angle + i * (360 / self.count))
            ox = player_x + math.cos(a) * self.radius
            oy = player_y + math.sin(a) * self.radius
            positions.append((ox, oy))
        return positions

    def check_hit(self, enemy, player_x, player_y):
        """Return damage if an orb hits the enemy, else 0."""
        positions = self.get_orb_positions(player_x, player_y)
        for i, (ox, oy) in enumerate(positions):
            if self.cooldowns[i] <= 0:
                dist = math.hypot(enemy.x - ox, enemy.y - oy)
                if dist < 20 + enemy.size:
                    self.cooldowns[i] = self.orb_cd
                    return self.damage
        return 0

    def draw(self, surface, camera, player_x, player_y):
        for ox, oy in self.get_orb_positions(player_x, player_y):
            sx, sy = camera.world_to_screen(ox, oy)
            pygame.draw.circle(surface, CYAN, (int(sx), int(sy)), 10)
            pygame.draw.circle(surface, WHITE, (int(sx), int(sy)), 5)


# ─────────────────────────────────────────────────
#  Base Skill class
# ─────────────────────────────────────────────────
class Skill:
    """
    Base class for all player skills.
    Subclass and override `fire()` to implement behavior.
    """
    def __init__(self, name: str, cooldown: float, damage: float,
                 description: str, color: tuple, icon: str = "?"):
        self.name = name
        self.cooldown = cooldown
        self.base_cooldown = cooldown
        self.damage = damage
        self.base_damage = damage
        self.description = description
        self.color = color
        self.icon = icon
        self.level = 1
        self.timer = 0.0            # time since last use
        self.passive = False        # passive skills always active

    @property
    def ready(self):
        return self.timer >= self.cooldown

    @property
    def cd_fraction(self):
        """0→1 fraction of cooldown elapsed."""
        return min(1.0, self.timer / self.cooldown)

    def update(self, dt, **kwargs):
        self.timer = min(self.timer + dt, self.cooldown)

    def fire(self, player_x, player_y, target_x, target_y) -> list:
        """Return list of Projectile / AOEZone / LaserBeam objects."""
        return []

    def upgrade(self):
        """Called when player picks this upgrade; override for custom behavior."""
        self.level += 1
        self.damage = self.base_damage * (1 + 0.3 * (self.level - 1))
        self.cooldown = max(0.08, self.base_cooldown * (0.85 ** (self.level - 1)))

    def get_upgrade_desc(self):
        return f"Lv {self.level + 1}: +30% DMG, -15% CD"


# ─────────────────────────────────────────────────
#  Pistol
# ─────────────────────────────────────────────────
class PistolSkill(Skill):
    def __init__(self):
        super().__init__("Pistol", CD_PISTOL, 25, "Fires a fast bullet toward cursor.",
                         YELLOW, "🔫")

    def fire(self, px, py, tx, ty):
        if not self.ready:
            return []
        self.timer = 0
        dx, dy = tx - px, ty - py
        return [Projectile(px, py, dx, dy, self.damage)]


# ─────────────────────────────────────────────────
#  Shotgun
# ─────────────────────────────────────────────────
class ShotgunSkill(Skill):
    def __init__(self):
        super().__init__("Shotgun", CD_SHOTGUN, 18,
                          "Fires 5 spread pellets, short range.",
                          ORANGE, "💥")
        self.pellets = 5
        self.spread = 22   # degrees

    def fire(self, px, py, tx, ty):
        if not self.ready:
            return []
        self.timer = 0
        base_angle = math.degrees(math.atan2(ty - py, tx - px))
        projs = []
        for i in range(self.pellets):
            offset = -self.spread / 2 + i * self.spread / (self.pellets - 1)
            a = math.radians(base_angle + offset)
            projs.append(Projectile(px, py, math.cos(a), math.sin(a),
                                     self.damage, speed=420, size=5,
                                     color=ORANGE, lifetime=0.55))
        return projs

    def upgrade(self):
        super().upgrade()
        if self.level % 2 == 0:
            self.pellets = min(9, self.pellets + 1)
        self.spread = min(40, self.spread + 3)


# ─────────────────────────────────────────────────
#  Rifle
# ─────────────────────────────────────────────────
class RifleSkill(Skill):
    def __init__(self):
        super().__init__("Rifle", CD_RIFLE, 15,
                          "Rapid fire, high accuracy, piercing.", CYAN, "🎯")

    def fire(self, px, py, tx, ty):
        if not self.ready:
            return []
        self.timer = 0
        dx, dy = tx - px, ty - py
        return [Projectile(px, py, dx, dy, self.damage, speed=650,
                            size=5, color=CYAN, piercing=True)]


# ─────────────────────────────────────────────────
#  Laser
# ─────────────────────────────────────────────────
class LaserSkill(Skill):
    def __init__(self):
        super().__init__("Laser", CD_LASER, 80,
                          "Fires a piercing laser beam.", CYAN, "⚡")

    def fire(self, px, py, tx, ty):
        if not self.ready:
            return []
        self.timer = 0
        dx, dy = tx - px, ty - py
        return [LaserBeam(px, py, dx, dy, self.damage)]


# ─────────────────────────────────────────────────
#  Fireball
# ─────────────────────────────────────────────────
class FireballSkill(Skill):
    def __init__(self):
        super().__init__("Fireball", CD_FIREBALL, 45,
                          "Slow fireball that explodes into an AoE.", RED, "🔥")
        self.aoe_radius = 70
        self.aoe_dps = 20

    def fire(self, px, py, tx, ty):
        if not self.ready:
            return []
        self.timer = 0
        dx, dy = tx - px, ty - py
        proj = Projectile(px, py, dx, dy, self.damage,
                           speed=260, size=10, color=(255, 100, 0), lifetime=1.6)
        proj._is_fireball = True
        proj._aoe_radius = self.aoe_radius
        proj._aoe_dps = self.aoe_dps
        return [proj]

    def upgrade(self):
        super().upgrade()
        self.aoe_radius = min(130, self.aoe_radius + 10)
        self.aoe_dps += 8


# ─────────────────────────────────────────────────
#  Ice Nova
# ─────────────────────────────────────────────────
class IceNovaSkill(Skill):
    def __init__(self):
        super().__init__("Ice Nova", CD_ICE_NOVA, 35,
                          "Radiates icy shards in all directions.", BLUE, "❄️")
        self.shard_count = 12

    def fire(self, px, py, tx, ty):
        if not self.ready:
            return []
        self.timer = 0
        projs = []
        for i in range(self.shard_count):
            a = math.radians(i * 360 / self.shard_count)
            projs.append(Projectile(px, py, math.cos(a), math.sin(a),
                                     self.damage, speed=350, size=7,
                                     color=(100, 180, 255), lifetime=0.9))
        return projs

    def upgrade(self):
        super().upgrade()
        self.shard_count = min(24, self.shard_count + 3)


# ─────────────────────────────────────────────────
#  Lightning
# ─────────────────────────────────────────────────
class LightningSkill(Skill):
    def __init__(self):
        super().__init__("Lightning", CD_LIGHTNING, 55,
                          "Chain lightning – hits nearest enemies.", YELLOW, "⚡")
        self.chain = 3

    def fire(self, px, py, tx, ty):
        if not self.ready:
            return []
        self.timer = 0
        # Lightning is handled specially in game loop (chain damage)
        # We return a marker projectile with flag
        dx, dy = tx - px, ty - py
        proj = Projectile(px, py, dx, dy, self.damage,
                           speed=800, size=8, color=YELLOW, lifetime=0.4)
        proj._is_lightning = True
        proj._chain = self.chain
        return [proj]

    def upgrade(self):
        super().upgrade()
        self.chain = min(8, self.chain + 1)


# ─────────────────────────────────────────────────
#  Bomb
# ─────────────────────────────────────────────────
class BombSkill(Skill):
    def __init__(self):
        super().__init__("Bomb", CD_BOMB, 70,
                          "Thrown bomb – big AoE explosion on impact.", ORANGE, "💣")
        self.radius = 90

    def fire(self, px, py, tx, ty):
        if not self.ready:
            return []
        self.timer = 0
        dx, dy = tx - px, ty - py
        proj = Projectile(px, py, dx, dy, self.damage,
                           speed=320, size=12, color=(200, 120, 20), lifetime=1.2)
        proj._is_bomb = True
        proj._bomb_radius = self.radius
        return [proj]

    def upgrade(self):
        super().upgrade()
        self.radius = min(160, self.radius + 15)


# ─────────────────────────────────────────────────
#  Dash skill (active, no projectile)
# ─────────────────────────────────────────────────
class DashSkill(Skill):
    def __init__(self):
        super().__init__("Dash", CD_DASH, 0,
                          "Blink forward in movement direction.", PURPLE, "💨")
        self.dash_dist = 150

    def fire(self, px, py, tx, ty):
        if not self.ready:
            return []
        self.timer = 0
        # Dash is handled directly in player; return a marker list
        marker = Projectile(px, py, 0, 0, 0, speed=0, size=0,
                             color=PURPLE, lifetime=0.01)
        marker._is_dash = True
        marker._dash_dist = self.dash_dist
        return [marker]


# ─────────────────────────────────────────────────
#  Orb Shield skill (passive)
# ─────────────────────────────────────────────────
class OrbSkill(Skill):
    def __init__(self):
        super().__init__("Orb Shield", CD_ORB, 20,
                          "Orbiting energy orbs deal contact damage.", CYAN, "🔮")
        self.passive = True
        self.orb_count = 3
        self.orb = OrbShield(self.orb_count, self.damage)

    def upgrade(self):
        super().upgrade()
        self.orb_count = min(8, self.orb_count + 1)
        self.orb = OrbShield(self.orb_count, self.damage, radius=60 + self.level * 5)

    def get_upgrade_desc(self):
        return f"Lv {self.level + 1}: +1 orb, +30% DMG"


# ─────────────────────────────────────────────────
#  Magnet skill (passive – item attraction)
# ─────────────────────────────────────────────────
class MagnetSkill(Skill):
    def __init__(self):
        super().__init__("Magnet", CD_MAGNET, 0,
                          "Auto-attracts items and XP in a large radius.", GOLD, "🧲")
        self.passive = True
        self.pull_radius = 150

    def upgrade(self):
        super().upgrade()
        self.pull_radius += 60

    def get_upgrade_desc(self):
        return f"Lv {self.level + 1}: +60 pull radius"


# ─────────────────────────────────────────────────
#  Skill registry  (all skills available in game)
# ─────────────────────────────────────────────────
ALL_SKILLS = {
    "pistol":    PistolSkill,
    "shotgun":   ShotgunSkill,
    "rifle":     RifleSkill,
    "laser":     LaserSkill,
    "fireball":  FireballSkill,
    "ice_nova":  IceNovaSkill,
    "lightning": LightningSkill,
    "bomb":      BombSkill,
    "dash":      DashSkill,
    "orb":       OrbSkill,
    "magnet":    MagnetSkill,
}
