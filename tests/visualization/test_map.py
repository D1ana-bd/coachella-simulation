import pytest
import math
import pygame
from unittest.mock import MagicMock
from src.coachella.visualization.map import FestivalMap
from src.coachella.simulation.environment import FestivalEnvironment
from src.coachella.simulation.agents import AgentType, create_agent
from src.coachella.config import STAGES, COLORS
import numpy as np
import random


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
    pygame.init()
    s = pygame.Surface((900, 600))
    yield s
    pygame.quit()


@pytest.fixture
def agent_general(festival):
    rng = random.Random(1)
    np_rng = np.random.default_rng(1)
    a = create_agent(rng, np_rng)
    a.agent_type = AgentType.GENERAL
    return a


@pytest.fixture
def agent_fan(festival):
    rng = random.Random(2)
    np_rng = np.random.default_rng(2)
    a = create_agent(rng, np_rng)
    a.agent_type = AgentType.FAN
    return a


@pytest.fixture
def agent_vip(festival):
    rng = random.Random(3)
    np_rng = np.random.default_rng(3)
    a = create_agent(rng, np_rng)
    a.agent_type = AgentType.VIP
    return a


# ─────────────────────────────────────────────
# TESTES: Construção do grafo
# ─────────────────────────────────────────────

def test_graph_has_correct_number_of_nodes(festival_map):
    assert festival_map.graph.number_of_nodes() == len(STAGES)


def test_graph_nodes_match_stage_names(festival_map):
    assert set(festival_map.graph.nodes) == set(STAGES.keys())


def test_graph_is_complete(festival_map):
    n = len(STAGES)
    expected_edges = n * (n - 1) // 2
    assert festival_map.graph.number_of_edges() == expected_edges


def test_graph_edges_have_weight(festival_map):
    for _, _, data in festival_map.graph.edges(data=True):
        assert "weight" in data
        assert data["weight"] > 0


def test_graph_nodes_have_position_attributes(festival_map):
    for name, data in festival_map.graph.nodes(data=True):
        assert "x" in data
        assert "y" in data


def test_graph_nodes_have_capacity(festival_map):
    for name, data in festival_map.graph.nodes(data=True):
        assert "capacity" in data
        assert data["capacity"] == STAGES[name]["capacity"]


def test_graph_nodes_have_popularity(festival_map):
    for name, data in festival_map.graph.nodes(data=True):
        assert "popularity" in data


# ─────────────────────────────────────────────
# TESTES: Distâncias
# ─────────────────────────────────────────────

def test_distance_is_symmetric(festival_map):
    stages = list(STAGES.keys())
    a, b = stages[0], stages[1]
    assert festival_map.distance(a, b) == festival_map.distance(b, a)


def test_distance_is_positive(festival_map):
    stages = list(STAGES.keys())
    for i in range(len(stages)):
        for j in range(i + 1, len(stages)):
            assert festival_map.distance(stages[i], stages[j]) > 0


def test_distance_matches_euclidean(festival_map):
    stages = list(STAGES.keys())
    a, b = stages[0], stages[1]
    xa, ya = STAGES[a]["x"], STAGES[a]["y"]
    xb, yb = STAGES[b]["x"], STAGES[b]["y"]
    expected = math.sqrt((xb - xa) ** 2 + (yb - ya) ** 2)
    assert abs(festival_map.distance(a, b) - expected) < 0.01


def test_all_distances_returns_correct_count(festival_map):
    n = len(STAGES)
    assert len(festival_map.all_distances()) == n * (n - 1) // 2


def test_all_distances_values_are_positive(festival_map):
    for dist in festival_map.all_distances().values():
        assert dist > 0


# ─────────────────────────────────────────────
# TESTES: nearest_stage
# ─────────────────────────────────────────────

def test_nearest_stage_returns_a_stage(festival_map):
    result = festival_map.nearest_stage(list(STAGES.keys())[0])
    assert result in STAGES


def test_nearest_stage_not_self(festival_map):
    for name in STAGES:
        assert festival_map.nearest_stage(name) != name


def test_nearest_stage_respects_exclude(festival_map):
    stages = list(STAGES.keys())
    exclude = [stages[1]]
    result = festival_map.nearest_stage(stages[0], exclude=exclude)
    assert result not in exclude


def test_nearest_stage_returns_none_when_all_excluded(festival_map):
    stages = list(STAGES.keys())
    from_stage = stages[0]
    exclude = [s for s in stages if s != from_stage]
    assert festival_map.nearest_stage(from_stage, exclude=exclude) is None


