# ui.py - Modern UI & Pause System
import pygame
import math
import random
from config import *

def get_font(size, bold=False):
    """Dynamic font loader fallback to standard modern sans-serif"""
    return pygame.font.SysFont("Segoe UI, Arial, Helvetica", size, bold=bold)

class Camera:
    def __init__(self):
        self.offset = pygame.math.Vector2(0, 0)
        self._shake_timer = 0.0
        self._shake_intensity = 0.0

    def follow(self, target_x: float, target_y: float, dt: float):
        dest_x = target_x - SCREEN_WIDTH / 2
        dest_y = target_y - SCREEN_HEIGHT / 2
        dest_x = max(0, min(WORLD_W - SCREEN_WIDTH, dest_x))
        dest_y = max(0, min(WORLD_H - SCREEN_HEIGHT, dest_y))
        speed = 10.0 # Tăng tốc độ mượt camera
        self.offset.x += (dest_x - self.offset.x) * min(1.0, speed * dt)
        self.offset.y += (dest_y - self.offset.y) * min(1.0, speed * dt)

    def shake(self, intensity=SHAKE_INTENSITY, duration=SHAKE_DURATION):
        self._shake_intensity = intensity
        self._shake_timer = duration

    def update(self, dt: float):
        if self._shake_timer > 0: self._shake_timer -= dt

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        sx, sy = wx - self.offset.x, wy - self.offset.y
        if self._shake_timer > 0:
            frac = self._shake_timer / SHAKE_DURATION
            sx += random.uniform(-1, 1) * self._shake_intensity * frac
            sy += random.uniform(-1, 1) * self._shake_intensity * frac
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        return sx + self.offset.x, sy + self.offset.y

