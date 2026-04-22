# upgrade_system.py - RPG upgrade menu with stat, skill unlock, and skill upgrade choices

import pygame
import random
from config import *
from skills import ALL_SKILLS


# ─────────────────────────────────────────────────
#  Upgrade definition
# ─────────────────────────────────────────────────
class Upgrade:
    """Represents a single upgrade option shown to the player."""
    STAT    = "stat"
    UNLOCK  = "unlock"
    UPGRADE = "upgrade"

    def __init__(self, kind: str, title: str, description: str,
                 color: tuple, icon: str, apply_fn):
        self.kind = kind
        self.title = title
        self.description = description
        self.color = color
        self.icon = icon
        self._apply = apply_fn

    def apply(self, player):
        self._apply(player)


# ─────────────────────────────────────────────────
#  Upgrade generator
# ─────────────────────────────────────────────────
def generate_upgrades(player, count=3) -> list[Upgrade]:
    """
    Generate `count` distinct random upgrade choices appropriate
    for the player's current state.
    """
    pool: list[Upgrade] = []

    # --- Stat upgrades ---
    pool.append(Upgrade(
        Upgrade.STAT, "Max HP +30", "+30 maximum health and restore 20 HP.",
        RED, "❤️",
        lambda p: (setattr(p, "max_hp", p.max_hp + 30),
                   setattr(p, "hp", min(p.max_hp, p.hp + 20)))
    ))
    pool.append(Upgrade(
        Upgrade.STAT, "Damage +25%", "All attack damage +25%.",
        ORANGE, "⚔️",
        lambda p: setattr(p, "damage", p.damage * 1.25)
    ))
    pool.append(Upgrade(
        Upgrade.STAT, "Speed +15%", "Movement speed +15%.",
        YELLOW, "👟",
        lambda p: setattr(p, "speed", p.speed * 1.15)
    ))
    pool.append(Upgrade(
        Upgrade.STAT, "HP Regen +1/s", "Regenerate 1 HP per second.",
        GREEN, "💚",
        lambda p: setattr(p, "hp_regen", p.hp_regen + 1.0)
    ))
    pool.append(Upgrade(
        Upgrade.STAT, "Max HP +50", "+50 max HP and full heal.",
        RED, "❤️‍🔥",
        lambda p: (setattr(p, "max_hp", p.max_hp + 50),
                   setattr(p, "hp", p.max_hp))
    ))
    pool.append(Upgrade(
        Upgrade.STAT, "Attack Speed +20%", "All skill cooldowns reduced by 20%.",
        CYAN, "⏩",
        lambda p: _reduce_all_cooldowns(p, 0.8)
    ))
    pool.append(Upgrade(
        Upgrade.STAT, "Damage +40%", "Massive damage boost +40%.",
        (255, 80, 0), "🔥",
        lambda p: setattr(p, "damage", p.damage * 1.40)
    ))

    # --- Unlock new skills ---
    for key, cls in ALL_SKILLS.items():
        if not player.has_skill(key):
            skill_inst = cls()
            pool.append(Upgrade(
                Upgrade.UNLOCK,
                f"Unlock: {skill_inst.name}",
                skill_inst.description,
                skill_inst.color, skill_inst.icon,
                _make_unlock_fn(key)
            ))

    # --- Upgrade existing skills ---
    for key, skill in player.skills.items():
        pool.append(Upgrade(
            Upgrade.UPGRADE,
            f"Upgrade: {skill.name} Lv{skill.level}→{skill.level+1}",
            skill.get_upgrade_desc(),
            skill.color, skill.icon,
            _make_upgrade_fn(key)
        ))

    # Shuffle and pick distinct choices
    random.shuffle(pool)
    chosen = []
    seen_titles = set()
    for u in pool:
        if u.title not in seen_titles:
            chosen.append(u)
            seen_titles.add(u.title)
        if len(chosen) >= count:
            break

    # Pad if needed
    while len(chosen) < count:
        chosen.append(Upgrade(
            Upgrade.STAT, "Bonus HP Regen", "+2 HP regen per second.",
            GREEN, "💚",
            lambda p: setattr(p, "hp_regen", p.hp_regen + 2.0)
        ))

    return chosen


