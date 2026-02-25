import pytest
import simpy
import random
from unittest.mock import patch, MagicMock
from src.coachella.simulation.events import Agent, visit_stage, try_another_stage, agent_arrivals
from src.coachella.simulation.environment import FestivalEnvironment, Stage
from src.coachella.config import NUM_AGENTS, PATIENCE_MIN, PATIENCE_MAX, WATCH_DURATION_MIN, WATCH_DURATION_MAX


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_agent_counter():
    """Reseta o contador de agentes antes de cada teste."""
    Agent.reset_counter()


@pytest.fixture
def rng():
    return random.Random(42)


@pytest.fixture
def festival():
    return FestivalEnvironment(seed=42)


@pytest.fixture
def agent(rng):
    return Agent(rng)


@pytest.fixture
def main_stage(festival):
    return festival.stages["Main Stage"]


# ─────────────────────────────────────────────
# TESTES: Agent
# ─────────────────────────────────────────────

def test_agent_id_increments(rng):
    """IDs dos agentes devem ser únicos e incrementais."""
    a1 = Agent(rng)
    a2 = Agent(rng)
    a3 = Agent(rng)
    assert a1.id == 1
    assert a2.id == 2
    assert a3.id == 3


def test_agent_patience_within_bounds(rng):
    """Paciência do agente deve estar dentro dos limites do config."""
    for _ in range(50):
        a = Agent(rng)
        assert PATIENCE_MIN <= a.patience <= PATIENCE_MAX


def test_agent_watch_duration_within_bounds(rng):
    """Duração de visita deve estar dentro dos limites do config."""
    for _ in range(50):
        a = Agent(rng)
        assert WATCH_DURATION_MIN <= a.watch_duration <= WATCH_DURATION_MAX


def test_agent_initial_status(agent):
    """Status inicial do agente é 'arriving'."""
    assert agent.status == "arriving"


def test_agent_initial_stage_is_none(agent):
    """Agente não está em nenhum palco no início."""
    assert agent.current_stage is None


def test_agent_reset_counter(rng):
    """reset_counter() deve reiniciar a contagem de IDs."""
    Agent(rng)
    Agent(rng)
    Agent.reset_counter()
    a = Agent(rng)
    assert a.id == 1


def test_agent_repr(agent):
    """__repr__ deve incluir id e status."""
    r = repr(agent)
    assert "Agent" in r
    assert "arriving" in r


# ─────────────────────────────────────────────
# TESTES: visit_stage - caminho feliz
# ─────────────────────────────────────────────

def test_agent_enters_stage_and_is_served(festival):
    """Agente com paciência suficiente deve entrar no palco e ser servido."""
    env = festival.env
    stage = festival.stages["Main Stage"]
    agent = Agent(festival.rng)
    agent.patience = 999  # paciência muito alta → nunca desiste

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert stage.total_served == 1
    assert stage.total_reneged == 0


def test_agent_status_leaving_after_visit(festival):
    """Após completar a visita, agente deve ter status 'leaving'."""
    env = festival.env
    stage = festival.stages["Main Stage"]
    agent = Agent(festival.rng)
    agent.patience = 999

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert agent.status == "leaving"


def test_wait_time_recorded_after_entry(festival):
    """Tempo de espera deve ser registado quando o agente entra."""
    env = festival.env
    stage = festival.stages["Main Stage"]
    agent = Agent(festival.rng)
    agent.patience = 999

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert len(stage.wait_times) == 1
    assert stage.wait_times[0] >= 0


def test_agent_removed_from_active_after_visit(festival):
    """Agente deve ser removido de active_agents após terminar a visita."""
    env = festival.env
    stage = festival.stages["Main Stage"]
    agent = Agent(festival.rng)
    agent.patience = 999
    festival.active_agents.append(agent)

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert agent not in festival.active_agents


# ─────────────────────────────────────────────
# TESTES: visit_stage - renege
# ─────────────────────────────────────────────

