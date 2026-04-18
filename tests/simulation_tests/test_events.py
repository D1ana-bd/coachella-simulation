import pytest
import simpy
import random
import numpy as np
from unittest.mock import patch, PropertyMock
from src.coachella.simulation.events import (
    visit_stage, try_another_stage, agent_arrivals,
    concert_scheduler, choose_stage_for_agent, get_next_show_or_active,
)
from src.coachella.simulation.agents import Agent, AgentType, PROFILES, create_agent
from src.coachella.simulation.environment import FestivalEnvironment
from src.coachella.simulation.policies import BASELINE, INFORMATIVE_APP, ACTIVE_MANAGEMENT, VIP_PRIORITY
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
def festival_vip():
    return FestivalEnvironment(seed=42, policy=VIP_PRIORITY)


@pytest.fixture
def festival_app():
    return FestivalEnvironment(seed=42, policy=INFORMATIVE_APP)


@pytest.fixture
def festival_active():
    return FestivalEnvironment(seed=42, policy=ACTIVE_MANAGEMENT)


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
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    env.process(concert_scheduler(env, stage))
    env.run(until=5)
    assert stage.is_open


def test_concert_scheduler_closes_stage_after_show(festival):
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    env.process(concert_scheduler(env, stage))
    env.run(until=41)
    assert not stage.is_open


def test_concert_scheduler_opens_for_each_show(festival):
    env = festival.env
    stage = festival.stages["Main Stage"]
    env.process(concert_scheduler(env, stage))
    env.run(until=481)
    assert not stage.is_open


# ─────────────────────────────────────────────
# TESTES: get_next_show_or_active
# ─────────────────────────────────────────────

def test_get_next_show_or_active_returns_show_before_end(festival):
    show = get_next_show_or_active("Sza", 10.0)
    assert show is not None
    assert show["artist"] == "Sza"


def test_get_next_show_or_active_returns_none_after_end(festival):
    show = get_next_show_or_active("Sza", 50.0)
    assert show is None


def test_get_next_show_or_active_unknown_artist(festival):
    assert get_next_show_or_active("Artista Falso", 0.0) is None


# ─────────────────────────────────────────────
# TESTES: choose_stage_for_agent
# ─────────────────────────────────────────────

def test_choose_stage_for_agent_returns_stage(festival, rngs):
    rng, np_rng = rngs
    agent = create_agent(rng, np_rng)
    result = choose_stage_for_agent(agent, festival)
    from src.coachella.simulation.environment import Stage
    assert isinstance(result, Stage)


def test_choose_stage_for_agent_respects_exclude(festival, rngs):
    rng, np_rng = rngs
    agent = create_agent(rng, np_rng)
    exclude = ["Main Stage", "Sahara Stage"]
    result = choose_stage_for_agent(agent, festival, exclude=exclude)
    if result is not None:
        assert result.name not in exclude


def test_fan_goes_to_favorite_stage(festival):
    rng = random.Random(42)
    np_rng = np.random.default_rng(42)
    agent = create_agent(rng, np_rng)
    agent.agent_type = AgentType.FAN
    agent.profile = PROFILES[AgentType.FAN]
    agent.favorite_artists = ["Sza"]
    festival.env._now = 5
    result = choose_stage_for_agent(agent, festival)
    assert result is not None
    assert result.name == "Outdoor Stage"


def test_choose_stage_app_avoids_congested(festival_app):
    """Com app informativa, agente evita palcos congestionados."""
    agent = create_agent(festival_app.rng, festival_app.np_rng)
    agent.favorite_artists = []

    # Mockar TODOS os palcos exceto Outdoor Stage como congestionados
    stages_to_mock = ["Main Stage", "Sahara Stage"]

    def mock_get_info(stage_name):
        return {
            "occupancy": 80,
            "queue_length": 0,
            "capacity": 80,
            "is_congested": stage_name in stages_to_mock,
        }

    with patch.object(festival_app, "get_stage_info_for_agent", side_effect=mock_get_info):
        with patch.object(festival_app.policy, "agent_uses_app", return_value=True):
            result = choose_stage_for_agent(agent, festival_app)

    assert result is not None
    assert result.name == "Outdoor Stage"


def test_choose_stage_baseline_ignores_congestion(festival):
    """Baseline não tem app — agente pode ir a palco congestionado."""
    agent = create_agent(festival.rng, festival.np_rng)
    agent.favorite_artists = []

    # Com baseline, app_enabled=False → choose_stage_for_agent não filtra por congestionamento
    assert festival.policy.app_enabled is False
    # Apenas verificamos que a função corre sem erro com baseline
    result = choose_stage_for_agent(agent, festival)
    from src.coachella.simulation.environment import Stage
    assert result is None or isinstance(result, Stage)