# ─────────────────────────────────────────────
# TESTES: shortest_path
# ─────────────────────────────────────────────

def test_shortest_path_includes_endpoints(festival_map):
    stages = list(STAGES.keys())
    a, b = stages[0], stages[2]
    path = festival_map.shortest_path(a, b)
    assert path[0] == a and path[-1] == b


def test_shortest_path_same_stage(festival_map):
    name = list(STAGES.keys())[0]
    assert festival_map.shortest_path(name, name) == [name]


def test_shortest_path_valid_nodes(festival_map):
    stages = list(STAGES.keys())
    path = festival_map.shortest_path(stages[0], stages[-1])
    for node in path:
        assert node in STAGES


# ─────────────────────────────────────────────
# TESTES: stage_position
# ─────────────────────────────────────────────

def test_stage_position_returns_tuple(festival_map):
    pos = festival_map.stage_position(list(STAGES.keys())[0])
    assert isinstance(pos, tuple) and len(pos) == 2


def test_stage_position_matches_config(festival_map):
    for name, cfg in STAGES.items():
        x, y = festival_map.stage_position(name)
        assert x == cfg["x"] and y == cfg["y"]


# ─────────────────────────────────────────────
# TESTES: Rendering — sem exceções
# ─────────────────────────────────────────────

def test_draw_does_not_raise(festival_map, surface):
    try:
        festival_map.draw(surface)
    except Exception as e:
        pytest.fail(f"draw() lançou exceção: {e}")


def test_draw_with_festival_does_not_raise(festival_map, surface, festival):
    try:
        festival_map.draw(surface, festival=festival)
    except Exception as e:
        pytest.fail(f"draw() com festival lançou exceção: {e}")


def test_draw_modifies_surface(festival_map, surface):
    surface.fill((0, 0, 0))
    festival_map.draw(surface)
    pixels = pygame.surfarray.array3d(surface)
    assert pixels.max() > 0


# ─────────────────────────────────────────────
# TESTES: Rendering — agentes por perfil
# ─────────────────────────────────────────────

def test_draw_with_general_agent_does_not_raise(festival_map, surface, festival, agent_general):
    agent_general.status = "watching"
    festival.active_agents.append(agent_general)
    try:
        festival_map.draw(surface, festival=festival)
    except Exception as e:
        pytest.fail(f"draw() com agente GENERAL lançou exceção: {e}")


def test_draw_with_fan_agent_does_not_raise(festival_map, surface, festival, agent_fan):
    agent_fan.status = "queuing"
    festival.active_agents.append(agent_fan)
    try:
        festival_map.draw(surface, festival=festival)
    except Exception as e:
        pytest.fail(f"draw() com agente FAN lançou exceção: {e}")


def test_draw_with_vip_agent_does_not_raise(festival_map, surface, festival, agent_vip):
    agent_vip.status = "moving"
    festival.active_agents.append(agent_vip)
    try:
        festival_map.draw(surface, festival=festival)
    except Exception as e:
        pytest.fail(f"draw() com agente VIP lançou exceção: {e}")


def test_draw_with_all_statuses_does_not_raise(festival_map, surface, festival):
    """Todos os statuses possíveis devem renderizar sem erros."""
    rng = random.Random(99)
    np_rng = np.random.default_rng(99)
    statuses = ["moving", "waiting_show", "queuing", "watching"]
    for i, status in enumerate(statuses):
        a = create_agent(rng, np_rng)
        a.status = status
        festival.active_agents.append(a)
    try:
        festival_map.draw(surface, festival=festival)
    except Exception as e:
        pytest.fail(f"draw() com status '{status}' lançou exceção: {e}")


def test_draw_artist_label_during_show(festival_map, surface, festival):
    """Durante um show, deve renderizar sem erros (artista visível no palco)."""
    festival.env._now = 65  # Becky G a tocar no Main Stage
    try:
        festival_map.draw(surface, festival=festival)
    except Exception as e:
        pytest.fail(f"draw() durante show lançou exceção: {e}")


def test_draw_no_artist_label_outside_show(festival_map, surface, festival):
    """Fora de um show, deve renderizar sem erros."""
    festival.env._now = 0  # Main Stage sem show
    try:
        festival_map.draw(surface, festival=festival)
    except Exception as e:
        pytest.fail(f"draw() fora de show lançou exceção: {e}")