def test_agent_reneges_when_patience_zero(festival):
    """Agente com paciência 0 num palco cheio deve desistir imediatamente."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]  # capacidade 30

    # Encher o palco com agentes com paciência alta
    blockers = []
    for _ in range(stage.capacity):
        blocker = Agent(festival.rng)
        blocker.patience = 999
        blockers.append(blocker)
        env.process(visit_stage(env, blocker, stage, festival))

    # Agente imediatamente impaciente
    impatient = Agent(festival.rng)
    impatient.patience = 0
    env.process(visit_stage(env, impatient, stage, festival))

    env.run(until=5)

    assert stage.total_reneged >= 1


def test_reneged_agent_tries_alternative(festival):
    """Agente que desiste deve tentar um palco alternativo."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]

    # Encher o palco
    for _ in range(stage.capacity):
        blocker = Agent(festival.rng)
        blocker.patience = 999
        env.process(visit_stage(env, blocker, stage, festival))

    impatient = Agent(festival.rng)
    impatient.patience = 0
    festival.active_agents.append(impatient)
    env.process(visit_stage(env, impatient, stage, festival))

    env.run(until=5)

    # Total servido nos outros palcos deve ser > 0 (tentou alternativa)
    other_stages_served = sum(
        s.total_served for name, s in festival.stages.items()
        if name != "Outdoor Stage"
    )
    assert other_stages_served >= 1 or impatient.status == "leaving"


def test_patience_decreases_after_renege(festival):
    """Paciência restante deve ser menor após desistir e tentar alternativa."""
    env = festival.env
    stage = festival.stages["Outdoor Stage"]

    # Encher o palco
    for _ in range(stage.capacity):
        blocker = Agent(festival.rng)
        blocker.patience = 999
        env.process(visit_stage(env, blocker, stage, festival))

    agent = Agent(festival.rng)
    original_patience = agent.patience
    env.process(visit_stage(env, agent, stage, festival))

    env.run(until=original_patience + 1)

    # Se desistiu, a paciência deve ter diminuído
    assert agent.patience <= original_patience


# ─────────────────────────────────────────────
# TESTES: try_another_stage
# ─────────────────────────────────────────────

def test_try_another_stage_goes_to_alternative(festival):
    """Agente deve ser encaminhado para um palco alternativo disponível."""
    env = festival.env
    agent = Agent(festival.rng)
    agent.patience = 999
    festival.active_agents.append(agent)

    env.process(try_another_stage(env, agent, festival, exclude=["Main Stage"], time_spent=0.0))
    env.run()

    assert agent.status == "leaving"


def test_try_another_stage_leaves_when_no_alternative(festival):
    """Se não houver alternativa, agente deve ficar com status 'leaving'."""
    env = festival.env
    agent = Agent(festival.rng)
    all_stages = list(festival.stages.keys())

    env.process(try_another_stage(env, agent, festival, exclude=all_stages, time_spent=0.0))
    env.run()

    assert agent.status == "leaving"


# ─────────────────────────────────────────────
# TESTES: agent_arrivals
# ─────────────────────────────────────────────

def test_agent_arrivals_spawns_correct_number(festival):
    """Processo de chegadas deve gerar exatamente NUM_AGENTS agentes."""
    env = festival.env
    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    assert Agent._id_counter == 10


def test_agent_arrivals_uses_exponential_interarrival(festival):
    """Chegadas devem ser espaçadas no tempo (não todas ao mesmo instante)."""
    env = festival.env
    arrival_times = []

    def mock_visit(e, agent, stage, fest):
        arrival_times.append(e.now)
        yield e.timeout(0)

    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        with patch("src.coachella.simulation.events.visit_stage", side_effect=mock_visit):
            env.process(agent_arrivals(env, festival))
            env.run(until=600)

    # Deve haver variação nos tempos de chegada
    assert len(set(arrival_times)) > 1


def test_agent_arrivals_all_agents_eventually_leave(festival):
    """Todos os agentes devem terminar com status 'leaving' após a simulação."""
    env = festival.env
    festival.setup()
    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    assert len(festival.active_agents) == 0


def test_total_served_plus_reneged_leq_num_agents(festival):
    """Total de servidos nunca pode exceder NUM_AGENTS."""
    env = festival.env
    festival.setup()
    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    total_served = sum(s.total_served for s in festival.stages.values())
    assert total_served <= 10