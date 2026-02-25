"""
visualization/map.py - Mapa do festival como grafo NetworkX + rendering Pygame
O grafo representa os palcos como nós e as distâncias entre eles como arestas.
Usa pygame.gfxdraw para rendering com anti-aliasing.
"""

import math
import networkx as nx
import pygame
import pygame.gfxdraw
from src.coachella.utils.logger import get_logger
from src.coachella.config import (
    STAGES, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT,
    STAGE_RADIUS, AGENT_RADIUS,
)

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# HELPERS DE RENDERING COM AA
# ─────────────────────────────────────────────

def draw_aacircle(surface: pygame.Surface, x: int, y: int, r: int, color: tuple):
    """Círculo preenchido com anti-aliasing."""
    pygame.gfxdraw.aacircle(surface, x, y, r, color)
    pygame.gfxdraw.filled_circle(surface, x, y, r, color)


def draw_aaline(surface: pygame.Surface, x1: int, y1: int, x2: int, y2: int,
                color: tuple, thickness: int = 1):
    """Linha com anti-aliasing e espessura configurável."""
    pygame.gfxdraw.line(surface, x1, y1, x2, y2, color)
    for i in range(1, thickness):
        pygame.gfxdraw.line(surface, x1, y1 + i, x2, y2 + i, color)
        pygame.gfxdraw.line(surface, x1, y1 - i, x2, y2 - i, color)


# ─────────────────────────────────────────────
# GRAFO DO FESTIVAL
# ─────────────────────────────────────────────

