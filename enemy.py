# enemy.py - Enemy AI system with multiple enemy types and wave management

import pygame
import math
import random
from config import *
from skills import Particle, Projectile


class Enemy:
    """
    Base enemy class. Subclass for different enemy types.
    Enemies follow and attack the player using simple seek AI.
    """
    def __init__(self, x: float, y: float, enemy_type: str, wave: int = 1):
        stats = ENEMY_STATS[enemy_type]
        self.x, self.y = float(x), float(y)
        self.enemy_type = enemy_type

        # Scale stats with wave number
        wave_mult = 1 + (wave - 1) * 0.12
        self.max_hp    = stats["hp"] * wave_mult
        self.hp        = self.max_hp
        self.speed     = stats["speed"] * (1 + (wave - 1) * 0.04)
        self.damage    = stats["damage"] * wave_mult
        self.xp_value  = stats["xp"]
        self.base_color = stats["color"]
        self.size      = stats["size"]

        # Combat
        self.attack_range = self.size + 22
        self.attack_cd    = 0.8
        self.attack_timer = random.uniform(0, 0.8)  # stagger spawns

        # Knockback
        self.knock_vx = 0.0
        self.knock_vy = 0.0

        # State
        self.alive  = True
        self.target = None   # set to player

        # Visual
        self._hit_flash = 0.0
        self._particles: list[Particle] = []
        self._anim_frame = 0
        self._anim_timer = 0.0

    # ------------------------------------------------------------------ #
    #  Update                                                              #
    # ------------------------------------------------------------------ #
    def update(self, dt: float, player, game_map) -> bool:
        """Returns True if player was damaged this frame."""
        if not self.alive:
            return False

        self._anim_timer += dt
        if self._anim_timer > 0.18:
            self._anim_timer = 0
            self._anim_frame = (self._anim_frame + 1) % 4

        # Apply knockback decay
        self.knock_vx *= max(0, 1 - 8 * dt)
        self.knock_vy *= max(0, 1 - 8 * dt)
        kx = self.knock_vx * dt
        ky = self.knock_vy * dt

        # Move toward player
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        if dist > self.attack_range:
            if dist > 0:
                dx /= dist; dy /= dist
            move_spd = self.speed * dt
            self._move_with_collision(dx * move_spd + kx, dy * move_spd + ky, game_map)
        else:
            self._move_with_collision(kx, ky, game_map)

        # Attack player
        damaged = False
        self.attack_timer -= dt
        if self.attack_timer <= 0 and dist < self.attack_range + 5:
            self.attack_timer = self.attack_cd
            player.take_damage(self.damage)
            damaged = True

        # Update hit flash
        if self._hit_flash > 0:
            self._hit_flash -= dt

        # Update particles
        self._particles = [p for p in self._particles if p.alive]
        for p in self._particles:
            p.update(dt)

        return damaged

    def _move_with_collision(self, dx, dy, game_map):
        nx = self.x + dx
        if not game_map.is_solid_world(nx, self.y):
            self.x = nx
        ny = self.y + dy
        if not game_map.is_solid_world(self.x, ny):
            self.y = ny

    # ------------------------------------------------------------------ #
    #  Take damage                                                          #
    # ------------------------------------------------------------------ #
    def take_damage(self, amount: float, kbx=0.0, kby=0.0):
        self.hp -= amount
        self._hit_flash = 0.12
        self.knock_vx += kbx * 200
        self.knock_vy += kby * 200
        # Blood particles
        for _ in range(4):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(40, 140)
            self._particles.append(Particle(
                self.x, self.y,
                math.cos(angle) * spd, math.sin(angle) * spd,
                RED, lifetime=0.3, size=3
            ))
        if self.hp <= 0:
            self.alive = False
            self._on_death()

    def _on_death(self):
        # Spawn death particles
        for _ in range(10):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(60, 200)
            self._particles.append(Particle(
                self.x, self.y,
                math.cos(angle) * spd, math.sin(angle) * spd,
                self.base_color, lifetime=0.5, size=4
            ))

    def apply_knockback(self, from_x, from_y, force=180):
        dx = self.x - from_x
        dy = self.y - from_y
        dist = math.hypot(dx, dy) or 1
        self.knock_vx = dx / dist * force
        self.knock_vy = dy / dist * force

    # ------------------------------------------------------------------ #
    #  Drawing                                                              #
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface, camera):
        # Draw lingering death particles even after dead
        for p in self._particles:
            p.draw(surface, camera)

        if not self.alive:
            return

        sx, sy = camera.world_to_screen(self.x, self.y)
        sx, sy = int(sx), int(sy)

        color = WHITE if self._hit_flash > 0 else self.base_color

        self._draw_body(surface, sx, sy, color)

        # HP bar
        if self.hp < self.max_hp:
            bar_w = int(self.size * 2.2)
            bar_h = 4
            bx = sx - bar_w // 2
            by = sy - self.size - 7
            pygame.draw.rect(surface, DARK_RED, (bx, by, bar_w, bar_h))
            frac = max(0, self.hp / self.max_hp)
            pygame.draw.rect(surface, (240, 60, 60), (bx, by, int(bar_w * frac), bar_h))
            pygame.draw.rect(surface, WHITE, (bx, by, bar_w, bar_h), 1)

    def _draw_body(self, surface, sx, sy, color):
        """Override in subclasses for different looks."""
        pygame.draw.circle(surface, color, (sx, sy), self.size)
        # Eyes
        pygame.draw.circle(surface, RED, (sx - 4, sy - 4), 4)
        pygame.draw.circle(surface, RED, (sx + 4, sy - 4), 4)
        pygame.draw.circle(surface, BLACK, (sx - 4, sy - 4), 2)
        pygame.draw.circle(surface, BLACK, (sx + 4, sy - 4), 2)

    @property
    def rect(self):
        return pygame.Rect(self.x - self.size, self.y - self.size,
                           self.size * 2, self.size * 2)


