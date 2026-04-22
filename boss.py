# boss.py - Boss enemy with phases, special attacks, and AI

import pygame
import math
import random
from config import *
from skills import Particle, Projectile, AOEZone


class Boss:
    """
    Boss enemy with 3 phases.
    Phase changes trigger new attack patterns.
    """
    def __init__(self, x: float, y: float, wave: int):
        self.x, self.y = float(x), float(y)
        self.wave = wave

        # Scale with wave
        scale = 1 + (wave // BOSS_EVERY_N_WAVES - 1) * 0.3
        self.max_hp = BOSS_HP * scale
        self.hp = self.max_hp
        self.speed = BOSS_SPEED * (1 + (wave - 1) * 0.04)
        self.damage = BOSS_DAMAGE * scale
        self.size = BOSS_SIZE
        self.xp_value = BOSS_XP + wave * 30

        # Phase thresholds: 100%→66%, 66%→33%, 33%→0%
        self.phase = 1
        self._phase_thresholds = [0.66, 0.33, 0.0]

        # Attack timers
        self._melee_cd = 1.0
        self._melee_timer = 0.5
        self._special_cd = 3.5
        self._special_timer = 1.5
        self._dash_cd = 5.0
        self._dash_timer = 2.5
        self._summon_cd = 8.0
        self._summon_timer = 4.0

        # Dash state
        self._dashing = False
        self._dash_vx = 0.0
        self._dash_vy = 0.0
        self._dash_remain = 0.0

        # Knockback
        self.knock_vx = 0.0
        self.knock_vy = 0.0

        # Combat
        self.alive = True
        self.projectiles: list[Projectile] = []
        self.aoe_zones: list[AOEZone] = []
        self.particles: list[Particle] = []

        # Summoned minions (managed by game loop)
        self.pending_spawns: list[tuple] = []   # (type, x, y)

        # Visual
        self._hit_flash = 0.0
        self._anim_angle = 0.0
        self._phase_changed = False
        self._phase_flash = 0.0

        # Name & color per phase
        self._phase_colors = [
            (200, 50, 200),   # Phase 1: purple
            (220, 100, 30),   # Phase 2: orange
            (220, 30, 30),    # Phase 3: red
        ]

    # ------------------------------------------------------------------ #
    #  Properties                                                           #
    # ------------------------------------------------------------------ #
    @property
    def hp_frac(self):
        return max(0, self.hp / self.max_hp)

    @property
    def color(self):
        return self._phase_colors[self.phase - 1]

    @property
    def rect(self):
        return pygame.Rect(self.x - self.size, self.y - self.size,
                           self.size * 2, self.size * 2)

    # ------------------------------------------------------------------ #
    #  Update                                                              #
    # ------------------------------------------------------------------ #
    def update(self, dt: float, player, game_map) -> bool:
        if not self.alive:
            return False

        self._anim_angle += dt * 90

        self._check_phase()

        # Knockback decay
        self.knock_vx *= max(0, 1 - 6 * dt)
        self.knock_vy *= max(0, 1 - 6 * dt)

        # Movement
        if self._dashing:
            self._do_dash(dt, game_map)
        else:
            self._seek_player(dt, player, game_map)

        # Attacks
        self._melee_timer -= dt
        self._special_timer -= dt
        self._dash_timer -= dt
        self._summon_timer -= dt
        self._phase_flash -= dt
        self._hit_flash -= dt

        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        # Melee attack
        if self._melee_timer <= 0 and dist < self.size + player.size + 20:
            self._melee_timer = self._melee_cd
            player.take_damage(self.damage)

        # Special attack based on phase
        if self._special_timer <= 0:
            self._special_timer = max(1.5, self._special_cd - (self.phase - 1) * 0.8)
            self._do_special_attack(player)

        # Dash attack
        if not self._dashing and self._dash_timer <= 0 and self.phase >= 2:
            self._dash_timer = self._dash_cd
            self._start_dash(player)

        # Summon minions (phase 3)
        if self._summon_timer <= 0 and self.phase == 3:
            self._summon_timer = self._summon_cd
            self._summon_minions()

        # Update projectiles
        alive_p = []
        for p in self.projectiles:
            p.update(dt, game_map)
            if p.alive:
                alive_p.append(p)
                dist_p = math.hypot(p.x - player.x, p.y - player.y)
                if dist_p < player.size + p.size:
                    player.take_damage(p.damage)
                    p.lifetime = 0
        self.projectiles = alive_p

        alive_a = []
        for z in self.aoe_zones:
            z.update(dt, game_map)
            if z.alive:
                alive_a.append(z)
        self.aoe_zones = alive_a

        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update(dt)

        return False

    def _check_phase(self):
        new_phase = 1
        if self.hp_frac <= 0.33:
            new_phase = 3
        elif self.hp_frac <= 0.66:
            new_phase = 2
        if new_phase != self.phase:
            self.phase = new_phase
            self._on_phase_change()

    def _on_phase_change(self):
        self._phase_flash = 0.6
        # Speed boost
        self.speed *= 1.18
        self._special_cd *= 0.75
        # Big explosion particles
        for _ in range(25):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(100, 350)
            self.particles.append(Particle(
                self.x, self.y,
                math.cos(angle) * spd, math.sin(angle) * spd,
                self.color, lifetime=0.7, size=7
            ))

    def _seek_player(self, dt, player, game_map):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist > self.size + player.size and dist > 0:
            ndx, ndy = dx / dist, dy / dist
            spd = self.speed * dt
            nx = self.x + ndx * spd + self.knock_vx * dt
            ny = self.y + ndy * spd + self.knock_vy * dt
            if not game_map.is_solid_world(nx, self.y):
                self.x = nx
            if not game_map.is_solid_world(self.x, ny):
                self.y = ny

    def _start_dash(self, player):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 1
        self._dash_vx = dx / dist
        self._dash_vy = dy / dist
        self._dashing = True
        self._dash_remain = 0.35
        # Trail particles
        for _ in range(15):
            self.particles.append(Particle(
                self.x, self.y,
                random.uniform(-80, 80), random.uniform(-80, 80),
                self.color, lifetime=0.4, size=6
            ))

    def _do_dash(self, dt, game_map):
        dash_spd = self.speed * 3.5
        nx = self.x + self._dash_vx * dash_spd * dt
        ny = self.y + self._dash_vy * dash_spd * dt
        if not game_map.is_solid_world(nx, self.y):
            self.x = nx
        else:
            self._dashing = False
        if not game_map.is_solid_world(self.x, ny):
            self.y = ny
        else:
            self._dashing = False
        self._dash_remain -= dt
        if self._dash_remain <= 0:
            self._dashing = False
        # Dash trail
        if random.random() < 0.5:
            self.particles.append(Particle(
                self.x, self.y,
                random.uniform(-40, 40), random.uniform(-40, 40),
                self.color, lifetime=0.25, size=8
            ))

    def _do_special_attack(self, player):
        if self.phase == 1:
            self._attack_ring_shot(player)
        elif self.phase == 2:
            self._attack_ring_shot(player)
            self._attack_aoe(player)
        else:
            self._attack_ring_shot(player)
            self._attack_aoe(player)
            self._attack_spiral(player)

    def _attack_ring_shot(self, player):
        """Fire bullets in a ring pattern."""
        count = 8 + (self.phase - 1) * 4
        for i in range(count):
            a = math.radians(i * 360 / count + self._anim_angle * 0.5)
            proj = Projectile(
                self.x, self.y,
                math.cos(a), math.sin(a),
                self.damage * 0.7,
                speed=200, size=10, color=self.color, lifetime=2.0,
                owner="boss"
            )
            self.projectiles.append(proj)
        # Particles
        for _ in range(8):
            angle = random.uniform(0, math.pi * 2)
            self.particles.append(Particle(
                self.x, self.y,
                math.cos(angle) * 100, math.sin(angle) * 100,
                self.color, lifetime=0.35, size=5
            ))

    def _attack_aoe(self, player):
        """Drop AoE zone at player's position."""
        self.aoe_zones.append(AOEZone(
            player.x, player.y,
            radius=80, damage_per_sec=self.damage * 0.8,
            color=self.color, duration=2.5
        ))

    def _attack_spiral(self, player):
        """Spiral of bullets."""
        for i in range(20):
            a = math.radians(self._anim_angle + i * 18)
            r = 30 + i * 6
            ox = self.x + math.cos(a) * r * 0.1
            oy = self.y + math.sin(a) * r * 0.1
            proj = Projectile(
                ox, oy,
                math.cos(a), math.sin(a),
                self.damage * 0.5,
                speed=180, size=8, color=(255, 150, 0), lifetime=2.0,
                owner="boss"
            )
            self.projectiles.append(proj)

    def _summon_minions(self):
        """Queue minion spawns for game loop to handle."""
        for i in range(3):
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(60, 120)
            mx = self.x + math.cos(angle) * dist
            my = self.y + math.sin(angle) * dist
            self.pending_spawns.append((ENEMY_ZOMBIE, mx, my))

    # ------------------------------------------------------------------ #
    #  Damage                                                              #
    # ------------------------------------------------------------------ #
    def take_damage(self, amount: float, kbx=0.0, kby=0.0):
        self.hp -= amount * 0.85   # bosses take slightly reduced damage
        self._hit_flash = 0.1
        self.knock_vx += kbx * 60
        self.knock_vy += kby * 60
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self._on_death()

    def _on_death(self):
        for _ in range(30):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(80, 300)
            self.particles.append(Particle(
                self.x, self.y,
                math.cos(angle) * spd, math.sin(angle) * spd,
                self.color, lifetime=random.uniform(0.4, 1.0), size=random.randint(4, 10)
            ))

    def apply_knockback(self, from_x, from_y, force=40):
        dx = self.x - from_x
        dy = self.y - from_y
        dist = math.hypot(dx, dy) or 1
        self.knock_vx = dx / dist * force
        self.knock_vy = dy / dist * force

    # ------------------------------------------------------------------ #
    #  Drawing                                                              #
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface, camera):
        # Particles (draw behind boss)
        for p in self.particles:
            p.draw(surface, camera)

        # AoE zones
        for z in self.aoe_zones:
            z.draw(surface, camera)

        # Projectiles
        for p in self.projectiles:
            p.draw(surface, camera)

        if not self.alive:
            return

        sx, sy = camera.world_to_screen(self.x, self.y)
        sx, sy = int(sx), int(sy)

        color = WHITE if self._hit_flash > 0 else self.color
        if self._phase_flash > 0:
            r = int(255 * (self._phase_flash / 0.6))
            color = (min(255, color[0] + r),
                     min(255, color[1]),
                     min(255, color[2] + r // 2))

        # Pulsing glow ring
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003)) * 15
        glow_surf = pygame.Surface((self.size * 4, self.size * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 50),
                            (self.size * 2, self.size * 2),
                            int(self.size + pulse))
        surface.blit(glow_surf, (sx - self.size * 2, sy - self.size * 2))

        # Rotating outer ring
        for i in range(8):
            a = math.radians(self._anim_angle + i * 45)
            rx = sx + int(math.cos(a) * (self.size + 12))
            ry = sy + int(math.sin(a) * (self.size + 12))
            pygame.draw.circle(surface, self.color, (rx, ry), 5)

        # Main body
        pygame.draw.circle(surface, color, (sx, sy), self.size)

        # Inner core
        inner_r = int(self.size * 0.55)
        inner_color = tuple(min(255, c + 60) for c in self.color)
        pygame.draw.circle(surface, inner_color, (sx, sy), inner_r)

        # Phase number
        font = pygame.font.SysFont("Arial", 14, bold=True)
        phase_text = font.render(f"P{self.phase}", True, WHITE)
        surface.blit(phase_text, (sx - phase_text.get_width() // 2,
                                   sy - phase_text.get_height() // 2))

        # Boss HP bar (wide, at top of screen – drawn in UI)
        # Small bar above boss
        bar_w = 90
        bar_h = 8
        bx = sx - bar_w // 2
        by = sy - self.size - 14
        pygame.draw.rect(surface, DARK_RED, (bx, by, bar_w, bar_h))
        pygame.draw.rect(surface, RED, (bx, by, int(bar_w * self.hp_frac), bar_h))
        pygame.draw.rect(surface, WHITE, (bx, by, bar_w, bar_h), 1)

        # Boss name
        font_name = pygame.font.SysFont("Arial", 12)
        name = font_name.render(f"BOSS  Wave {self.wave}", True, self.color)
        surface.blit(name, (sx - name.get_width() // 2, by - 14))