class FestivalMap:
    """
    Representa o layout do festival como um grafo não-dirigido.

    Nós:     palcos (com atributos de posição, capacidade, popularidade)
    Arestas: ligações entre palcos, pesadas pela distância euclidiana
    """

    def __init__(self):
        self.graph = nx.Graph()
        self._build_graph()
        self._max_dist = max(d["weight"] for _, _, d in self.graph.edges(data=True))
        logger.info("FestivalMap inicializado com %d nós e %d arestas.",
                    self.graph.number_of_nodes(), self.graph.number_of_edges())

    def _build_graph(self):
        """Constrói o grafo a partir do config: adiciona nós e arestas."""
        for name, cfg in STAGES.items():
            self.graph.add_node(name, **cfg)
            logger.debug("Nó adicionado: %s %s", name, cfg)

        stage_names = list(STAGES.keys())
        for i in range(len(stage_names)):
            for j in range(i + 1, len(stage_names)):
                a, b = stage_names[i], stage_names[j]
                dist = self._euclidean_distance(a, b)
                self.graph.add_edge(a, b, weight=dist)
                logger.debug("Aresta: %s ↔ %s | distância: %.1f", a, b, dist)

    def _euclidean_distance(self, stage_a: str, stage_b: str) -> float:
        """Calcula a distância euclidiana entre dois palcos com base nas posições x/y."""
        xa, ya = STAGES[stage_a]["x"], STAGES[stage_a]["y"]
        xb, yb = STAGES[stage_b]["x"], STAGES[stage_b]["y"]
        return math.sqrt((xb - xa) ** 2 + (yb - ya) ** 2)

    # ── Queries úteis ────────────────────────────────────────────────

    def distance(self, stage_a: str, stage_b: str) -> float:
        """Retorna a distância (peso da aresta) entre dois palcos."""
        return self.graph[stage_a][stage_b]["weight"]

    def nearest_stage(self, from_stage: str, exclude: list[str] = None) -> str | None:
        """Retorna o palco mais próximo, excluindo opcionalmente alguns palcos."""
        neighbors = [
            (neighbor, data["weight"])
            for neighbor, data in self.graph[from_stage].items()
            if exclude is None or neighbor not in exclude
        ]
        if not neighbors:
            return None
        return min(neighbors, key=lambda x: x[1])[0]

    def shortest_path(self, from_stage: str, to_stage: str) -> list[str]:
        """Retorna o caminho mais curto entre dois palcos (via Dijkstra)."""
        return nx.shortest_path(self.graph, from_stage, to_stage, weight="weight")

    def all_distances(self) -> dict:
        """Retorna um dicionário com todas as distâncias entre pares de palcos."""
        return {
            (a, b): round(data["weight"], 2)
            for a, b, data in self.graph.edges(data=True)
        }

    def stage_position(self, stage_name: str) -> tuple[int, int]:
        """Retorna a posição (x, y) de um palco."""
        node = self.graph.nodes[stage_name]
        return node["x"], node["y"]

    # ── Rendering Pygame ─────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, festival=None):
        """Renderiza o mapa completo do festival na surface Pygame."""
        self._draw_edges(surface)
        self._draw_stages(surface, festival)
        if festival is not None:
            self._draw_agents(surface, festival)

    def _draw_edges(self, surface: pygame.Surface):
        """Desenha as arestas com anti-aliasing e espessura proporcional."""
        font = pygame.font.SysFont("monospace", 11)

        for a, b, data in self.graph.edges(data=True):
            x1, y1 = self.stage_position(a)
            x2, y2 = self.stage_position(b)
            dist = data["weight"]
            thickness = max(1, int(3 * (1 - dist / self._max_dist)))

            draw_aaline(surface, x1, y1, x2, y2, COLORS["grid"], thickness)

            mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
            label = font.render(f"{dist:.0f}m", True, COLORS["grid"])
            surface.blit(label, (mid_x - label.get_width() // 2, mid_y - 8))

    def _draw_stages(self, surface: pygame.Surface, festival=None):
        """Desenha cada palco como um círculo AA com label e borda."""
        font_name = pygame.font.SysFont("monospace", 13, bold=True)
        font_info = pygame.font.SysFont("monospace", 11)

        for name in self.graph.nodes:
            x, y = self.stage_position(name)

            color = COLORS["stage"]
            occupancy_text = ""
            if festival is not None:
                stage_obj = festival.stages.get(name)
                if stage_obj:
                    ratio = stage_obj.occupancy / stage_obj.capacity
                    if ratio >= 1.0:
                        color = COLORS["stage_full"]
                    elif ratio >= 0.7:
                        color = (255, 165, 0)
                    occupancy_text = f"{stage_obj.occupancy}/{stage_obj.capacity}"

            # Círculo preenchido AA
            draw_aacircle(surface, x, y, STAGE_RADIUS, color)
            # Borda AA (dupla para ficar mais visível)
            pygame.gfxdraw.aacircle(surface, x, y, STAGE_RADIUS, COLORS["text"])
            pygame.gfxdraw.aacircle(surface, x, y, STAGE_RADIUS + 1, COLORS["text"])

            label = font_name.render(name, True, COLORS["text"])
            surface.blit(label, (x - label.get_width() // 2, y - STAGE_RADIUS - 20))

            if occupancy_text:
                info = font_info.render(occupancy_text, True, COLORS["text"])
                surface.blit(info, (x - info.get_width() // 2, y - info.get_height() // 2))

    def _draw_agents(self, surface: pygame.Surface, festival):
        """Desenha os agentes ativos usando a posição real (x, y) do agente."""
        for agent in festival.active_agents:
            if agent.status == "moving":
                color = (180, 180, 255)     # azul claro — em movimento
            elif agent.status == "waiting_show":
                color = (200, 200, 200)     # cinzento — à espera do show
            elif agent.status == "queuing":
                color = COLORS["queue"]     # amarelo — na fila
            elif agent.status == "watching":
                color = COLORS["agent"]     # verde — a ver o show
            else:
                continue

            ax = int(agent.x)
            ay = int(agent.y)

            if agent.status in ("queuing", "watching", "waiting_show"):
                ax += ((agent.id * 7) % (STAGE_RADIUS * 2)) - STAGE_RADIUS
                ay += ((agent.id * 13) % (STAGE_RADIUS * 2)) - STAGE_RADIUS

            draw_aacircle(surface, ax, ay, AGENT_RADIUS, color)