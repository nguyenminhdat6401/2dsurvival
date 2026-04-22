# items.py - Item drop and pickup system

import pygame
import math
import random
from config import *


class DroppedItem:
    """
    Item that drops from slain enemies.
    Auto-attracted to player when magnet skill active.
    """
    HP_POTION   = "hp_potion"
    DMG_BUFF    = "dmg_buff"
    SPEED_BUFF  = "speed_buff"
    XP_GEM      = "xp_gem"

    # Visual configs  (color, icon_char, label)
    _configs = {
        HP_POTION:  ((220, 60, 80),  "HP",  "+HP"),
        DMG_BUFF:   ((255, 140, 0),  "DMG", "+ATK"),
        SPEED_BUFF: ((80, 200, 255), "SPD", "+SPD"),
        XP_GEM:     ((120, 80, 255), "XP",  "+XP"),
    }

    def __init__(self, x: float, y: float, item_type: str):
        self.x, self.y = float(x), float(y)
        self.item_type = item_type
        self.alive = True

        # Lifetime so map doesn't fill up
        self.lifetime = 18.0

        # Bob animation
        self._age = random.uniform(0, math.pi * 2)
        self._vx = random.uniform(-40, 40)
        self._vy = random.uniform(-60, -20)
        self._friction = 6.0

        # Magnet pull
        self._pulled = False

        color, icon, label = self._configs.get(item_type, ((200, 200, 200), "?", "?"))
        self.color = color
        self.icon  = icon
        self.label = label

        self._font = pygame.font.SysFont("Arial", 11, bold=True)
        self.size  = 10

    def update(self, dt: float, player) -> bool:
        """Returns True if item was collected."""
        if not self.alive:
            return False

        self.lifetime -= dt

        # Physics (initial bounce)
        self._vx *= max(0, 1 - self._friction * dt)
        self._vy += 120 * dt   # gravity
        self.x += self._vx * dt
        self.y += self._vy * dt
        # Ground (stop falling after 0.4 s)
        if self.lifetime < 17.6:
            self._vy = 0; self._vx = 0

        # Magnet pull
        pull_r = player.get_magnet_radius()
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        if dist < pull_r:
            pull_spd = 220 + (pull_r - dist) * 2
            if dist > 0:
                self.x += dx / dist * pull_spd * dt
                self.y += dy / dist * pull_spd * dt

        # Pickup collision
        if dist < player.size + self.size:
            self._on_pickup(player)
            self.alive = False
            return True

        # Expire
        if self.lifetime <= 0:
            self.alive = False

        self._age += dt * 3
        return False

    def _on_pickup(self, player):
        if self.item_type == self.HP_POTION:
            player.hp = min(player.max_hp, player.hp + 25)
        elif self.item_type == self.DMG_BUFF:
            player.damage *= 1.08
        elif self.item_type == self.SPEED_BUFF:
            player.speed *= 1.05
        elif self.item_type == self.XP_GEM:
            player.gain_xp(15)

    def draw(self, surface: pygame.Surface, camera):
        if not self.alive:
            return
        sx, sy = camera.world_to_screen(self.x, self.y)
        sx, sy = int(sx), int(sy)

        # Blink when about to expire
        if self.lifetime < 4 and int(self.lifetime * 5) % 2 == 0:
            return

        # Bob
        by_off = int(math.sin(self._age) * 3)
        sy += by_off

        # Shadow
        pygame.draw.ellipse(surface, (0, 0, 0),
                             (sx - self.size, sy + self.size - 3,
                              self.size * 2, 6))

        # Item circle
        pygame.draw.circle(surface, self.color, (sx, sy), self.size)
        pygame.draw.circle(surface, WHITE, (sx, sy), self.size, 2)

        # Inner icon
        t = self._font.render(self.icon, True, WHITE)
        surface.blit(t, (sx - t.get_width() // 2, sy - t.get_height() // 2))

    def _on_pickup(self, player):
        if self.item_type == self.HP_POTION:
            player.hp = min(player.max_hp, player.hp + 25)
        elif self.item_type == self.DMG_BUFF:
            player.damage *= 1.08
        elif self.item_type == self.SPEED_BUFF:
            player.speed *= 1.05
        elif self.item_type == self.XP_GEM:
            player.gain_xp(15)  # KẾT NỐI VỚI HÀM XP MỚI

    def draw(self, surface: pygame.Surface, camera):
        if not self.alive: return
        sx, sy = camera.world_to_screen(self.x, self.y)
        sx, sy = int(sx), int(sy)

        if self.lifetime < 4 and int(self.lifetime * 5) % 2 == 0: return

        by_off = int(math.sin(self._age) * 3)
        sy += by_off

        # Shadow
        pygame.draw.ellipse(surface, (0, 0, 0, 100), (sx - self.size, sy + self.size - 3, self.size * 2, 6))

        # Hiệu ứng Glow cho XP GEM
        if self.item_type == self.XP_GEM:
            glow_surf = pygame.Surface((self.size*4, self.size*4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*self.color, 80), (self.size*2, self.size*2), self.size*1.8)
            surface.blit(glow_surf, (sx - self.size*2, sy - self.size*2))

        pygame.draw.circle(surface, self.color, (sx, sy), self.size)
        pygame.draw.circle(surface, WHITE, (sx, sy), self.size, 2)

        t = self._font.render(self.icon, True, WHITE)
        surface.blit(t, (sx - t.get_width() // 2, sy - t.get_height() // 2))


# ─────────────────────────────────────────────────
#  Item spawning helper
# ─────────────────────────────────────────────────
def maybe_drop_items(x: float, y: float, is_boss: bool = False) -> list[DroppedItem]:
    """Return a list of items to drop at position."""
    items = []
    if is_boss:
        # Boss always drops goodies
        items.append(DroppedItem(x, y, DroppedItem.HP_POTION))
        items.append(DroppedItem(x + 20, y, DroppedItem.DMG_BUFF))
        items.append(DroppedItem(x - 20, y, DroppedItem.XP_GEM))
        return items

    if random.random() < DROP_CHANCE_HP:
        items.append(DroppedItem(x, y, DroppedItem.HP_POTION))
    if random.random() < DROP_CHANCE_DAMAGE:
        items.append(DroppedItem(x + 15, y, DroppedItem.DMG_BUFF))
    if random.random() < DROP_CHANCE_SPEED:
        items.append(DroppedItem(x, y + 15, DroppedItem.SPEED_BUFF))
    if random.random() < 0.35:
        items.append(DroppedItem(x - 10, y - 10, DroppedItem.XP_GEM))

    return items
