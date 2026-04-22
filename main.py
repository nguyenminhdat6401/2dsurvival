# main.py - Main game loop and system orchestration

import pygame
import sys
import math
import random
from config import *
from map import GameMap
from player import Player
from enemy import WaveManager, create_enemy
from boss import Boss
from ui import Camera, HUD, StartMenu, GameOverScreen, PauseMenu  # THÊM PauseMenu
from upgrade_system import UpgradeMenu, generate_upgrades
from items import DroppedItem, maybe_drop_items
from skills import AOEZone, LaserBeam, Projectile


# ─────────────────────────────────────────────────
#  High Score persistence
# ─────────────────────────────────────────────────
def load_highscore() -> int:
    try:
        with open(HIGHSCORE_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_highscore(score: int):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(score))
    except Exception:
        pass


# ─────────────────────────────────────────────────
#  Game class
# ─────────────────────────────────────────────────
class Game:
    STATE_MENU     = "menu"
    STATE_PLAYING  = "playing"
    STATE_UPGRADE  = "upgrade"
    STATE_GAME_OVER = "game_over"
    STATE_PAUSED   = "paused" 

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock  = pygame.time.Clock()

        self.high_score = load_highscore()
        self.state = self.STATE_MENU

        self.hud          = HUD()
        self.upgrade_menu = UpgradeMenu()
        self.start_menu   = StartMenu()
        self.gameover_scr = GameOverScreen()
        self.pause_menu   = PauseMenu() # KHỞI TẠO PAUSE MENU

    def new_game(self):
        self.game_map  = GameMap()
        self.player    = Player(WORLD_W // 2, WORLD_H // 2)
        self.camera    = Camera()
        self.wave_mgr  = WaveManager()
        self.boss      = None
        self.items     = []
        self.total_kills, self.elapsed_time, self.score = 0, 0.0, 0
        self._wave_banner_alpha = 255
        self._wave_complete_timer = 0.0
        self._between_waves = False

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if self._handle_event(event) == "quit": running = False

            self._update(dt)
            self._draw()
            pygame.display.flip()
        pygame.quit()
        sys.exit()

    def _handle_event(self, event):
        if self.state == self.STATE_MENU:
            if self.start_menu.handle_event(event) == "play":
                self.new_game()
                self.state = self.STATE_PLAYING

        elif self.state == self.STATE_PLAYING:
            # BẤM ESC ĐỂ PAUSE
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = self.STATE_PAUSED

        elif self.state == self.STATE_PAUSED:
            action = self.pause_menu.handle_event(event)
            if action == "resume": self.state = self.STATE_PLAYING
            elif action == "restart":
                self.new_game()
                self.state = self.STATE_PLAYING
            elif action == "quit": self.state = self.STATE_MENU

        elif self.state == self.STATE_UPGRADE:
            idx = self.upgrade_menu.handle_event(event)
            if idx >= 0:
                upg = self.upgrade_menu.upgrades[idx]
                upg.apply(self.player)
                
                # Check nếu còn dư lượt upgrade do ăn quá nhiều XP
                if self.player.pending_level_ups > 0:
                    self.player.pending_level_ups -= 1
                    self.upgrade_menu.show(generate_upgrades(self.player, 3))
                    self.hud.trigger_level_up() # Flash màn hình
                else:
                    self.upgrade_menu.active = False
                    self.state = self.STATE_PLAYING
                    if self._between_waves: self._start_next_wave()
                    self._between_waves = False

        elif self.state == self.STATE_GAME_OVER:
            action = self.gameover_scr.handle_event(event)
            if action == "retry":
                self.new_game()
                self.state = self.STATE_PLAYING
            elif action == "menu": self.state = self.STATE_MENU
        return None

    def _update(self, dt: float):
        if self.state == self.STATE_MENU: self.start_menu.update(dt)
        elif self.state == self.STATE_PLAYING: self._update_gameplay(dt)
        elif self.state == self.STATE_PAUSED: pass # Không update logic game khi đang Pause
        elif self.state == self.STATE_UPGRADE: self.upgrade_menu.update(dt)
        elif self.state == self.STATE_GAME_OVER: self.gameover_scr.update(dt)

    def _update_gameplay(self, dt: float):
        self.elapsed_time += dt
        mouse_world = self.camera.screen_to_world(*pygame.mouse.get_pos())
        self.camera.follow(self.player.x, self.player.y, dt)
        self.camera.update(dt)

        self.player.update(dt, self.game_map, self.wave_mgr.enemies, mouse_world)
        if not self.player.alive:
            self._trigger_game_over()
            return

        if self._wave_banner_alpha > 0: self._wave_banner_alpha -= dt * 280

        if self._wave_complete_timer > 0:
            self._wave_complete_timer -= dt
            if self._wave_complete_timer <= 0: self._trigger_upgrade(between_waves=True)
            return

        # XP Logic đã được sửa trong Player -> Main chỉ cần lấy số lượng killed enemies
        dead_enemies = self.wave_mgr.update(dt, self.player, self.game_map)
        for enemy in dead_enemies:
            if not enemy.alive:
                self.total_kills += 1
                self.score += enemy.xp_value * 10
                self.player.gain_xp(enemy.xp_value) # Cộng XP
                for item in maybe_drop_items(enemy.x, enemy.y): self.items.append(item)

        if self.boss:
            for (etype, bx, by) in self.boss.pending_spawns:
                self.wave_mgr.enemies.append(create_enemy(etype, bx, by, self.wave_mgr.wave))
            self.boss.pending_spawns.clear()

        if self.wave_mgr.is_wave_complete() and not self.boss:
            if self.wave_mgr.wave % BOSS_EVERY_N_WAVES == 0: self._spawn_boss()
            else: self._wave_complete_timer = 1.2

        if self.boss:
            self.boss.update(dt, self.player, self.game_map)
            if not self.boss.alive and not self.boss.particles:
                self.player.gain_xp(self.boss.xp_value)
                for item in maybe_drop_items(self.boss.x, self.boss.y, is_boss=True): self.items.append(item)
                self.total_kills += 1; self.score += self.boss.xp_value * 15
                self.boss, self._wave_complete_timer = None, 1.5

        self._check_player_projectile_hits()
        self._check_aoe_hits(dt)
        self._check_orb_hits()

        for item in self.items: item.update(dt, self.player)
        self.items = [i for i in self.items if i.alive]

        # CORE FIX: Check Hàng đợi Upgrade từ bất kỳ nguồn XP nào
        if self.player.pending_level_ups > 0 and self.state != self.STATE_UPGRADE:
            self.player.pending_level_ups -= 1
            self.hud.trigger_level_up() # Hiệu ứng Flash
            self._trigger_upgrade(between_waves=False)

    # ------------------------------------------------------------------ #
    #  Combat helpers                                                      #
    # ------------------------------------------------------------------ #
    def _check_player_projectile_hits(self):
        """Check player projectiles against enemies and boss."""
        targets = list(self.wave_mgr.enemies)
        if self.boss and self.boss.alive:
            targets.append(self.boss)

        for proj in self.player.projectiles:
            if not proj.alive:
                continue
            for target in targets:
                if not target.alive:
                    continue
                if id(target) in proj.hit_enemies:
                    continue
                dist = math.hypot(proj.x - target.x, proj.y - target.y)
                if dist < target.size + proj.size:
                    dx = target.x - proj.x
                    dy = target.y - proj.y
                    d = math.hypot(dx, dy) or 1
                    total_dmg = proj.damage * (1 + (self.player.damage - PLAYER_DAMAGE) / PLAYER_DAMAGE)
                    total_dmg = proj.damage * self.player.damage / PLAYER_DAMAGE
                    target.take_damage(total_dmg, dx / d * 0.5, dy / d * 0.5)
                    if hasattr(target, 'apply_knockback'):
                        target.apply_knockback(proj.x, proj.y)
                    if proj.piercing:
                        proj.hit_enemies.add(id(target))
                    else:
                        # Fireball / bomb handled on expire; just kill regular bullet
                        if not (hasattr(proj, '_is_fireball') or hasattr(proj, '_is_bomb')):
                            proj.lifetime = 0
                    break

        # Laser beams
        for lb in self.player.laser_beams:
            if not lb.alive:
                continue
            for target in targets:
                if not target.alive:
                    continue
                # Check if target is on the laser line
                if self._point_near_line(target.x, target.y,
                                          lb.x, lb.y, lb.dx, lb.dy, target.size + 8):
                    dmg = lb.damage * self.player.damage / PLAYER_DAMAGE * 0.016  # per frame
                    target.take_damage(dmg)

    def _point_near_line(self, px, py, lx, ly, ldx, ldy, tol) -> bool:
        """Check if point (px,py) is within tol of the ray from (lx,ly) in direction (ldx,ldy)."""
        tx = px - lx; ty = py - ly
        proj = tx * ldx + ty * ldy
        if proj < 0:
            return False
        perp_x = tx - proj * ldx
        perp_y = ty - proj * ldy
        return math.hypot(perp_x, perp_y) < tol

    def _check_aoe_hits(self, dt):
        targets = list(self.wave_mgr.enemies)
        if self.boss and self.boss.alive:
            targets.append(self.boss)
        for zone in self.player.aoe_zones:
            for target in targets:
                if not target.alive:
                    continue
                dist = math.hypot(target.x - zone.x, target.y - zone.y)
                if dist < zone.radius + target.size:
                    dmg = zone.dps * dt * self.player.damage / PLAYER_DAMAGE
                    target.take_damage(dmg)

    def _check_orb_hits(self):
        orb_skill = self.player.get_orb_skill()
        if not orb_skill:
            return
        orb = orb_skill.orb
        targets = list(self.wave_mgr.enemies)
        if self.boss and self.boss.alive:
            targets.append(self.boss)
        for target in targets:
            if not target.alive:
                continue
            dmg = orb.check_hit(target, self.player.x, self.player.y)
            if dmg:
                target.take_damage(dmg * self.player.damage / PLAYER_DAMAGE)

    # ------------------------------------------------------------------ #
    #  Wave / boss transitions                                             #
    # ------------------------------------------------------------------ #
    def _spawn_boss(self):
        angle = random.uniform(0, math.pi * 2)
        bx = max(TILE_SIZE * 3, min(WORLD_W - TILE_SIZE * 3, self.player.x + math.cos(angle) * 350))
        by = max(TILE_SIZE * 3, min(WORLD_H - TILE_SIZE * 3, self.player.y + math.sin(angle) * 350))
        self.boss = Boss(bx, by, self.wave_mgr.wave)
        self.camera.shake(intensity=18, duration=0.8) # Boss ra rung mạnh hơn
        self._wave_banner_alpha = 255

    def _trigger_upgrade(self, between_waves: bool = False):
        self.upgrade_menu.show(generate_upgrades(self.player, 3))
        self._between_waves = between_waves
        self.state = self.STATE_UPGRADE

    def _start_next_wave(self):
        self.wave_mgr.start_next_wave()
        self._wave_banner_alpha = 255

    def _trigger_game_over(self):
        self.score += int(self.total_kills * 10 + self.elapsed_time * 5)
        new_hs = self.score > self.high_score
        if new_hs: self.high_score = self.score; save_highscore(self.high_score)
        self._go_stats = {"wave": self.wave_mgr.wave, "kills": self.total_kills, "time": self.elapsed_time, "level": self.player.level, "score": self.score, "new_highscore": new_hs}
        self.state = self.STATE_GAME_OVER

    # ------------------------------------------------------------------ #
    #  Drawing (per state)                                                 #
    # ------------------------------------------------------------------ #
    def _draw(self):
        if self.state == self.STATE_MENU: self.start_menu.draw(self.screen, self.high_score)
        elif self.state in (self.STATE_PLAYING, self.STATE_UPGRADE, self.STATE_PAUSED):
            self._draw_gameplay()
            if self.state == self.STATE_UPGRADE: self.upgrade_menu.draw(self.screen)
            elif self.state == self.STATE_PAUSED: self.pause_menu.draw(self.screen) # VẼ PAUSE MENU
        elif self.state == self.STATE_GAME_OVER:
            self._draw_gameplay()
            self.gameover_scr.draw(self.screen, self._go_stats)

    def _draw_gameplay(self):
        self.screen.fill((15, 23, 42)) # Slate 900 Background
        self.game_map.draw(self.screen, self.camera)
        for item in self.items: item.draw(self.screen, self.camera)
        self.wave_mgr.draw(self.screen, self.camera)
        if self.boss: self.boss.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        self.hud.draw(self.screen, self.player, self.wave_mgr, self.boss, self.total_kills, self.elapsed_time)
        if self._wave_banner_alpha > 0: self.hud.show_wave_banner(self.screen, self.wave_mgr.wave, int(self._wave_banner_alpha))


# ─────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────
if __name__ == "__main__":
    game = Game()
    game.run()
