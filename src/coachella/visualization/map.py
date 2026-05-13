"""
visualization/map.py - Mapa do festival com MAP.png como fundo + sprites pixel art
"""

import math
import os
import networkx as nx
import pygame
import pygame.gfxdraw
from src.coachella.utils.logger import get_logger
from src.coachella.config import (
    STAGES, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT,
    STAGE_RADIUS, AGENT_RADIUS,
)
from src.coachella.data.lineup import get_active_show

logger = get_logger(__name__)

# Path dos assets
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

HUD_WIDTH = 280
MAP_WIDTH  = WINDOW_WIDTH - HUD_WIDTH
MAP_HEIGHT = WINDOW_HEIGHT

# Tamanho dos sprites no ecrã
SPRITE_SIZE = 26  # pixels — pequeno mas reconhecível


def draw_aacircle(surface, x, y, r, color):
    pygame.gfxdraw.aacircle(surface, x, y, r, color)
    pygame.gfxdraw.filled_circle(surface, x, y, r, color)


class FestivalMap:
    def __init__(self):
        self.graph = nx.Graph()
        self._build_graph()
        self._max_dist = max(d["weight"] for _, _, d in self.graph.edges(data=True))

        # ── Carregar fundo ───────────────────────────────────────────
        map_path = os.path.join(ASSETS_DIR, "MAP.png")
        try:
            raw = pygame.image.load(map_path).convert()
            self.bg = pygame.transform.scale(raw, (MAP_WIDTH, MAP_HEIGHT))
            logger.info("MAP.png carregado e escalado para %dx%d", MAP_WIDTH, MAP_HEIGHT)
        except Exception as e:
            logger.warning("Não foi possível carregar MAP.png: %s", e)
            self.bg = None

        # ── Carregar sprites ─────────────────────────────────────────
        self.sprites = {}
        sprite_files = {
            "general": "stripe_geral.png",
            "fan":     "stripe_FAN.png",
            "vip":     "stripe_VIP.png",
        }
        for key, fname in sprite_files.items():
            path = os.path.join(ASSETS_DIR, fname)
            try:
                img = pygame.image.load(path).convert_alpha()
                # Remover fundo preto (transparência)
                img.set_colorkey((0, 0, 0))
                self.sprites[key] = pygame.transform.scale(img, (SPRITE_SIZE, SPRITE_SIZE))
                logger.info("Sprite '%s' carregado.", key)
            except Exception as e:
                logger.warning("Não foi possível carregar sprite '%s': %s", key, e)
                self.sprites[key] = None

        logger.info("FestivalMap inicializado com %d nós.", self.graph.number_of_nodes())

    def _build_graph(self):
        for name, cfg in STAGES.items():
            self.graph.add_node(name, **cfg)
        stage_names = list(STAGES.keys())
        for i in range(len(stage_names)):
            for j in range(i + 1, len(stage_names)):
                a, b = stage_names[i], stage_names[j]
                dist = self._euclidean_distance(a, b)
                self.graph.add_edge(a, b, weight=dist)

    def _euclidean_distance(self, stage_a, stage_b):
        xa, ya = STAGES[stage_a]["x"], STAGES[stage_a]["y"]
        xb, yb = STAGES[stage_b]["x"], STAGES[stage_b]["y"]
        return math.sqrt((xb - xa) ** 2 + (yb - ya) ** 2)

    def distance(self, stage_a, stage_b):
        return self.graph[stage_a][stage_b]["weight"]

    def nearest_stage(self, from_stage, exclude=None):
        neighbors = [
            (n, d["weight"]) for n, d in self.graph[from_stage].items()
            if exclude is None or n not in exclude
        ]
        return min(neighbors, key=lambda x: x[1])[0] if neighbors else None

    def shortest_path(self, from_stage, to_stage):
        return nx.shortest_path(self.graph, from_stage, to_stage, weight="weight")

    def stage_position(self, stage_name):
        node = self.graph.nodes[stage_name]
        return node["x"], node["y"]

    def draw(self, surface, festival=None):
        # ── Fundo ────────────────────────────────────────────────────
        if self.bg:
            surface.blit(self.bg, (0, 0))
        else:
            surface.fill(COLORS["background"])

        # ── Labels e indicadores dos palcos ──────────────────────────
        self._draw_stage_indicators(surface, festival)

        # ── Agentes ──────────────────────────────────────────────────
        if festival is not None:
            self._draw_agents(surface, festival)

    def _draw_stage_indicators(self, surface, festival=None):
        """
        Overlay minimalista sobre o mapa:
        - Barra de ocupação pequena por baixo do nome
        - Artista atual a tocar
        Sem círculos — o mapa já tem os palcos desenhados.
        """
        font_name   = pygame.font.SysFont("monospace", 10, bold=True)
        font_artist = pygame.font.SysFont("monospace", 9)

        for name in self.graph.nodes:
            x, y = self.stage_position(name)

            # ── Caixa semitransparente de fundo ───────────────────────
            label_surf = font_name.render(name, True, (255, 255, 255))
            box_w = max(label_surf.get_width() + 8, 60)
            box_h = 14
            box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            box.fill((0, 0, 0, 140))
            surface.blit(box, (x - box_w // 2, y - STAGE_RADIUS - 18))
            surface.blit(label_surf, (x - label_surf.get_width() // 2, y - STAGE_RADIUS - 17))

            if festival is not None:
                stage_obj = festival.stages.get(name)
                if stage_obj:
                    ratio = min(stage_obj.occupancy / stage_obj.capacity, 1.0)

                    # Barra de ocupação
                    bar_w = 50
                    bar_x = x - bar_w // 2
                    bar_y = y - STAGE_RADIUS - 4
                    pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, 5), border_radius=2)
                    fill_color = (
                        (220, 60, 60) if ratio >= 1.0 else
                        (255, 165, 0) if ratio >= 0.7 else
                        (80, 200, 120)
                    )
                    pygame.draw.rect(surface, fill_color,
                                     (bar_x, bar_y, int(bar_w * ratio), 5), border_radius=2)

                # Artista a tocar
                active = get_active_show(name, festival.env.now)
                if active:
                    artist_surf = font_artist.render(
                        f"♪ {active['artist'][:16]}", True, (255, 215, 0)
                    )
                    bg2 = pygame.Surface((artist_surf.get_width() + 6, 13), pygame.SRCALPHA)
                    bg2.fill((0, 0, 0, 120))
                    surface.blit(bg2, (x - artist_surf.get_width() // 2 - 3,
                                       y + STAGE_RADIUS + 2))
                    surface.blit(artist_surf, (x - artist_surf.get_width() // 2,
                                               y + STAGE_RADIUS + 3))

    def _draw_agents(self, surface, festival):
        from src.coachella.simulation.agents import AgentType

        sprite_keys = {
            AgentType.GENERAL: "general",
            AgentType.FAN:     "fan",
            AgentType.VIP:     "vip",
        }
        fallback_colors = {
            AgentType.GENERAL: COLORS["agent_general"],
            AgentType.FAN:     COLORS["agent_fan"],
            AgentType.VIP:     COLORS["agent_vip"],
        }

        for agent in festival.active_agents:
            if agent.status not in ("moving", "waiting_show", "queuing", "watching"):
                continue

            ax = int(agent.x)
            ay = int(agent.y)

            # Dispersão visual quando está num palco
            if agent.status in ("queuing", "watching", "waiting_show"):
                ax += ((agent.id * 7) % (STAGE_RADIUS * 2)) - STAGE_RADIUS
                ay += ((agent.id * 13) % (STAGE_RADIUS * 2)) - STAGE_RADIUS

            key = sprite_keys.get(agent.agent_type)
            sprite = self.sprites.get(key) if key else None

            if sprite:
                # Centrar o sprite na posição do agente
                surface.blit(sprite, (ax - SPRITE_SIZE // 2, ay - SPRITE_SIZE // 2))
            else:
                # Fallback: círculo colorido
                color = fallback_colors.get(agent.agent_type, COLORS["agent"])
                draw_aacircle(surface, ax, ay, AGENT_RADIUS, color)