"""
visualization/map.py - Mapa do festival como grafo NetworkX + rendering Pygame
O grafo representa os palcos como nós e as distâncias entre eles como arestas.
"""

import math
import networkx as nx
import pygame
from src.coachella.utils.logger import get_logger
from src.coachella.config import (
    STAGES, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT,
    STAGE_RADIUS, AGENT_RADIUS,
)

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# GRAFO DO FESTIVAL
# ─────────────────────────────────────────────

class FestivalMap:
    """
    Representa o layout do festival como um grafo não-dirigido.

    Nós:   palcos (com atributos de posição, capacidade, popularidade)
    Arestas: ligações entre palcos, pesadas pela distância euclidiana
    """

    def __init__(self):
        self.graph = nx.Graph()
        self._build_graph()
        logger.info("FestivalMap inicializado com %d nós e %d arestas.",
                    self.graph.number_of_nodes(), self.graph.number_of_edges())

    def _build_graph(self):
        """Constrói o grafo a partir do config: adiciona nós e arestas."""
        # Adicionar nós (palcos)
        for name, cfg in STAGES.items():
            self.graph.add_node(name, **cfg)
            logger.debug("Nó adicionado: %s %s", name, cfg)

        # Adicionar arestas entre todos os pares de palcos (grafo completo)
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
        """
        Retorna o palco mais próximo de `from_stage`.
        Opcionalmente exclui palcos da lista `exclude`.
        """
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
        """
        Renderiza o mapa do festival na surface Pygame.

        Desenha:
          - Arestas (ligações entre palcos) com peso visual
          - Nós (palcos) com cor baseada na ocupação
          - Labels com nome e ocupação atual
          - Agentes ativos (se festival fornecido)
        """
        self._draw_edges(surface)
        self._draw_stages(surface, festival)
        if festival is not None:
            self._draw_agents(surface, festival)

    def _draw_edges(self, surface: pygame.Surface):
        """Desenha as arestas do grafo com espessura proporcional à distância inversa."""
        for a, b, data in self.graph.edges(data=True):
            x1, y1 = self.stage_position(a)
            x2, y2 = self.stage_position(b)
            dist = data["weight"]

            # Linhas mais grossas = palcos mais próximos
            max_dist = max(d["weight"] for _, _, d in self.graph.edges(data=True))
            thickness = max(1, int(3 * (1 - dist / max_dist)))

            pygame.draw.line(surface, COLORS["grid"], (x1, y1), (x2, y2), thickness)

            # Label da distância no meio da aresta
            mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
            font = pygame.font.SysFont("monospace", 11)
            label = font.render(f"{dist:.0f}m", True, COLORS["grid"])
            surface.blit(label, (mid_x - label.get_width() // 2, mid_y - 8))

    def _draw_stages(self, surface: pygame.Surface, festival=None):
        """Desenha cada palco como um círculo colorido com label."""
        font_name = pygame.font.SysFont("monospace", 13, bold=True)
        font_info = pygame.font.SysFont("monospace", 11)

        for name in self.graph.nodes:
            x, y = self.stage_position(name)

            # Cor baseada na ocupação (se festival disponível)
            color = COLORS["stage"]
            occupancy_text = ""
            if festival is not None:
                stage_obj = festival.stages.get(name)
                if stage_obj:
                    ratio = stage_obj.occupancy / stage_obj.capacity
                    if ratio >= 1.0:
                        color = COLORS["stage_full"]
                    elif ratio >= 0.7:
                        color = (255, 165, 0)  # laranja — quase cheio
                    occupancy_text = f"{stage_obj.occupancy}/{stage_obj.capacity}"

            # Círculo do palco
            pygame.draw.circle(surface, color, (x, y), STAGE_RADIUS)
            pygame.draw.circle(surface, COLORS["text"], (x, y), STAGE_RADIUS, 2)  # borda

            # Nome do palco
            label = font_name.render(name, True, COLORS["text"])
            surface.blit(label, (x - label.get_width() // 2, y - STAGE_RADIUS - 20))

            # Ocupação
            if occupancy_text:
                info = font_info.render(occupancy_text, True, COLORS["text"])
                surface.blit(info, (x - info.get_width() // 2, y - info.get_height() // 2))

    def _draw_agents(self, surface: pygame.Surface, festival):
        """Desenha os agentes ativos como pequenos círculos no palco onde estão."""
        for agent in festival.active_agents:
            if agent.current_stage is None:
                continue

            x, y = self.stage_position(agent.current_stage)

            # Cor por status
            if agent.status == "queuing":
                color = COLORS["queue"]
            elif agent.status == "watching":
                color = COLORS["agent"]
            else:
                continue  # não desenha agentes a sair

            # Offset aleatório mas determinístico (baseado no id) para não sobrepor
            offset_x = ((agent.id * 7) % (STAGE_RADIUS * 2)) - STAGE_RADIUS
            offset_y = ((agent.id * 13) % (STAGE_RADIUS * 2)) - STAGE_RADIUS

            pygame.draw.circle(surface, color,
                               (x + offset_x, y + offset_y),
                               AGENT_RADIUS)