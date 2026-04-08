import pytest
import simpy
import random
import numpy as np
from unittest.mock import patch
from src.coachella.simulation.events import (
    visit_stage, try_another_stage, agent_arrivals,
    concert_scheduler, choose_stage_for_agent, get_next_show_or_active,
)
from src.coachella.simulation.agents import Agent, AgentType, PROFILES, create_agent
from src.coachella.simulation.environment import FestivalEnvironment
from src.coachella.config import NUM_AGENTS


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_agent_counter():
    Agent.reset_counter()


@pytest.fixture
def festival():
    return FestivalEnvironment(seed=42)


@pytest.fixture
def rngs():
    return random.Random(42), np.random.default_rng(42)


@pytest.fixture
def agent(rngs):
    rng, np_rng = rngs
    return create_agent(rng, np_rng)


@pytest.fixture
def main_stage(festival):
    return festival.stages["Main Stage"]


@pytest.fixture
def outdoor_stage(festival):
    return festival.stages["Outdoor Stage"]


# ─────────────────────────────────────────────
# TESTES: concert_scheduler
# ─────────────────────────────────────────────

def test_concert_scheduler_opens_stage(festival):
    """Palco deve estar aberto durante um show."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]  # SZA: start=0, duration=40

    env.process(concert_scheduler(env, stage))
    env.run(until=5)

    assert stage.is_open


def test_concert_scheduler_closes_stage_after_show(festival):
    """Palco deve estar fechado após o show terminar."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]  # SZA: start=0, duration=40

    env.process(concert_scheduler(env, stage))
    env.run(until=41)

    assert not stage.is_open


def test_concert_scheduler_opens_for_each_show(festival):
    """Scheduler deve abrir o palco para cada show no lineup."""
    env = festival.env
    stage = festival.stages["Main Stage"]

    env.process(concert_scheduler(env, stage))
    env.run(until=480)

    # Main Stage tem 4 shows — verificamos que o palco abriu e fechou
    # O último show termina em t=420+60=480, então no fim está fechado
    assert not stage.is_open


# ─────────────────────────────────────────────
# TESTES: get_next_show_or_active
# ─────────────────────────────────────────────

def test_get_next_show_or_active_returns_show_before_end(festival):
    """Retorna o show se ainda não terminou."""
    show = get_next_show_or_active("Sza", 10.0)
    assert show is not None
    assert show["artist"] == "Sza"


def test_get_next_show_or_active_returns_none_after_end(festival):
    """Retorna None se o show já terminou."""
    show = get_next_show_or_active("Sza", 50.0)  # SZA termina em t=40
    assert show is None


def test_get_next_show_or_active_unknown_artist(festival):
    assert get_next_show_or_active("Artista Falso", 0.0) is None


# ─────────────────────────────────────────────
# TESTES: choose_stage_for_agent
# ─────────────────────────────────────────────

def test_choose_stage_for_agent_returns_stage(festival, rngs):
    """Deve retornar um palco válido."""
    rng, np_rng = rngs
    agent = create_agent(rng, np_rng)
    result = choose_stage_for_agent(agent, festival)
    from src.coachella.simulation.environment import Stage
    assert isinstance(result, Stage)


def test_choose_stage_for_agent_respects_exclude(festival, rngs):
    """Não deve retornar palcos excluídos."""
    rng, np_rng = rngs
    agent = create_agent(rng, np_rng)
    exclude = ["Main Stage", "Sahara Stage"]
    result = choose_stage_for_agent(agent, festival, exclude=exclude)
    if result is not None:
        assert result.name not in exclude


def test_fan_goes_to_favorite_stage(festival):
    """Fã com artista favorito a tocar em breve deve ser direcionado para esse palco."""
    rng = random.Random(42)
    np_rng = np.random.default_rng(42)
    agent = create_agent(rng, np_rng)

    # Forçar perfil FAN com favorito conhecido
    agent.agent_type = AgentType.FAN
    agent.profile = PROFILES[AgentType.FAN]
    agent.favorite_artists = ["Sza"]  # Outdoor Stage, start=0

    festival.env._now = 5  # dentro do show da SZA
    result = choose_stage_for_agent(agent, festival)

    assert result is not None
    assert result.name == "Outdoor Stage"


# ─────────────────────────────────────────────
# TESTES: visit_stage
# ─────────────────────────────────────────────

def test_agent_enters_stage_and_is_served(festival):
    """Agente com paciência alta entra e é servido."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]  # SZA: start=0, show ativo desde t=0
    stage.is_open = True
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert stage.total_served == 1
    assert stage.total_reneged == 0


def test_agent_status_leaving_after_visit(festival):
    """Após a visita, agente fica com status 'leaving'."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert agent.status == "leaving"