# ─────────────────────────────────────────────────
#  Zombie  – slow, medium HP
# ─────────────────────────────────────────────────
class Zombie(Enemy):
    def __init__(self, x, y, wave=1):
        super().__init__(x, y, ENEMY_ZOMBIE, wave)

    def _draw_body(self, surface, sx, sy, color):
        # Rounded square zombie shape
        r = pygame.Rect(sx - self.size, sy - self.size,
                         self.size * 2, self.size * 2)
        pygame.draw.rect(surface, color, r, border_radius=6)
        # Zombie arms (wave animation)
        arm_y = sy + int(math.sin(self._anim_frame * math.pi / 2) * 3)
        pygame.draw.line(surface, color, (sx - self.size, sy),
                          (sx - self.size - 10, arm_y - 5), 4)
        pygame.draw.line(surface, color, (sx + self.size, sy),
                          (sx + self.size + 10, arm_y - 5), 4)
        # Eyes
        pygame.draw.circle(surface, (200, 50, 50), (sx - 5, sy - 4), 4)
        pygame.draw.circle(surface, (200, 50, 50), (sx + 5, sy - 4), 4)


# ─────────────────────────────────────────────────
#  Fast enemy  – fast, low HP
# ─────────────────────────────────────────────────
class FastEnemy(Enemy):
    def __init__(self, x, y, wave=1):
        super().__init__(x, y, ENEMY_FAST, wave)

    def _draw_body(self, surface, sx, sy, color):
        # Diamond shape
        points = [
            (sx, sy - self.size),
            (sx + self.size, sy),
            (sx, sy + self.size),
            (sx - self.size, sy),
        ]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, WHITE, points, 2)
        pygame.draw.circle(surface, BLACK, (sx, sy), 5)


# ─────────────────────────────────────────────────
#  Tank enemy  – slow, very high HP
# ─────────────────────────────────────────────────
class TankEnemy(Enemy):
    def __init__(self, x, y, wave=1):
        super().__init__(x, y, ENEMY_TANK, wave)
        self.attack_cd = 1.4   # slower attacks

    def _draw_body(self, surface, sx, sy, color):
        # Big hexagon
        points = []
        for i in range(6):
            a = math.radians(i * 60 - 30)
            points.append((sx + math.cos(a) * self.size,
                            sy + math.sin(a) * self.size))
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, WHITE, points, 3)
        # Armor lines
        pygame.draw.line(surface, WHITE, (sx - 8, sy), (sx + 8, sy), 2)
        pygame.draw.line(surface, WHITE, (sx, sy - 8), (sx, sy + 8), 2)


# ─────────────────────────────────────────────────
#  Shooter enemy  – keeps distance and fires
# ─────────────────────────────────────────────────
class ShooterEnemy(Enemy):
    def __init__(self, x, y, wave=1):
        super().__init__(x, y, ENEMY_SHOOTER, wave)
        self.attack_range = 220   # attacks from distance
        self.attack_cd = 1.8
        self.preferred_dist = 170
        self.projectiles: list[Projectile] = []

    def update(self, dt, player, game_map) -> bool:
        if not self.alive:
            return False

        self._anim_timer += dt
        if self._anim_timer > 0.2:
            self._anim_timer = 0
            self._anim_frame = (self._anim_frame + 1) % 4

        self.knock_vx *= max(0, 1 - 8 * dt)
        self.knock_vy *= max(0, 1 - 8 * dt)

        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        # Maintain preferred distance
        if dist < self.preferred_dist - 30:
            move_dir = -1   # back away
        elif dist > self.preferred_dist + 30:
            move_dir = 1    # approach
        else:
            move_dir = 0

        if move_dir and dist > 0:
            ndx, ndy = dx / dist, dy / dist
            self._move_with_collision(
                ndx * self.speed * dt * move_dir + self.knock_vx * dt,
                ndy * self.speed * dt * move_dir + self.knock_vy * dt,
                game_map
            )

        # Fire projectile
        damaged = False
        self.attack_timer -= dt
        if self.attack_timer <= 0 and dist < self.attack_range:
            self.attack_timer = self.attack_cd
            if dist > 0:
                ndx, ndy = dx / dist, dy / dist
                proj = Projectile(self.x, self.y, ndx, ndy, self.damage,
                                   speed=280, size=7, color=(255, 140, 50),
                                   lifetime=1.4, owner="enemy")
                self.projectiles.append(proj)

        # Update own projectiles
        alive_p = []
        for p in self.projectiles:
            p.update(dt, game_map)
            if p.alive:
                alive_p.append(p)
                # Check hit on player
                dist_to_player = math.hypot(p.x - player.x, p.y - player.y)
                if dist_to_player < player.size + p.size:
                    player.take_damage(p.damage)
                    p.lifetime = 0
                    damaged = True
        self.projectiles = alive_p

        if self._hit_flash > 0:
            self._hit_flash -= dt
        self._particles = [p for p in self._particles if p.alive]
        for p in self._particles:
            p.update(dt)

        return damaged

    def draw(self, surface, camera):
        # Draw shooter projectiles
        for p in self.projectiles:
            p.draw(surface, camera)
        super().draw(surface, camera)

    def _draw_body(self, surface, sx, sy, color):
        # Star shape for shooter
        points = []
        for i in range(8):
            a = math.radians(i * 45)
            r = self.size if i % 2 == 0 else self.size * 0.55
            points.append((sx + math.cos(a) * r, sy + math.sin(a) * r))
        pygame.draw.polygon(surface, color, points)
        pygame.draw.circle(surface, (255, 200, 100), (sx, sy), 7)