def _make_unlock_fn(key: str):
    def fn(player):
        player.upgrade_skill(key)
    return fn


def _make_upgrade_fn(key: str):
    def fn(player):
        player.upgrade_skill(key)
    return fn


def _reduce_all_cooldowns(player, factor: float):
    for skill in player.skills.values():
        skill.cooldown = max(0.05, skill.cooldown * factor)
        skill.base_cooldown = max(0.05, skill.base_cooldown * factor)


# ─────────────────────────────────────────────────
#  Upgrade Menu (UI)
# ─────────────────────────────────────────────────
class UpgradeMenu:
    """
    Fullscreen overlay presenting 3 upgrade cards.
    The player clicks one to apply it.
    """
    CARD_W = 280
    CARD_H = 200
    CARD_GAP = 30

    def __init__(self):
        self.active = False
        self.upgrades: list[Upgrade] = []
        self._hover = -1
        self._chosen = -1
        self._anim = 0.0     # 0→1 slide-in animation
        self._font_title  = pygame.font.SysFont("Arial", 20, bold=True)
        self._font_desc   = pygame.font.SysFont("Arial", 14)
        self._font_icon   = pygame.font.SysFont("Segoe UI Emoji", 36)
        self._font_header = pygame.font.SysFont("Arial", 30, bold=True)
        self._font_kind   = pygame.font.SysFont("Arial", 11)

    def show(self, upgrades: list[Upgrade]):
        self.upgrades = upgrades
        self.active = True
        self._chosen = -1
        self._anim = 0.0

    def update(self, dt: float):
        if self.active:
            self._anim = min(1.0, self._anim + dt * 4)

    def handle_event(self, event) -> int:
        """Returns index of chosen upgrade or -1."""
        if not self.active:
            return -1
        if event.type == pygame.MOUSEMOTION:
            self._hover = self._get_card_at(*event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            idx = self._get_card_at(*event.pos)
            if idx >= 0:
                return idx
        return -1

    def _get_card_positions(self):
        total_w = len(self.upgrades) * self.CARD_W + (len(self.upgrades) - 1) * self.CARD_GAP
        start_x = (SCREEN_WIDTH - total_w) // 2
        cy = (SCREEN_HEIGHT - self.CARD_H) // 2 + 30
        positions = []
        for i in range(len(self.upgrades)):
            x = start_x + i * (self.CARD_W + self.CARD_GAP)
            positions.append((x, cy))
        return positions

    def _get_card_at(self, mx, my) -> int:
        for i, (x, y) in enumerate(self._get_card_positions()):
            if x <= mx <= x + self.CARD_W and y <= my <= y + self.CARD_H:
                return i
        return -1

    def draw(self, surface: pygame.Surface):
        if not self.active:
            return

        # Dim background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * self._anim)))
        surface.blit(overlay, (0, 0))

        # Header
        header = self._font_header.render("⬆  CHOOSE AN UPGRADE  ⬆", True, GOLD)
        surface.blit(header, (SCREEN_WIDTH // 2 - header.get_width() // 2, 80))

        positions = self._get_card_positions()
        for i, (x, y) in enumerate(positions):
            # Slide-in from below
            slide = int((1 - self._anim) * 200)
            ry = y + slide

            upg = self.upgrades[i]
            hovered = (i == self._hover)

            self._draw_card(surface, x, ry, upg, hovered, i)

        # Footer hint
        hint = self._font_desc.render("Click a card to select", True, (140, 140, 160))
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                             SCREEN_HEIGHT - 60))

    def _draw_card(self, surface, x, y, upg: Upgrade, hovered: bool, idx: int):
        # HIỆU ỨNG HOVER: Nảy Card lên trên và đổ bóng
        if hovered:
            y -= 12  # Lift card up
            border_color = (56, 189, 248) # Xanh dương nổi bật
            shadow_rect = pygame.Rect(x - 5, y + 10, self.CARD_W + 10, self.CARD_H)
            pygame.draw.rect(surface, (0, 0, 0, 100), shadow_rect, border_radius=16)
        else:
            border_color = (60, 60, 100)

        # Card BG
        pygame.draw.rect(surface, (30, 41, 59), (x, y, self.CARD_W, self.CARD_H), border_radius=16)
        pygame.draw.rect(surface, border_color, (x, y, self.CARD_W, self.CARD_H), 3, border_radius=16)

        # Gradient Top Bar theo màu Skill
        bar_h = 60
        for row in range(bar_h):
            alpha = int(220 * (1 - row / bar_h))
            r, g, b = upg.color
            pygame.draw.line(surface, (r, g, b), (x+2, y+row+2), (x + self.CARD_W-3, y+row+2))

        kind_labels = {Upgrade.STAT: "STAT UPGRADE", Upgrade.UNLOCK: "NEW SKILL", Upgrade.UPGRADE: "UPGRADE"}
        badge = self._font_kind.render(kind_labels.get(upg.kind, ""), True, WHITE)
        surface.blit(badge, (x + 12, y + 10))

        try:
            icon_surf = self._font_icon.render(upg.icon, True, WHITE)
            surface.blit(icon_surf, (x + self.CARD_W // 2 - icon_surf.get_width() // 2, y + bar_h + 10))
        except Exception: pass

        title = self._font_title.render(upg.title, True, WHITE)
        if title.get_width() > self.CARD_W - 16: title = self._font_kind.render(upg.title, True, WHITE)
        surface.blit(title, (x + self.CARD_W // 2 - title.get_width() // 2, y + bar_h + 60))

        desc_lines = self._wrap_text(upg.description, self._font_desc, self.CARD_W - 30)
        for j, line in enumerate(desc_lines[:3]):
            dsurf = self._font_desc.render(line, True, (200, 200, 220))
            surface.blit(dsurf, (x + self.CARD_W//2 - dsurf.get_width()//2, y + bar_h + 95 + j * 20))

        # Gradient top bar
        bar_h = 50
        for row in range(bar_h):
            alpha = int(180 * (1 - row / bar_h))
            r, g, b = upg.color
            pygame.draw.line(surface, (r, g, b),
                              (x, y + row), (x + self.CARD_W, y + row))

        # Type badge
        kind_labels = {Upgrade.STAT: "STAT", Upgrade.UNLOCK: "NEW SKILL",
                        Upgrade.UPGRADE: "UPGRADE"}
        kind_color = {Upgrade.STAT: GREEN, Upgrade.UNLOCK: PURPLE,
                       Upgrade.UPGRADE: CYAN}
        badge = self._font_kind.render(kind_labels.get(upg.kind, ""), True,
                                        kind_color.get(upg.kind, WHITE))
        surface.blit(badge, (x + 8, y + 6))

        # Icon
        try:
            icon_surf = self._font_icon.render(upg.icon, True, WHITE)
            surface.blit(icon_surf, (x + self.CARD_W // 2 - icon_surf.get_width() // 2,
                                      y + bar_h + 8))
        except Exception:
            pass

        # Title
        title = self._font_title.render(upg.title, True, WHITE)
        # Wrap title if too long
        if title.get_width() > self.CARD_W - 16:
            title = self._font_kind.render(upg.title, True, WHITE)
        surface.blit(title, (x + self.CARD_W // 2 - title.get_width() // 2,
                               y + bar_h + 52))

        # Description (wrapped)
        desc_lines = self._wrap_text(upg.description, self._font_desc, self.CARD_W - 20)
        for j, line in enumerate(desc_lines[:3]):
            dsurf = self._font_desc.render(line, True, (190, 190, 210))
            surface.blit(dsurf, (x + 10, y + bar_h + 80 + j * 18))

    def _wrap_text(self, text: str, font, max_w: int) -> list[str]:
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word
            if font.size(test)[0] <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
