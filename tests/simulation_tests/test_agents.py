"""
tests/simulation_tests/test_agents.py - Testes para simulation/agents.py
"""

import pytest
import random
import numpy as np

from src.coachella.simulation.agents import (
    Agent,
    AgentType,
    AgentProfile,
    PROFILES,
    create_agent,
)
from src.coachella.data.lineup import get_artist_names


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_agent_counter():
    """Reseta o contador de IDs antes de cada teste."""
    Agent.reset_counter()


@pytest.fixture
def rngs():
    rng    = random.Random(42)
    np_rng = np.random.default_rng(42)
    return rng, np_rng


@pytest.fixture
def agent(rngs):
    rng, np_rng = rngs
    return Agent(rng, np_rng)


# ─────────────────────────────────────────────
# PERFIS
# ─────────────────────────────────────────────

def test_profiles_exist():
    assert AgentType.GENERAL in PROFILES
    assert AgentType.FAN in PROFILES
    assert AgentType.VIP in PROFILES


def test_proportions_sum_to_one():
    total = sum(p.proportion for p in PROFILES.values())
    assert abs(total - 1.0) < 1e-9


def test_all_profiles_have_positive_patience():
    for profile in PROFILES.values():
        assert profile.patience_mean > 0
        assert profile.patience_std > 0


# ─────────────────────────────────────────────
# CRIAÇÃO DO AGENTE
# ─────────────────────────────────────────────

def test_agent_has_valid_id(agent):
    assert agent.id == 1


def test_agent_ids_increment():
    rng    = random.Random(1)
    np_rng = np.random.default_rng(1)
    a1 = Agent(rng, np_rng)
    a2 = Agent(rng, np_rng)
    assert a2.id == a1.id + 1


def test_agent_has_valid_type(agent):
    assert agent.agent_type in AgentType


def test_agent_patience_positive(agent):
    assert agent.patience >= 1.0


def test_agent_watch_duration_positive(agent):
    assert agent.watch_duration >= 5.0


def test_agent_has_favorite_artists(agent):
    assert len(agent.favorite_artists) >= 1
    all_artists = get_artist_names()
    for fav in agent.favorite_artists:
        assert fav in all_artists


def test_agent_num_favorites_matches_profile(agent):
    expected = agent.profile.num_favorites
    assert len(agent.favorite_artists) == expected


def test_agent_initial_status(agent):
    assert agent.status == "arriving"


def test_agent_initial_position(agent):
    from src.coachella.config import FESTIVAL_ENTRANCE
    assert agent.x == float(FESTIVAL_ENTRANCE["x"])
    assert agent.y == float(FESTIVAL_ENTRANCE["y"])


def test_agent_leaves_early_is_bool(agent):
    assert isinstance(agent.leaves_early, bool)


# ─────────────────────────────────────────────
# LÓGICA DE FAVORITOS
# ─────────────────────────────────────────────

def test_is_favorite_true(agent):
    fav = agent.favorite_artists[0]
    assert agent.is_favorite(fav) is True


def test_is_favorite_false(agent):
    # artista que de certeza não está nos favoritos
    non_fav = next(a for a in get_artist_names() if a not in agent.favorite_artists)
    assert agent.is_favorite(non_fav) is False


def test_record_favorite_seen(agent):
    fav = agent.favorite_artists[0]
    agent.record_favorite_seen(fav)
    assert fav in agent.favorites_seen


def test_record_favorite_seen_no_duplicate(agent):
    fav = agent.favorite_artists[0]
    agent.record_favorite_seen(fav)
    agent.record_favorite_seen(fav)
    assert agent.favorites_seen.count(fav) == 1


def test_record_non_favorite_not_recorded(agent):
    non_fav = next(a for a in get_artist_names() if a not in agent.favorite_artists)
    agent.record_favorite_seen(non_fav)
    assert non_fav not in agent.favorites_seen


# ─────────────────────────────────────────────
# PACIÊNCIA POR ARTISTA
# ─────────────────────────────────────────────

def test_get_patience_for_returns_positive(agent):
    rng, np_rng = random.Random(0), np.random.default_rng(0)
    patience = agent.get_patience_for(agent.favorite_artists[0], np_rng)
    assert patience >= 1.0


def test_fan_gets_higher_patience_for_favorite():
    """Fã deve ter paciência média maior para favoritos do que para outros."""
    rng    = random.Random(42)
    np_rng = np.random.default_rng(42)

    # Forçar um agente do tipo FAN
    fan_profile = PROFILES[AgentType.FAN]
    agent = Agent(rng, np_rng)
    agent.profile    = fan_profile
    agent.agent_type = AgentType.FAN
    fav = agent.favorite_artists[0]

    samples_fav   = [agent.get_patience_for(fav, np.random.default_rng(i))     for i in range(200)]
    samples_other = [agent.get_patience_for(None, np.random.default_rng(i))    for i in range(200)]

    assert np.mean(samples_fav) > np.mean(samples_other)


def test_vip_patience_lower_than_fan():
    """VIP deve ter paciência média menor que Fã."""
    rng    = random.Random(42)
    np_rng = np.random.default_rng(42)

    assert PROFILES[AgentType.VIP].patience_mean < PROFILES[AgentType.FAN].fan_patience_mean


# ─────────────────────────────────────────────
# FACTORY
# ─────────────────────────────────────────────

def test_create_agent_returns_agent():
    rng    = random.Random(99)
    np_rng = np.random.default_rng(99)
    a = create_agent(rng, np_rng)
    assert isinstance(a, Agent)


def test_population_proportions_roughly_correct():
    """Com 1000 agentes, as proporções devem estar perto de 70/20/10%."""
    rng    = random.Random(42)
    np_rng = np.random.default_rng(42)

    counts = {t: 0 for t in AgentType}
    n = 1000
    for _ in range(n):
        a = create_agent(rng, np_rng)
        counts[a.agent_type] += 1

    assert 0.60 <= counts[AgentType.GENERAL] / n <= 0.80
    assert 0.12 <= counts[AgentType.FAN]     / n <= 0.28
    assert 0.04 <= counts[AgentType.VIP]     / n <= 0.16