# ─────────────────────────────────────────────────
#  Enemy Factory
# ─────────────────────────────────────────────────
def create_enemy(enemy_type: str, x: float, y: float, wave: int) -> Enemy:
    constructors = {
        ENEMY_ZOMBIE:  Zombie,
        ENEMY_FAST:    FastEnemy,
        ENEMY_TANK:    TankEnemy,
        ENEMY_SHOOTER: ShooterEnemy,
    }
    cls = constructors.get(enemy_type, Zombie)
    return cls(x, y, wave)


# ─────────────────────────────────────────────────
#  Wave Manager
# ─────────────────────────────────────────────────
class WaveManager:
    """
    Controls enemy spawning per wave.
    Wave difficulty increases with each wave.
    """
    def __init__(self):
        self.wave = 1
        self.spawn_timer = 0.0
        self.enemies: list[Enemy] = []
        self.wave_kills = 0
        self.wave_kill_target = 0
        self._compute_wave_target()
        self._wave_active = True

    def _compute_wave_target(self):
        self.wave_kill_target = 8 + self.wave * 4

    def get_spawn_rate(self) -> float:
        return max(0.4, ENEMY_SPAWN_RATE - self.wave * 0.06)

    def get_enemy_pool(self) -> list[str]:
        """Return weighted list of enemy types for current wave."""
        pool = [ENEMY_ZOMBIE] * 5
        if self.wave >= 2:
            pool += [ENEMY_FAST] * 3
        if self.wave >= 3:
            pool += [ENEMY_TANK]
        if self.wave >= 4:
            pool += [ENEMY_SHOOTER] * 2
        if self.wave >= 6:
            pool += [ENEMY_TANK] * 2
            pool += [ENEMY_FAST] * 2
        return pool

    def update(self, dt: float, player, game_map) -> list[Enemy]:
        """Update enemies, spawn new ones, return list of dead enemies for XP."""
        dead_enemies = []

        # Update existing enemies
        alive = []
        for enemy in self.enemies:
            enemy.update(dt, player, game_map)
            if not enemy.alive and not enemy._particles:
                dead_enemies.append(enemy)
            else:
                alive.append(enemy)
        self.enemies = alive

        # Count kills
        newly_killed = [e for e in dead_enemies if not e.alive]
        self.wave_kills += len([e for e in newly_killed if e.hp <= 0])

        # Spawn
        if (self._wave_active and
                len(self.enemies) < MAX_ENEMIES_ON_MAP and
                self.wave_kills < self.wave_kill_target):
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_timer = self.get_spawn_rate()
                self._spawn_enemy(player, game_map)

        return dead_enemies

    def _spawn_enemy(self, player, game_map):
        # Spawn off-screen edges
        angle = random.uniform(0, math.pi * 2)
        dist = random.uniform(350, 500)
        sx = player.x + math.cos(angle) * dist
        sy = player.y + math.sin(angle) * dist
        # Clamp to world
        sx = max(TILE_SIZE * 2, min(WORLD_W - TILE_SIZE * 2, sx))
        sy = max(TILE_SIZE * 2, min(WORLD_H - TILE_SIZE * 2, sy))
        # Don't spawn in solid tiles
        if game_map.is_solid_world(sx, sy):
            return
        etype = random.choice(self.get_enemy_pool())
        self.enemies.append(create_enemy(etype, sx, sy, self.wave))

    def is_wave_complete(self) -> bool:
        return (self.wave_kills >= self.wave_kill_target and
                len(self.enemies) == 0)

    def start_next_wave(self):
        self.wave += 1
        self.wave_kills = 0
        self._compute_wave_target()
        self.spawn_timer = 1.0

    def draw(self, surface, camera):
        for enemy in self.enemies:
            enemy.draw(surface, camera)