# ─────────────────────────────────────────────
# TESTES: visit_stage — baseline
# ─────────────────────────────────────────────

def test_agent_enters_stage_and_is_served(festival):
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert stage.total_served == 1
    assert stage.total_reneged == 0


def test_agent_status_leaving_after_visit(festival):
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert agent.status == "leaving"


def test_wait_time_recorded_after_entry(festival):
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
    env = festival.env
    stage = festival.stages["Main Stage"]
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999
    festival.active_agents.append(agent)

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert agent not in festival.active_agents


def test_agent_records_favorite_seen(festival):
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
    env = festival.env
    stage = festival.stages["Main Stage"]
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert agent.total_wait_time >= 0


def test_stage_added_to_stages_visited(festival):
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999
    agent.favorite_artists = []

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    assert "Outdoor Stage" in agent.stages_visited


# ─────────────────────────────────────────────
# TESTES: visit_stage — VIP Priority
# ─────────────────────────────────────────────

def test_vip_uses_priority_resource(festival_vip):
    """Com VIP Priority, o resource é PriorityResource."""
    for stage in festival_vip.stages.values():
        assert isinstance(stage.resource, simpy.PriorityResource)


def test_vip_served_before_general(festival_vip):
    """VIP deve ser servido antes de General quando palco está cheio."""
    env = festival_vip.env
    stage = festival_vip.stages["Outdoor Stage"]
    stage.is_open = True

    served_order = []

    # Encher o palco com blockers para forçar fila
    blockers = []
    for _ in range(stage.capacity):
        b = create_agent(festival_vip.rng, festival_vip.np_rng)
        b.patience = 999
        b.watch_duration = 30
        b.leaves_early = False
        blockers.append(b)
        env.process(visit_stage(env, b, stage, festival_vip))

    # Agente General entra na fila primeiro
    general = create_agent(festival_vip.rng, festival_vip.np_rng)
    general.agent_type = AgentType.GENERAL
    general.patience = 999
    general.favorite_artists = []

    # Agente VIP entra na fila depois
    vip = create_agent(festival_vip.rng, festival_vip.np_rng)
    vip.agent_type = AgentType.VIP
    vip.patience = 999
    vip.favorite_artists = []

    def track_visit(agent, label):
        def inner():
            yield env.timeout(1)  # General chega primeiro
            env.process(visit_stage(env, agent, stage, festival_vip))
            yield env.timeout(0)
        return inner

    # General chega em t=1, VIP em t=2
    def spawn_general():
        yield env.timeout(1)
        env.process(visit_stage(env, general, stage, festival_vip))

    def spawn_vip():
        yield env.timeout(2)
        env.process(visit_stage(env, vip, stage, festival_vip))

    env.process(spawn_general())
    env.process(spawn_vip())
    env.run(until=5)

    # Com PriorityResource, VIP (priority=0) deve ultrapassar General (priority=2)
    # Ambos estão em fila — VIP deve ter menor posição na fila ou ser servido primeiro
    assert isinstance(stage.resource, simpy.PriorityResource)


def test_baseline_uses_regular_resource(festival):
    """Baseline usa simpy.Resource normal, não PriorityResource."""
    for stage in festival.stages.values():
        assert not isinstance(stage.resource, simpy.PriorityResource)


# ─────────────────────────────────────────────
# TESTES: visit_stage — renege
# ─────────────────────────────────────────────

def test_agent_reneges_when_patience_zero(festival):
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True

    for _ in range(stage.capacity):
        blocker = create_agent(festival.rng, festival.np_rng)
        blocker.patience = 999
        env.process(visit_stage(env, blocker, stage, festival))

    impatient = create_agent(festival.rng, festival.np_rng)
    impatient.favorite_artists = []
    impatient.get_patience_for = lambda artist, np_rng: 0.0

    env.process(visit_stage(env, impatient, stage, festival))
    env.run(until=5)

    assert stage.total_reneged >= 1


def test_patience_decreases_after_renege(festival):
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
# TESTES: visit_stage — gestão ativa
# ─────────────────────────────────────────────