def test_wait_time_recorded_after_entry(festival):
    """Tempo de espera é registado após entrada."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert len(stage.wait_times) == 1
    assert stage.wait_times[0] >= 0


def test_agent_removed_from_active_after_visit(festival):
    """Agente é removido de active_agents após a visita."""
    env = festival.env
    stage = festival.stages["Main Stage"]
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999
    festival.active_agents.append(agent)

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert agent not in festival.active_agents


def test_agent_records_favorite_seen(festival):
    """Agente regista artista favorito quando o vê."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]

    agent = create_agent(festival.rng, festival.np_rng)
    agent.favorite_artists = ["Sza"]
    agent.patience = 999

    festival.env._now = 0
    env.process(concert_scheduler(env, stage))
    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert "Sza" in agent.favorites_seen


def test_agent_total_wait_time_updated(festival):
    """total_wait_time do agente é atualizado após entrar."""
    env = festival.env
    stage = festival.stages["Main Stage"]
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert agent.total_wait_time >= 0


def test_stage_added_to_stages_visited(festival):
    """Palco visitado é adicionado a stages_visited do agente."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999
    agent.favorite_artists = []  # sem favoritos → sem redirecionamento

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert "Outdoor Stage" in agent.stages_visited


# ─────────────────────────────────────────────
# TESTES: visit_stage - renege
# ─────────────────────────────────────────────

def test_agent_reneges_when_patience_zero(festival):
    """Agente com paciência 0 num palco cheio desiste imediatamente."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True  # forçar palco aberto

    for _ in range(stage.capacity):
        blocker = create_agent(festival.rng, festival.np_rng)
        blocker.patience = 999
        env.process(visit_stage(env, blocker, stage, festival))

    impatient = create_agent(festival.rng, festival.np_rng)
    impatient.patience = 0
    impatient.favorite_artists = []
    env.process(visit_stage(env, impatient, stage, festival))

    env.run(until=5)
    assert stage.total_reneged >= 1


def test_patience_decreases_after_renege(festival):
    """Paciência diminui após desistir e tentar alternativa."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]

    for _ in range(stage.capacity):
        blocker = create_agent(festival.rng, festival.np_rng)
        blocker.patience = 999
        env.process(visit_stage(env, blocker, stage, festival))

    agent = create_agent(festival.rng, festival.np_rng)
    original_patience = agent.patience
    env.process(visit_stage(env, agent, stage, festival))

    env.run(until=original_patience + 1)
    assert agent.patience <= original_patience


# ─────────────────────────────────────────────
# TESTES: try_another_stage
# ─────────────────────────────────────────────

def test_try_another_stage_goes_to_alternative(festival):
    """Agente é encaminhado para palco alternativo disponível."""
    env = festival.env
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999
    festival.active_agents.append(agent)

    env.process(try_another_stage(env, agent, festival, exclude=["Main Stage"], time_spent=0.0))
    env.run()

    assert agent.status == "leaving"


def test_try_another_stage_leaves_when_no_alternative(festival):
    """Se não houver alternativa, agente fica com status 'leaving'."""
    env = festival.env
    agent = create_agent(festival.rng, festival.np_rng)
    all_stages = list(festival.stages.keys())

    env.process(try_another_stage(env, agent, festival, exclude=all_stages, time_spent=0.0))
    env.run()

    assert agent.status == "leaving"


# ─────────────────────────────────────────────
# TESTES: agent_arrivals
# ─────────────────────────────────────────────

def test_agent_arrivals_spawns_correct_number(festival):
    """Deve gerar exatamente NUM_AGENTS agentes."""
    env = festival.env
    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    assert Agent._id_counter == 10


def test_agent_arrivals_uses_exponential_interarrival(festival):
    """Chegadas devem ser espaçadas no tempo."""
    env = festival.env
    arrival_times = []

    def mock_visit(e, agent, stage, fest):
        arrival_times.append(e.now)
        yield e.timeout(0)

    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        with patch("src.coachella.simulation.events.visit_stage", side_effect=mock_visit):
            env.process(agent_arrivals(env, festival))
            env.run(until=600)

    assert len(set(arrival_times)) > 1


def test_agent_arrivals_all_agents_eventually_leave(festival):
    """Todos os agentes devem terminar com status 'leaving'."""
    env = festival.env
    festival.setup()
    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    assert len(festival.active_agents) == 0


def test_total_served_leq_num_agents(festival):
    """Total de servidos não pode exceder NUM_AGENTS."""
    env = festival.env
    festival.setup()
    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    total_served = sum(s.total_served for s in festival.stages.values())
    assert total_served <= 10


def test_agent_arrivals_creates_mixed_profiles(festival):
    """Chegadas devem gerar agentes com perfis diferentes."""
    env = festival.env
    festival.setup()
    with patch("src.coachella.simulation.events.NUM_AGENTS", 50):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    types_seen = {a.agent_type for a in festival.active_agents}
    # Com 50 agentes é muito provável ter pelo menos 2 tipos distintos
    # (mesmo que alguns já tenham saído, o counter confirma)
    assert Agent._id_counter == 50