class HUD:
    def __init__(self):
        self._font_lg  = get_font(24, bold=True)
        self._font_md  = get_font(16, bold=True)
        self._font_sm  = get_font(13, bold=True)
        self._font_em  = pygame.font.SysFont("Segoe UI Emoji", 20)
        self._font_big = get_font(36, bold=True)
        self.level_up_flash = 0.0

    def trigger_level_up(self):
        self.level_up_flash = 1.0

    def draw(self, surface: pygame.Surface, player, wave_mgr, boss=None, kill_count=0, elapsed=0.0):
        self._draw_hp_bar(surface, player)
        self._draw_xp_bar(surface, player)
        self._draw_wave_info(surface, wave_mgr, kill_count, elapsed)
        self._draw_skills(surface, player)
        if boss and boss.alive: self._draw_boss_bar(surface, boss)

        # Level up visual feedback
        if self.level_up_flash > 0:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(150 * self.level_up_flash)))
            surface.blit(flash, (0, 0))
            self.level_up_flash = max(0.0, self.level_up_flash - 0.02) # Phai dần đều (dựa trên frames)

    def _draw_hp_bar(self, surface, player):
        bx, by, bw, bh = 20, 20, 240, 24
        # Dropshadow modern
        pygame.draw.rect(surface, (10, 10, 15, 180), (bx, by+4, bw, bh), border_radius=8)
        pygame.draw.rect(surface, UI_PANEL, (bx - 6, by - 6, bw + 12, bh + 12), border_radius=10)
        
        pygame.draw.rect(surface, DARK_RED, (bx, by, bw, bh), border_radius=6)
        frac = max(0, player.hp / player.max_hp)
        bar_color = GREEN if frac > 0.5 else (YELLOW if frac > 0.25 else RED)
        pygame.draw.rect(surface, bar_color, (bx, by, int(bw * frac), bh), border_radius=6)
        
        hp_text = self._font_md.render(f"HP: {int(player.hp)} / {int(player.max_hp)}", True, WHITE)
        surface.blit(hp_text, (bx + 10, by + 2))

    def _draw_xp_bar(self, surface, player):
        bx, by, bw, bh = 20, 55, 240, 16
        pygame.draw.rect(surface, UI_PANEL, (bx - 6, by - 4, bw + 12, bh + 8), border_radius=6)
        pygame.draw.rect(surface, (30, 41, 59), (bx, by, bw, bh), border_radius=5)
        frac = min(1.0, player.xp / player.xp_to_next)
        pygame.draw.rect(surface, (56, 189, 248), (bx, by, int(bw * frac), bh), border_radius=5)
        
        lv_text = self._font_sm.render(f"LVL {player.level} • {int(player.xp)}/{player.xp_to_next} XP", True, WHITE)
        # Bóng chữ
        shadow = self._font_sm.render(f"LVL {player.level} • {int(player.xp)}/{player.xp_to_next} XP", True, BLACK)
        surface.blit(shadow, (bx + bw//2 - shadow.get_width()//2, by + 2))
        surface.blit(lv_text, (bx + bw//2 - lv_text.get_width()//2, by + 1))

    def _draw_wave_info(self, surface, wave_mgr, kill_count, elapsed):
        cx = SCREEN_WIDTH // 2
        wave_text = self._font_lg.render(f"WAVE {wave_mgr.wave}", True, GOLD)
        surface.blit(wave_text, (cx - wave_text.get_width() // 2, 15))

        kill_text = self._font_sm.render(f"Progression: {wave_mgr.wave_kills} / {wave_mgr.wave_kill_target}", True, LIGHT_GRAY)
        surface.blit(kill_text, (cx - kill_text.get_width() // 2, 45))

        mins, secs = int(elapsed) // 60, int(elapsed) % 60
        time_text = self._font_md.render(f"{mins:02d}:{secs:02d}", True, WHITE)
        surface.blit(time_text, (SCREEN_WIDTH - time_text.get_width() - 25, 20))

    def _draw_skills(self, surface, player):
        skills = list(player.skills.values())
        icon_size, gap = 52, 10
        total_w = len(skills) * (icon_size + gap) - gap
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        y = SCREEN_HEIGHT - icon_size - 20

        for i, skill in enumerate(skills):
            x = start_x + i * (icon_size + gap)
            pygame.draw.rect(surface, (15, 23, 42, 200), (x, y, icon_size, icon_size), border_radius=12)
            pygame.draw.rect(surface, skill.color, (x, y, icon_size, icon_size), 2, border_radius=12)

            if not skill.ready:
                cd_h = int(icon_size * (1 - skill.cd_fraction))
                cd_surf = pygame.Surface((icon_size, cd_h), pygame.SRCALPHA)
                cd_surf.fill((0, 0, 0, 180))
                surface.blit(cd_surf, (x, y + icon_size - cd_h))

            try:
                icon_surf = self._font_em.render(skill.icon, True, WHITE)
                surface.blit(icon_surf, (x + icon_size // 2 - icon_surf.get_width() // 2, y + 8))
            except Exception: pass

            lv = self._font_sm.render(f"Lv{skill.level}", True, GOLD)
            surface.blit(lv, (x + icon_size - lv.get_width() - 4, y + icon_size - 16))

    def _draw_boss_bar(self, surface, boss):
        bw, bh = SCREEN_WIDTH - 400, 24
        bx, by = 200, 80
        pygame.draw.rect(surface, UI_PANEL, (bx - 4, by - 4, bw + 8, bh + 8), border_radius=8)
        pygame.draw.rect(surface, DARK_RED, (bx, by, bw, bh), border_radius=6)
        pygame.draw.rect(surface, boss.color, (bx, by, int(bw * boss.hp_frac), bh), border_radius=6)
        label = self._font_md.render(f"BOSS PHASE {boss.phase}  -  {int(boss.hp)}/{int(boss.max_hp)}", True, WHITE)
        surface.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, by + 3))

    def show_wave_banner(self, surface, wave, alpha):
        if alpha <= 0: return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(150, alpha // 2)))
        surface.blit(overlay, (0, 0))
        text = self._font_big.render(f"WAVE {wave} START", True, (*GOLD, min(255, alpha)))
        surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 20))

# ─────────────────────────────────────────────────
# MỚI: PAUSE MENU (Hệ thống Pause chuẩn)
# ─────────────────────────────────────────────────
class PauseMenu:
    def __init__(self):
        self._font_title = get_font(56, bold=True)
        self._font_btn = get_font(28, bold=True)
        self.buttons = [
            {"label": "Resume Game (ESC)", "action": "resume", "rect": None},
            {"label": "Restart", "action": "restart", "rect": None},
            {"label": "Quit to Menu", "action": "quit", "rect": None}
        ]
        self._hover = -1

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "resume"
        if event.type == pygame.MOUSEMOTION:
            self._hover = -1
            for i, b in enumerate(self.buttons):
                if b["rect"] and b["rect"].collidepoint(event.pos): self._hover = i
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._hover >= 0: return self.buttons[self._hover]["action"]
        return None

    def draw(self, surface: pygame.Surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 220)) # Dark Slate 900 blur effect
        surface.blit(overlay, (0, 0))

        title = self._font_title.render("PAUSED", True, WHITE)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 200))

        btn_w, btn_h, gap = 300, 60, 20
        start_y = 320
        for i, btn in enumerate(self.buttons):
            rect = pygame.Rect(SCREEN_WIDTH//2 - btn_w//2, start_y + i*(btn_h + gap), btn_w, btn_h)
            btn["rect"] = rect
            color = (56, 189, 248) if i == self._hover else (30, 41, 59) # Light blue vs Dark slate
            
            pygame.draw.rect(surface, color, rect, border_radius=12)
            pygame.draw.rect(surface, WHITE, rect, 2, border_radius=12)
            
            t = self._font_btn.render(btn["label"], True, WHITE)
            surface.blit(t, (rect.centerx - t.get_width()//2, rect.centery - t.get_height()//2))

# (Giữ nguyên StartMenu & GameOverScreen ở file cũ, chỉ đổi _font thành get_font nếu muốn)


# ─────────────────────────────────────────────────
#  Start Menu
# ─────────────────────────────────────────────────
class StartMenu:
    """Game start / main menu screen."""
    def __init__(self):
        self._font_title = pygame.font.SysFont("Arial", 60, bold=True)
        self._font_sub   = pygame.font.SysFont("Arial", 22)
        self._font_btn   = pygame.font.SysFont("Arial", 28, bold=True)
        self._font_info  = pygame.font.SysFont("Arial", 15)
        self._hover_play = False
        self._tick = 0.0

    def update(self, dt):
        self._tick += dt

    def handle_event(self, event) -> str | None:
        """Returns 'play' or None."""
        if event.type == pygame.MOUSEMOTION:
            self._hover_play = self._play_rect().collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._play_rect().collidepoint(event.pos):
                return "play"
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return "play"
        return None

    def _play_rect(self) -> pygame.Rect:
        return pygame.Rect(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 20, 240, 60)

    def draw(self, surface: pygame.Surface, high_score: int = 0):
        # Animated background
        surface.fill((10, 12, 20))
        t = self._tick

        # Starfield dots
        import random as _random, math as _math
        _random.seed(42)
        for _ in range(80):
            sx = _random.randint(0, SCREEN_WIDTH)
            sy = _random.randint(0, SCREEN_HEIGHT)
            brightness = int(100 + 80 * _math.sin(t * 1.5 + sx + sy))
            pygame.draw.circle(surface, (brightness, brightness, brightness), (sx, sy), 1)

        # Title
        pulse = int(20 * math.sin(t * 2))
        title_color = (200 + pulse, 160 + pulse, 0)
        title = self._font_title.render("SURVIVAL 2D", True, title_color)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 160))

        sub = self._font_sub.render("Wave Survival Roguelite", True, (140, 140, 200))
        surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 235))

        # Play button
        play_rect = self._play_rect()
        btn_color = (0, 180, 80) if self._hover_play else (0, 130, 60)
        pygame.draw.rect(surface, btn_color, play_rect, border_radius=12)
        pygame.draw.rect(surface, WHITE, play_rect, 2, border_radius=12)
        play_text = self._font_btn.render("▶  PLAY", True, WHITE)
        surface.blit(play_text, (play_rect.centerx - play_text.get_width() // 2,
                                   play_rect.centery - play_text.get_height() // 2))

        # Controls
        controls = [
            "WASD / Arrow Keys – Move",
            "Auto-fire toward cursor",
            "Dash skill active on cooldown",
            "Kill enemies → earn XP → upgrades",
        ]
        cy = SCREEN_HEIGHT // 2 + 110
        for line in controls:
            cs = self._font_info.render(line, True, (120, 120, 160))
            surface.blit(cs, (SCREEN_WIDTH // 2 - cs.get_width() // 2, cy))
            cy += 20

        # High score
        if high_score > 0:
            hs_text = self._font_sub.render(f"🏆 High Score: {high_score}", True, GOLD)
            surface.blit(hs_text, (SCREEN_WIDTH // 2 - hs_text.get_width() // 2,
                                    SCREEN_HEIGHT - 60))


# ─────────────────────────────────────────────────
#  Game Over Screen
# ─────────────────────────────────────────────────
class GameOverScreen:
    """Game over / results screen."""
    def __init__(self):
        self._font_title  = pygame.font.SysFont("Arial", 52, bold=True)
        self._font_stat   = pygame.font.SysFont("Arial", 22)
        self._font_btn    = pygame.font.SysFont("Arial", 26, bold=True)
        self._hover_retry = False
        self._hover_menu  = False
        self._anim = 0.0

    def update(self, dt):
        self._anim = min(1.0, self._anim + dt * 2)

    def _retry_rect(self):
        return pygame.Rect(SCREEN_WIDTH // 2 - 130, SCREEN_HEIGHT // 2 + 120, 240, 56)

    def _menu_rect(self):
        return pygame.Rect(SCREEN_WIDTH // 2 - 130, SCREEN_HEIGHT // 2 + 190, 240, 50)

    def handle_event(self, event) -> str | None:
        """Returns 'retry', 'menu', or None."""
        if event.type == pygame.MOUSEMOTION:
            self._hover_retry = self._retry_rect().collidepoint(event.pos)
            self._hover_menu  = self._menu_rect().collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._retry_rect().collidepoint(event.pos):
                return "retry"
            if self._menu_rect().collidepoint(event.pos):
                return "menu"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                return "retry"
            if event.key == pygame.K_ESCAPE:
                return "menu"
        return None

    def draw(self, surface: pygame.Surface, stats: dict):
        # Dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(200 * self._anim)))
        surface.blit(overlay, (0, 0))

        a = self._anim

        # Title
        title = self._font_title.render("GAME OVER", True, (int(220 * a), int(40 * a), int(40 * a)))
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2,
                               SCREEN_HEIGHT // 2 - 200))

        # Stats
        stat_lines = [
            f"Wave Reached:  {stats.get('wave', 1)}",
            f"Total Kills:   {stats.get('kills', 0)}",
            f"Time Survived: {int(stats.get('time', 0)) // 60:02d}:{int(stats.get('time', 0)) % 60:02d}",
            f"Player Level:  {stats.get('level', 1)}",
            f"Score:         {stats.get('score', 0)}",
        ]
        if stats.get("new_highscore"):
            stat_lines.append("🏆  NEW HIGH SCORE!")

        sy = SCREEN_HEIGHT // 2 - 90
        for line in stat_lines:
            color = GOLD if "HIGH SCORE" in line else (int(200 * a), int(200 * a), int(220 * a))
            s = self._font_stat.render(line, True, color)
            surface.blit(s, (SCREEN_WIDTH // 2 - s.get_width() // 2, sy))
            sy += 34

        # Retry button
        rr = self._retry_rect()
        bc = (0, 180, 80) if self._hover_retry else (0, 130, 60)
        pygame.draw.rect(surface, bc, rr, border_radius=10)
        pygame.draw.rect(surface, WHITE, rr, 2, border_radius=10)
        rt = self._font_btn.render("↺  Retry  [R]", True, WHITE)
        surface.blit(rt, (rr.centerx - rt.get_width() // 2, rr.centery - rt.get_height() // 2))

        # Menu button
        mr = self._menu_rect()
        mc = (60, 60, 160) if self._hover_menu else (40, 40, 120)
        pygame.draw.rect(surface, mc, mr, border_radius=10)
        pygame.draw.rect(surface, UI_BORDER, mr, 2, border_radius=10)
        mt = self._font_btn.render("Main Menu  [Esc]", True, WHITE)
        surface.blit(mt, (mr.centerx - mt.get_width() // 2, mr.centery - mt.get_height() // 2))