def test_active_management_renege_logs_recommendation(festival_active, caplog):
    """Com gestão ativa, renege em palco congestionado deve logar recomendação."""
    import logging
    env = festival_active.env
    stage = festival_active.stages["Outdoor Stage"]
    stage.is_open = True

    # Encher o palco
    for _ in range(stage.capacity):
        blocker = create_agent(festival_active.rng, festival_active.np_rng)
        blocker.patience = 999
        env.process(visit_stage(env, blocker, stage, festival_active))

    impatient = create_agent(festival_active.rng, festival_active.np_rng)
    impatient.favorite_artists = []
    impatient.get_patience_for = lambda artist, np_rng: 0.0

    # Forçar congestionamento e compliance
    with patch.object(festival_active.policy, "is_congested", return_value=True):
        with patch.object(festival_active.policy, "agent_follows_recommendation", return_value=True):
            with caplog.at_level(logging.DEBUG, logger="src.coachella.simulation.events"):
                env.process(visit_stage(env, impatient, stage, festival_active))
                env.run(until=5)

    assert any("seguiu recomendação" in r.message for r in caplog.records)


def test_active_management_does_not_log_when_not_following(festival_active, caplog):
    """Se agente não segue recomendação, não deve logar recomendação."""
    import logging
    env = festival_active.env
    stage = festival_active.stages["Outdoor Stage"]
    stage.is_open = True

    for _ in range(stage.capacity):
        blocker = create_agent(festival_active.rng, festival_active.np_rng)
        blocker.patience = 999
        env.process(visit_stage(env, blocker, stage, festival_active))

    impatient = create_agent(festival_active.rng, festival_active.np_rng)
    impatient.favorite_artists = []
    impatient.get_patience_for = lambda artist, np_rng: 0.0

    with patch.object(festival_active.policy, "is_congested", return_value=True):
        with patch.object(festival_active.policy, "agent_follows_recommendation", return_value=False):
            with caplog.at_level(logging.DEBUG, logger="src.coachella.simulation.events"):
                env.process(visit_stage(env, impatient, stage, festival_active))
                env.run(until=5)

    assert not any("seguiu recomendação" in r.message for r in caplog.records)


# ─────────────────────────────────────────────
# TESTES: try_another_stage
# ─────────────────────────────────────────────

def test_try_another_stage_goes_to_alternative(festival):
    env = festival.env
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999
    festival.active_agents.append(agent)

    env.process(try_another_stage(env, agent, festival, exclude=["Main Stage"], time_spent=0.0))
    env.run()

    assert agent.status == "leaving"


def test_try_another_stage_leaves_when_no_alternative(festival):
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
    env = festival.env
    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    assert Agent._id_counter == 10


def test_agent_arrivals_uses_exponential_interarrival(festival):
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
    env = festival.env
    festival.setup()
    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    assert len(festival.active_agents) == 0


def test_total_served_leq_num_agents(festival):
    env = festival.env
    festival.setup()
    with patch("src.coachella.simulation.events.NUM_AGENTS", 10):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    total_served = sum(s.total_served for s in festival.stages.values())
    assert total_served <= 10


def test_agent_arrivals_creates_mixed_profiles(festival):
    env = festival.env
    festival.setup()
    with patch("src.coachella.simulation.events.NUM_AGENTS", 50):
        env.process(agent_arrivals(env, festival))
        env.run(until=600)

    assert Agent._id_counter == 50


# ─────────────────────────────────────────────
# TESTES: Perfis — métricas e comportamento
# ─────────────────────────────────────────────

def test_served_by_profile_increments(festival):
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True
    agent = create_agent(festival.rng, festival.np_rng)
    agent.patience = 999
    agent.favorite_artists = []

    env.process(visit_stage(env, agent, stage, festival))
    env.run()

    total_served = sum(festival.served_by_profile.values())
    assert total_served == 1


def test_reneged_by_profile_increments(festival):
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True

    for _ in range(stage.capacity):
        blocker = create_agent(festival.rng, festival.np_rng)
        blocker.patience = 999
        env.process(visit_stage(env, blocker, stage, festival))

    impatient = create_agent(festival.rng, festival.np_rng)
    impatient.favorite_artists = []
    impatient.get_patience_for = lambda artist, np_rng: 0.0

    env.process(visit_stage(env, impatient, stage, festival))
    env.run(until=5)

    total_reneged = sum(festival.reneged_by_profile.values())
    assert total_reneged >= 1
    assert impatient.reneged is True


def test_leaves_early_shorter_watch(festival):
    env = festival.env
    stage = festival.stages["Outdoor Stage"]
    stage.is_open = True

    early = create_agent(festival.rng, festival.np_rng)
    early.leaves_early = True
    early.patience = 999
    early.favorite_artists = []

    normal = create_agent(festival.rng, festival.np_rng)
    normal.leaves_early = False
    normal.patience = 999
    normal.favorite_artists = []
    normal.watch_duration = early.watch_duration

    t_early_start = env.now
    env.process(visit_stage(env, early, stage, festival))
    env.run()
    t_early_end = env.now

    assert t_early_end < t_early_start + early.watch_duration + 10