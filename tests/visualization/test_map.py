import pytest
import math
import pygame
from unittest.mock import MagicMock, patch
from src.coachella.visualization.map import FestivalMap
from src.coachella.simulation.environment import FestivalEnvironment
from src.coachella.config import STAGES


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def festival_map():
    return FestivalMap()


@pytest.fixture
def festival():
    return FestivalEnvironment(seed=42)


@pytest.fixture
def surface():
    """Surface Pygame mínima para testes de rendering."""
    pygame.init()
    s = pygame.Surface((900, 600))
    yield s
    pygame.quit()


# ─────────────────────────────────────────────
# TESTES: Construção do grafo
# ─────────────────────────────────────────────

def test_graph_has_correct_number_of_nodes(festival_map):
    """Grafo deve ter um nó por palco definido no config."""
    assert festival_map.graph.number_of_nodes() == len(STAGES)


def test_graph_nodes_match_stage_names(festival_map):
    """Nós do grafo devem corresponder aos nomes dos palcos no config."""
    assert set(festival_map.graph.nodes) == set(STAGES.keys())


def test_graph_is_complete(festival_map):
    """Grafo deve ser completo — todos os palcos ligados entre si."""
    n = len(STAGES)
    expected_edges = n * (n - 1) // 2
    assert festival_map.graph.number_of_edges() == expected_edges


def test_graph_edges_have_weight(festival_map):
    """Todas as arestas devem ter atributo 'weight'."""
    for _, _, data in festival_map.graph.edges(data=True):
        assert "weight" in data
        assert data["weight"] > 0


def test_graph_nodes_have_position_attributes(festival_map):
    """Todos os nós devem ter atributos x e y."""
    for name, data in festival_map.graph.nodes(data=True):
        assert "x" in data
        assert "y" in data


def test_graph_nodes_have_capacity(festival_map):
    """Todos os nós devem ter atributo capacity."""
    for name, data in festival_map.graph.nodes(data=True):
        assert "capacity" in data
        assert data["capacity"] == STAGES[name]["capacity"]


def test_graph_nodes_have_popularity(festival_map):
    """Todos os nós devem ter atributo popularity."""
    for name, data in festival_map.graph.nodes(data=True):
        assert "popularity" in data


# ─────────────────────────────────────────────
# TESTES: Distâncias
# ─────────────────────────────────────────────

def test_distance_is_symmetric(festival_map):
    """Distância A→B deve ser igual a B→A."""
    stages = list(STAGES.keys())
    a, b = stages[0], stages[1]
    assert festival_map.distance(a, b) == festival_map.distance(b, a)


def test_distance_is_positive(festival_map):
    """Distâncias entre palcos diferentes devem ser positivas."""
    stages = list(STAGES.keys())
    for i in range(len(stages)):
        for j in range(i + 1, len(stages)):
            assert festival_map.distance(stages[i], stages[j]) > 0


def test_distance_matches_euclidean(festival_map):
    """Distância no grafo deve corresponder à distância euclidiana real."""
    stages = list(STAGES.keys())
    a, b = stages[0], stages[1]
    xa, ya = STAGES[a]["x"], STAGES[a]["y"]
    xb, yb = STAGES[b]["x"], STAGES[b]["y"]
    expected = math.sqrt((xb - xa) ** 2 + (yb - ya) ** 2)
    assert abs(festival_map.distance(a, b) - expected) < 0.01


def test_all_distances_returns_correct_count(festival_map):
    """all_distances() deve retornar uma entrada por aresta."""
    n = len(STAGES)
    expected = n * (n - 1) // 2
    assert len(festival_map.all_distances()) == expected


def test_all_distances_values_are_positive(festival_map):
    """Todas as distâncias em all_distances() devem ser positivas."""
    for dist in festival_map.all_distances().values():
        assert dist > 0


# ─────────────────────────────────────────────
# TESTES: nearest_stage
# ─────────────────────────────────────────────

def test_nearest_stage_returns_a_stage(festival_map):
    """nearest_stage() deve retornar um nome de palco válido."""
    stages = list(STAGES.keys())
    result = festival_map.nearest_stage(stages[0])
    assert result in STAGES


