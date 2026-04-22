# player.py - Đã sửa lỗi XP và thêm shadow/hit effect
import pygame
import math
import random
from config import *
from skills import (Skill, Projectile, AOEZone, LaserBeam, OrbSkill, MagnetSkill, DashSkill, Particle, ALL_SKILLS)

class Player:
    def __init__(self, x: float, y: float):
        self.x, self.y = float(x), float(y)
        self.max_hp = PLAYER_HP
        self.hp = float(self.max_hp)
        self.speed = float(PLAYER_SPEED)
        self.damage = float(PLAYER_DAMAGE)
        self.hp_regen = PLAYER_HP_REGEN

        # LƯU TRỮ XP CHUẨN (Sửa lỗi quan trọng)
        self.level = 1
        self.xp = 0
        self.xp_to_next = XP_PER_LEVEL
        self.pending_level_ups = 0  # Hàng đợi level up

        self.size = PLAYER_SIZE
        self.skills: dict[str, Skill] = {}
        self._add_skill("pistol")
        self.active_skill_key = "pistol"
        self.auto_fire = True

        self.projectiles: list = []
        self.aoe_zones: list = []
        self.laser_beams: list = []
        self.particles: list[Particle] = []

        self.iframes = 0.0
        self.iframes_max = 0.5
        self._anim_timer = 0.0
        self._anim_frame = 0
        self._facing_right = True
        self._state = "idle"
        self._attack_flash = 0.0
        
        self._dashing = False
        self._dash_timer = 0.0
        self._dash_dx = 0.0
        self._dash_dy = 0.0
        self._dash_speed = 600
        self.alive = True

    def _add_skill(self, key: str):
        if key in ALL_SKILLS and key not in self.skills:
            self.skills[key] = ALL_SKILLS[key]()

    def has_skill(self, key: str) -> bool: return key in self.skills
    def upgrade_skill(self, key: str):
        if key in self.skills: self.skills[key].upgrade()
        else: self._add_skill(key)
    def get_orb_skill(self) -> OrbSkill | None: return self.skills.get("orb")
    def get_magnet_radius(self) -> float:
        mag = self.skills.get("magnet")
        return mag.pull_radius if mag else 80

    def update(self, dt: float, game_map, enemies: list, mouse_world: tuple):
        if not self.alive: return
        self._handle_movement(dt, game_map)
        self._handle_firing(dt, mouse_world, enemies)
        self._update_projectiles(dt, game_map)
        self._update_particles(dt)
        self._regen_hp(dt)

        if self.iframes > 0: self.iframes -= dt
        for skill in self.skills.values():
            if skill.passive: skill.update(dt)

        self._anim_timer += dt
        if self._anim_timer > 0.15:
            self._anim_timer = 0
            self._anim_frame = (self._anim_frame + 1) % 4
        if self._attack_flash > 0: self._attack_flash -= dt

    def _regen_hp(self, dt):
        if self.hp_regen > 0: self.hp = min(self.max_hp, self.hp + self.hp_regen * dt)

    def _handle_movement(self, dt, game_map):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if self._dashing:
            self._perform_dash(dt, game_map)
            return

        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1; self._facing_right = False
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1; self._facing_right = True

        if dx or dy:
            length = math.hypot(dx, dy)
            dx /= length; dy /= length
            self._state = "run"
        else:
            self._state = "idle"

        spd = self.speed * dt
        self._move_with_collision(dx * spd, dy * spd, game_map)

    def _move_with_collision(self, dx, dy, game_map):
        nx = self.x + dx
        if not self._collides_solid(nx, self.y, game_map): self.x = nx
        ny = self.y + dy
        if not self._collides_solid(self.x, ny, game_map): self.y = ny

    def _collides_solid(self, x, y, game_map) -> bool:
        for rect in game_map.get_solid_rects_near(x, y, radius=2):
            if rect.collidepoint(x, y): return True
        return False

    def _perform_dash(self, dt, game_map):
        dist = self._dash_speed * dt
        nx = self.x + self._dash_dx * dist
        ny = self.y + self._dash_dy * dist
        if not self._collides_solid(nx, ny, game_map):
            self.x, self.y = nx, ny
        self._dash_timer -= dt
        if self._dash_timer <= 0: self._dashing = False

    def _handle_firing(self, dt, mouse_world, enemies):
        mx, my = mouse_world
        for skill in self.skills.values(): skill.update(dt)
        if self.auto_fire:
            for key, skill in self.skills.items():
                if skill.passive: continue
                if skill.ready:
                    results = skill.fire(self.x, self.y, mx, my)
                    self._process_fire_results(results, mouse_world)

    def _process_fire_results(self, results: list, mouse_world):
        mx, my = mouse_world
        for obj in results:
            if isinstance(obj, LaserBeam):
                self.laser_beams.append(obj)
                self._attack_flash = 0.1
            elif isinstance(obj, Projectile):
                if hasattr(obj, '_is_dash') and obj._is_dash:
                    self._start_dash(mx, my, obj._dash_dist)
                else:
                    self.projectiles.append(obj)
                    self._attack_flash = 0.1
                    self._spawn_muzzle_flash()
            elif isinstance(obj, AOEZone):
                self.aoe_zones.append(obj)

    def _start_dash(self, tx, ty, dist):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if not (dx or dy): dx, dy = tx - self.x, ty - self.y
        length = math.hypot(dx, dy) or 1
        self._dash_dx, self._dash_dy = dx / length, dy / length
        self._dashing, self._dash_timer = True, dist / self._dash_speed
        for _ in range(8):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(40, 120)
            self.particles.append(Particle(self.x, self.y, math.cos(angle) * spd, math.sin(angle) * spd, PURPLE, lifetime=0.3, size=5))

    def _spawn_muzzle_flash(self):
        for _ in range(4):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(60, 180)
            self.particles.append(Particle(self.x, self.y, math.cos(angle) * spd, math.sin(angle) * spd, YELLOW, lifetime=0.2, size=3))

    def _update_projectiles(self, dt, game_map):
        alive = []
        for p in self.projectiles:
            p.update(dt, game_map)
            if p.alive: alive.append(p)
            else:
                if hasattr(p, '_is_fireball'):
                    self.aoe_zones.append(AOEZone(p.x, p.y, p._aoe_radius, p._aoe_dps, (255, 80, 0), duration=1.5))
                    self._spawn_explosion(p.x, p.y, RED, 14)
                elif hasattr(p, '_is_bomb'):
                    self.aoe_zones.append(AOEZone(p.x, p.y, p._bomb_radius, p.damage * 3, ORANGE, duration=0.6))
                    self._spawn_explosion(p.x, p.y, ORANGE, 20)
        self.projectiles = alive

        self.aoe_zones = [z for z in self.aoe_zones if (z.update(dt, game_map) or z.alive)]
        self.laser_beams = [lb for lb in self.laser_beams if (lb.update(dt, game_map) or lb.alive)]

    def _update_particles(self, dt):
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles: p.update(dt)

    def _spawn_explosion(self, x, y, color, count):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(80, 260)
            self.particles.append(Particle(x, y, math.cos(angle) * spd, math.sin(angle) * spd, color, lifetime=random.uniform(0.3, 0.7), size=random.randint(3, 7)))

    def take_damage(self, amount: float, knockback_dx=0, knockback_dy=0):
        if self.iframes > 0: return
        self.hp -= amount
        self.iframes = self.iframes_max
        for _ in range(5):
            angle = random.uniform(0, math.pi * 2)
            self.particles.append(Particle(self.x, self.y, math.cos(angle) * 120, math.sin(angle) * 120, RED, lifetime=0.3, size=4))
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    # FIX LOGIC XP: Dùng vòng lặp while để xử lý cộng dồn XP, không bao giờ mất XP dư
    def gain_xp(self, amount: int):
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(XP_PER_LEVEL * (XP_SCALE_FACTOR ** (self.level - 1)))
            self.pending_level_ups += 1 # Đẩy vào hàng đợi level up

    def draw(self, surface: pygame.Surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        sx, sy = int(sx), int(sy)

        visible = True
        if self.iframes > 0 and int(self.iframes * 15) % 2 == 0: visible = False

        for p in self.particles: p.draw(surface, camera)
        orb_skill = self.get_orb_skill()
        if orb_skill: orb_skill.orb.draw(surface, camera, self.x, self.y)
        for lb in self.laser_beams: lb.draw(surface, camera, None)
        for z in self.aoe_zones: z.draw(surface, camera)
        for p in self.projectiles: p.draw(surface, camera)

        if not visible: return

        # MỚI: Bóng râm hiện đại
        pygame.draw.ellipse(surface, (0, 0, 0, 100), (sx - self.size, sy + self.size - 6, self.size * 2, 12))

        # Hiệu ứng hit flash
        color = (80, 180, 80)
        if self._attack_flash > 0 or self.iframes > 0.3:
            color = WHITE
            
        pygame.draw.circle(surface, color, (sx, sy), self.size)
        pygame.draw.circle(surface, (50, 130, 200), (sx, sy), self.size - 4)

        eye_dx = 1 if self._facing_right else -1
        pygame.draw.circle(surface, WHITE, (sx + eye_dx * 6, sy - 3), 5)
        pygame.draw.circle(surface, BLACK, (sx + eye_dx * 7, sy - 3), 3)

        if self._state == "run":
            leg_offset = math.sin(self._anim_frame * math.pi / 2) * 6
            pygame.draw.line(surface, (60, 60, 200), (sx - 5, sy + self.size - 2), (sx - 5, sy + self.size + 6 + int(leg_offset)), 3)
            pygame.draw.line(surface, (60, 60, 200), (sx + 5, sy + self.size - 2), (sx + 5, sy + self.size + 6 - int(leg_offset)), 3)

        # Thanh HP bo góc
        bar_w, bar_h = 40, 6
        bx, by = sx - bar_w // 2, sy - self.size - 12
        pygame.draw.rect(surface, DARK_RED, (bx, by, bar_w, bar_h), border_radius=3)
        hp_frac = max(0, self.hp / self.max_hp)
        pygame.draw.rect(surface, GREEN, (bx, by, int(bar_w * hp_frac), bar_h), border_radius=3)
        pygame.draw.rect(surface, WHITE, (bx, by, bar_w, bar_h), 1, border_radius=3)

    @property
    def rect(self):
        return pygame.Rect(self.x - self.size, self.y - self.size, self.size * 2, self.size * 2)