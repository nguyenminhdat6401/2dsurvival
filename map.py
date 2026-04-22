# map.py - Tile-based map system with procedural generation

import pygame
import random
import math
from config import *


class Tile:
    """Represents a single tile on the map."""
    def __init__(self, tile_type: int):
        self.type = tile_type
        self.solid = tile_type in (TILE_WALL, TILE_TREE, TILE_ROCK, TILE_WATER)

    def get_color(self):
        colors = {
            TILE_GRASS:      (45, 110, 45),
            TILE_DARK_GRASS: (30, 85, 30),
            TILE_SAND:       (180, 160, 100),
            TILE_WALL:       (90, 80, 70),
            TILE_TREE:       (25, 90, 25),
            TILE_ROCK:       (100, 95, 90),
            TILE_WATER:      (30, 80, 160),
        }
        return colors.get(self.type, (50, 50, 50))

    def get_detail_color(self):
        """Slightly lighter color for tile decoration."""
        base = self.get_color()
        return tuple(min(255, c + 20) for c in base)


class GameMap:
    """
    Procedurally generated 2D tile map.
    Generates varied terrain with obstacles, open areas, and decoration.
    """
    def __init__(self):
        self.cols = MAP_COLS
        self.rows = MAP_ROWS
        self.tiles: list[list[Tile]] = []
        self._generate()
        self._tile_surface_cache: dict = {}

    # ------------------------------------------------------------------ #
    #  Generation                                                           #
    # ------------------------------------------------------------------ #
    def _generate(self):
        """Fill map with procedural terrain."""
        # Start with grass
        self.tiles = [[Tile(TILE_GRASS) for _ in range(self.cols)]
                      for _ in range(self.rows)]

        # Border walls
        for r in range(self.rows):
            for c in range(self.cols):
                if r == 0 or r == self.rows - 1 or c == 0 or c == self.cols - 1:
                    self.tiles[r][c] = Tile(TILE_WALL)

        # Scatter dark grass patches
        self._scatter_patches(TILE_DARK_GRASS, count=18, size=6)
        # Sand patches
        self._scatter_patches(TILE_SAND, count=8, size=4)
        # Water pools
        self._scatter_patches(TILE_WATER, count=5, size=3)
        # Rock clusters
        self._scatter_obstacles(TILE_ROCK, count=35, cluster=3)
        # Tree clusters
        self._scatter_obstacles(TILE_TREE, count=55, cluster=4)
        # Wall ruins (rectangular)
        self._place_ruins(count=6)

        # Clear spawn area around center so player can breathe
        cx, cy = self.rows // 2, self.cols // 2
        for dr in range(-4, 5):
            for dc in range(-4, 5):
                r, c = cy + dr, cx + dc
                if 0 < r < self.rows - 1 and 0 < c < self.cols - 1:
                    self.tiles[r][c] = Tile(TILE_GRASS)

    def _scatter_patches(self, tile_type, count, size):
        for _ in range(count):
            cr = random.randint(4, self.rows - 5)
            cc = random.randint(4, self.cols - 5)
            for dr in range(-size, size + 1):
                for dc in range(-size, size + 1):
                    if dr * dr + dc * dc <= size * size:
                        r, c = cr + dr, cc + dc
                        if 1 < r < self.rows - 2 and 1 < c < self.cols - 2:
                            if not self.tiles[r][c].solid:
                                self.tiles[r][c] = Tile(tile_type)

    def _scatter_obstacles(self, tile_type, count, cluster):
        for _ in range(count):
            cr = random.randint(3, self.rows - 4)
            cc = random.randint(3, self.cols - 4)
            for _ in range(cluster):
                dr = random.randint(-2, 2)
                dc = random.randint(-2, 2)
                r, c = cr + dr, cc + dc
                if 1 < r < self.rows - 2 and 1 < c < self.cols - 2:
                    self.tiles[r][c] = Tile(tile_type)

    def _place_ruins(self, count):
        for _ in range(count):
            cr = random.randint(5, self.rows - 6)
            cc = random.randint(5, self.cols - 6)
            h = random.randint(3, 6)
            w = random.randint(3, 6)
            for dr in range(h):
                for dc in range(w):
                    if dr == 0 or dr == h - 1 or dc == 0 or dc == w - 1:
                        r, c = cr + dr, cc + dc
                        if 1 < r < self.rows - 2 and 1 < c < self.cols - 2:
                            # Leave random gaps in walls
                            if random.random() > 0.25:
                                self.tiles[r][c] = Tile(TILE_WALL)

    # ------------------------------------------------------------------ #
    #  Tile queries                                                         #
    # ------------------------------------------------------------------ #
    def get_tile(self, row, col) -> Tile | None:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.tiles[row][col]
        return None

    def is_solid(self, row, col) -> bool:
        tile = self.get_tile(row, col)
        return tile is None or tile.solid

    def is_solid_world(self, wx, wy) -> bool:
        """Check world-coordinate position."""
        col = int(wx // TILE_SIZE)
        row = int(wy // TILE_SIZE)
        return self.is_solid(row, col)

    def get_solid_rects_near(self, wx, wy, radius=2) -> list[pygame.Rect]:
        """Return list of collision rects near a world position."""
        col = int(wx // TILE_SIZE)
        row = int(wy // TILE_SIZE)
        rects = []
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                r, c = row + dr, col + dc
                if self.is_solid(r, c):
                    rects.append(pygame.Rect(c * TILE_SIZE, r * TILE_SIZE,
                                             TILE_SIZE, TILE_SIZE))
        return rects

    def get_random_open_pos(self, margin=5) -> tuple[float, float]:
        """Return a random non-solid world position."""
        while True:
            r = random.randint(margin, self.rows - margin)
            c = random.randint(margin, self.cols - margin)
            if not self.is_solid(r, c):
                return (c * TILE_SIZE + TILE_SIZE // 2,
                        r * TILE_SIZE + TILE_SIZE // 2)

    # ------------------------------------------------------------------ #
    #  Rendering                                                            #
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface, camera):
        """Draw only visible tiles (frustum culling)."""
        cx, cy = camera.offset
        start_col = max(0, int(cx // TILE_SIZE) - 1)
        start_row = max(0, int(cy // TILE_SIZE) - 1)
        end_col = min(self.cols, start_col + SCREEN_WIDTH // TILE_SIZE + 3)
        end_row = min(self.rows, start_row + SCREEN_HEIGHT // TILE_SIZE + 3)

        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                tile = self.tiles[r][c]
                sx = c * TILE_SIZE - cx
                sy = r * TILE_SIZE - cy
                rect = pygame.Rect(sx, sy, TILE_SIZE, TILE_SIZE)

                pygame.draw.rect(surface, tile.get_color(), rect)

                # Draw tile details / decorations
                if tile.type == TILE_TREE:
                    self._draw_tree(surface, sx, sy)
                elif tile.type == TILE_ROCK:
                    self._draw_rock(surface, sx, sy)
                elif tile.type == TILE_WALL:
                    pygame.draw.rect(surface, (70, 62, 55), rect, 2)
                elif tile.type == TILE_WATER:
                    self._draw_water(surface, sx, sy)
                elif tile.type == TILE_GRASS or tile.type == TILE_DARK_GRASS:
                    # Subtle grass detail
                    if (r + c) % 3 == 0:
                        pygame.draw.line(surface, tile.get_detail_color(),
                                         (sx + 12, sy + 20), (sx + 12, sy + 28), 1)
                        pygame.draw.line(surface, tile.get_detail_color(),
                                         (sx + 28, sy + 14), (sx + 28, sy + 22), 1)

    def _draw_tree(self, surface, sx, sy):
        # Trunk
        pygame.draw.rect(surface, (80, 50, 20),
                         (sx + 18, sy + 28, 12, 18))
        # Canopy
        pygame.draw.circle(surface, (20, 100, 20),
                            (sx + 24, sy + 22), 18)
        pygame.draw.circle(surface, (30, 130, 30),
                            (sx + 24, sy + 18), 13)

    def _draw_rock(self, surface, sx, sy):
        pygame.draw.ellipse(surface, (90, 85, 80),
                             (sx + 6, sy + 12, 36, 26))
        pygame.draw.ellipse(surface, (120, 115, 110),
                             (sx + 10, sy + 14, 18, 12))

    def _draw_water(self, surface, sx, sy):
        tick = pygame.time.get_ticks() // 600
        ripple_color = (50, 110, 190)
        offset = tick % 2
        for i in range(2):
            pygame.draw.line(surface, ripple_color,
                              (sx + 8 + offset * 4, sy + 16 + i * 14),
                              (sx + 38 + offset * 4, sy + 16 + i * 14), 2)