def test_nearest_stage_not_self(festival_map):
    """nearest_stage() não deve retornar o próprio palco."""
    for name in STAGES:
        result = festival_map.nearest_stage(name)
        assert result != name


def test_nearest_stage_respects_exclude(festival_map):
    """nearest_stage() não deve retornar palcos excluídos."""
    stages = list(STAGES.keys())
    from_stage = stages[0]
    exclude = [stages[1]]
    result = festival_map.nearest_stage(from_stage, exclude=exclude)
    assert result not in exclude


def test_nearest_stage_returns_none_when_all_excluded(festival_map):
    """nearest_stage() retorna None se todos os outros palcos forem excluídos."""
    stages = list(STAGES.keys())
    from_stage = stages[0]
    exclude = [s for s in stages if s != from_stage]
    result = festival_map.nearest_stage(from_stage, exclude=exclude)
    assert result is None


# ─────────────────────────────────────────────
# TESTES: shortest_path
# ─────────────────────────────────────────────

def test_shortest_path_includes_endpoints(festival_map):
    """Caminho mais curto deve incluir origem e destino."""
    stages = list(STAGES.keys())
    a, b = stages[0], stages[2]
    path = festival_map.shortest_path(a, b)
    assert path[0] == a
    assert path[-1] == b


def test_shortest_path_same_stage(festival_map):
    """Caminho de um palco para si mesmo é só esse palco."""
    name = list(STAGES.keys())[0]
    path = festival_map.shortest_path(name, name)
    assert path == [name]


def test_shortest_path_valid_nodes(festival_map):
    """Todos os nós no caminho devem ser palcos válidos."""
    stages = list(STAGES.keys())
    path = festival_map.shortest_path(stages[0], stages[-1])
    for node in path:
        assert node in STAGES


# ─────────────────────────────────────────────
# TESTES: stage_position
# ─────────────────────────────────────────────

def test_stage_position_returns_tuple(festival_map):
    """stage_position() deve retornar um tuple (x, y)."""
    name = list(STAGES.keys())[0]
    pos = festival_map.stage_position(name)
    assert isinstance(pos, tuple)
    assert len(pos) == 2


def test_stage_position_matches_config(festival_map):
    """Posição retornada deve coincidir com o config."""
    for name, cfg in STAGES.items():
        x, y = festival_map.stage_position(name)
        assert x == cfg["x"]
        assert y == cfg["y"]


# ─────────────────────────────────────────────
# TESTES: Rendering Pygame
# ─────────────────────────────────────────────

def test_draw_does_not_raise(festival_map, surface):
    """draw() não deve lançar exceções com surface válida."""
    try:
        festival_map.draw(surface)
    except Exception as e:
        pytest.fail(f"draw() lançou exceção inesperada: {e}")


def test_draw_with_festival_does_not_raise(festival_map, surface, festival):
    """draw() com festival não deve lançar exceções."""
    try:
        festival_map.draw(surface, festival=festival)
    except Exception as e:
        pytest.fail(f"draw() com festival lançou exceção inesperada: {e}")


def test_draw_with_agents_does_not_raise(festival_map, surface, festival):
    """draw() com agentes ativos não deve lançar exceções."""
    from src.coachella.simulation.events import Agent
    Agent.reset_counter()
    agent = Agent(festival.rng)
    agent.current_stage = "Main Stage"
    agent.status = "watching"
    festival.active_agents.append(agent)

    try:
        festival_map.draw(surface, festival=festival)
    except Exception as e:
        pytest.fail(f"draw() com agentes lançou exceção inesperada: {e}")


def test_draw_modifies_surface(festival_map, surface):
    """draw() deve modificar a surface (não ficar toda preta)."""
    # Preencher de preto
    surface.fill((0, 0, 0))
    festival_map.draw(surface)
    # Verificar que pelo menos um pixel foi alterado
    pixels = pygame.surfarray.array3d(surface)
    assert pixels.max() > 0