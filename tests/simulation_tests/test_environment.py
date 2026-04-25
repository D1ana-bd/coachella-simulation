"""
tests/simulation_tests/test_environment.py
"""

import pytest
import simpy
import os
from unittest.mock import patch, MagicMock
from src.coachella.simulation.environment import FestivalEnvironment, Stage
from src.coachella.simulation.policies import BASELINE, INFORMATIVE_APP, ACTIVE_MANAGEMENT, VIP_PRIORITY
from src.coachella.config import STAGES, METRICS_INTERVAL, OUTPUT_DIR, METRICS_FILE


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def env():
    return FestivalEnvironment(seed=42)


@pytest.fixture
def stage(env):
    return env.stages["Coachella Stage"]


# ─────────────────────────────────────────────
# TESTES: FestivalEnvironment - Inicialização
# ─────────────────────────────────────────────

def test_environment_creates_all_stages(env):
    assert set(env.stages.keys()) == set(STAGES.keys())


def test_environment_stages_are_stage_instances(env):
    for stage in env.stages.values():
        assert isinstance(stage, Stage)


def test_environment_initial_metrics_empty(env):
    assert env.metrics_log == []


def test_environment_initial_agents_empty(env):
    assert env.active_agents == []


def test_environment_has_np_rng(env):
    import numpy as np
    assert isinstance(env.np_rng, np.random.Generator)


def test_environment_creates_output_dir(tmp_path):
    fake_output = str(tmp_path / "test_data/")
    with patch("src.coachella.simulation.environment.OUTPUT_DIR", fake_output):
        with patch("src.coachella.simulation.environment.METRICS_FILE", fake_output + "metrics.csv"):
            fe = FestivalEnvironment()
    assert os.path.exists(fake_output)


# ─────────────────────────────────────────────
# TESTES: FestivalEnvironment - PolicyConfig
# ─────────────────────────────────────────────

def test_environment_default_policy_is_baseline():
    fe = FestivalEnvironment(seed=42)
    assert fe.policy.name == "Baseline"


def test_environment_accepts_policy():
    fe = FestivalEnvironment(seed=42, policy=INFORMATIVE_APP)
    assert fe.policy.name == "Informative App"


def test_environment_accepts_active_management_policy():
    fe = FestivalEnvironment(seed=42, policy=ACTIVE_MANAGEMENT)
    assert fe.policy.name == "Active Management"


def test_environment_accepts_vip_policy():
    fe = FestivalEnvironment(seed=42, policy=VIP_PRIORITY)
    assert fe.policy.name == "VIP Priority"


# ─────────────────────────────────────────────
# TESTES: Stage - Resource vs PriorityResource
# ─────────────────────────────────────────────

def test_stage_uses_resource_with_baseline():
    fe = FestivalEnvironment(seed=42, policy=BASELINE)
    for stage in fe.stages.values():
        assert isinstance(stage.resource, simpy.Resource)
        assert not isinstance(stage.resource, simpy.PriorityResource)


def test_stage_uses_priority_resource_with_vip_policy():
    fe = FestivalEnvironment(seed=42, policy=VIP_PRIORITY)
    for stage in fe.stages.values():
        assert isinstance(stage.resource, simpy.PriorityResource)


def test_stage_uses_resource_with_informative_app():
    fe = FestivalEnvironment(seed=42, policy=INFORMATIVE_APP)
    for stage in fe.stages.values():
        assert isinstance(stage.resource, simpy.Resource)
        assert not isinstance(stage.resource, simpy.PriorityResource)


def test_stage_uses_resource_with_active_management():
    fe = FestivalEnvironment(seed=42, policy=ACTIVE_MANAGEMENT)
    for stage in fe.stages.values():
        assert isinstance(stage.resource, simpy.Resource)
        assert not isinstance(stage.resource, simpy.PriorityResource)


# ─────────────────────────────────────────────
# TESTES: get_stage_info_for_agent()
# ─────────────────────────────────────────────

def test_get_stage_info_returns_required_keys(env):
    info = env.get_stage_info_for_agent("Coachella Stage")
    assert {"occupancy", "queue_length", "capacity", "is_congested"} == set(info.keys())


def test_get_stage_info_occupancy_initially_zero(env):
    info = env.get_stage_info_for_agent("Coachella Stage")
    assert info["occupancy"] == 0


def test_get_stage_info_capacity_matches_config(env):
    info = env.get_stage_info_for_agent("Coachella Stage")
    assert info["capacity"] == STAGES["Coachella Stage"]["capacity"]


def test_get_stage_info_not_congested_when_empty(env):
    info = env.get_stage_info_for_agent("Coachella Stage")
    assert info["is_congested"] is False


def test_get_stage_info_congested_when_above_threshold():
    """Palco com 90% de ocupação está congestionado (threshold=0.85)."""
    fe = FestivalEnvironment(seed=42, policy=ACTIVE_MANAGEMENT)
    stage = fe.stages["Coachella Stage"]
    from unittest.mock import PropertyMock
    # 90% de 3000 = 2700
    with patch.object(type(stage), "occupancy", new_callable=PropertyMock, return_value=2700):
        info = fe.get_stage_info_for_agent("Coachella Stage")
        assert info["is_congested"] is True


def test_get_stage_info_not_congested_baseline():
    fe = FestivalEnvironment(seed=42, policy=BASELINE)
    info = fe.get_stage_info_for_agent("Sahara")
    assert "is_congested" in info


# ─────────────────────────────────────────────
# TESTES: Stage - Estado inicial
# ─────────────────────────────────────────────

def test_stage_initial_occupancy_zero(stage):
    assert stage.occupancy == 0


def test_stage_initial_queue_empty(stage):
    assert stage.queue_length == 0


def test_stage_not_full_initially(stage):
    assert not stage.is_full


def test_stage_capacity_matches_config(stage):
    assert stage.capacity == STAGES["Coachella Stage"]["capacity"]


def test_stage_popularity_matches_config(stage):
    assert stage.popularity == STAGES["Coachella Stage"]["popularity"]


def test_stage_has_no_show_duration_attr(stage):
    assert not hasattr(stage, "show_duration")
    assert not hasattr(stage, "shows_start")


# ─────────────────────────────────────────────
# TESTES: Stage - Shows (via lineup.py)
# ─────────────────────────────────────────────

def test_stage_no_active_show_at_start(stage):
    assert not stage.has_active_show()


def test_stage_active_show_during_show(stage):
    # Becky G: start=60, duration=60 → ativo entre t=60 e t=120
    stage.env._now = 65
    assert stage.has_active_show()


def test_stage_no_active_show_between_shows(stage):
    # Entre Becky G (fim=120) e Burna Boy (start=180)
    stage.env._now = 150
    assert not stage.has_active_show()


def test_stage_next_show_in_returns_positive(stage):
    # t=0: próximo show é Becky G a t=60 → 60 minutos
    result = stage.next_show_in()
    assert result == pytest.approx(60.0)


def test_stage_next_show_in_returns_minus_one_after_last_show(stage):
    stage.env._now = 9999
    assert stage.next_show_in() == -1


def test_outdoor_theatre_has_active_show_at_start():
    fe = FestivalEnvironment(seed=0)
    outdoor = fe.stages["Outdoor Theatre"]
    # SZA: start=0, duration=40 → ativo a t=10
    outdoor.env._now = 10
    assert outdoor.has_active_show()


# ─────────────────────────────────────────────
# TESTES: Stage - Métricas
# ─────────────────────────────────────────────

def test_stage_avg_wait_time_zero_initially(stage):
    assert stage.avg_wait_time() == 0.0


def test_stage_record_wait_updates_avg(stage):
    stage.record_wait(10.0)
    stage.record_wait(20.0)
    assert stage.avg_wait_time() == 15.0


def test_stage_snapshot_has_required_keys(stage):
    snap = stage.snapshot()
    expected_keys = {
        "stage", "time", "occupancy", "queue_length",
        "total_served", "total_reneged", "avg_wait_time",
        "active_show", "current_artist",
    }
    assert expected_keys == set(snap.keys())


def test_stage_snapshot_current_artist_none_when_no_show(stage):
    snap = stage.snapshot()
    assert snap["current_artist"] is None


def test_stage_snapshot_current_artist_during_show(stage):
    # Becky G toca no Coachella Stage a t=65
    stage.env._now = 65
    snap = stage.snapshot()
    assert snap["current_artist"] == "Becky G"


def test_stage_snapshot_values_match_state(stage):
    stage.record_wait(5.0)
    stage.total_served = 3
    snap = stage.snapshot()
    assert snap["stage"] == "Coachella Stage"
    assert snap["occupancy"] == 0
    assert snap["total_served"] == 3
    assert snap["avg_wait_time"] == 5.0


# ─────────────────────────────────────────────
# TESTES: FestivalEnvironment - choose_stage
# ─────────────────────────────────────────────

def test_choose_stage_returns_stage_instance(env):
    assert isinstance(env.choose_stage(), Stage)


def test_choose_stage_excludes_specified_stages(env):
    exclude = ["Coachella Stage", "Sahara"]
    result = env.choose_stage(exclude=exclude)
    assert result.name not in exclude


def test_choose_stage_returns_none_when_all_full(env):
    for stage in env.stages.values():
        stage.resource.queue.extend([MagicMock()] * 51)
    assert env.choose_stage() is None


def test_choose_stage_returns_none_when_all_excluded(env):
    all_stages = list(env.stages.keys())
    assert env.choose_stage(exclude=all_stages) is None


def test_choose_stage_vip_only_excluded_for_general(env):
    """Agentes General não devem conseguir ir ao Yuma (vip_only)."""
    from src.coachella.simulation.agents import AgentType
    results = set()
    for _ in range(50):
        s = env.choose_stage(agent_type=AgentType.GENERAL)
        if s:
            results.add(s.name)
    assert "Yuma" not in results


def test_choose_stage_vip_can_access_yuma(env):
    """Agentes VIP podem aceder ao Yuma."""
    from src.coachella.simulation.agents import AgentType
    results = set()
    for _ in range(100):
        s = env.choose_stage(agent_type=AgentType.VIP)
        if s:
            results.add(s.name)
    assert "Yuma" in results


# ─────────────────────────────────────────────
# TESTES: FestivalEnvironment - Métricas & Run
# ─────────────────────────────────────────────

def test_collect_metrics_populates_log(env):
    env.setup()
    env.run(duration=METRICS_INTERVAL + 1)
    assert len(env.metrics_log) > 0


def test_collect_metrics_one_entry_per_stage_per_interval(env):
    env.setup()
    env.run(duration=METRICS_INTERVAL + 1)
    assert len(env.metrics_log) == len(STAGES) * 2


def test_save_metrics_creates_csv(env, tmp_path):
    fake_file = str(tmp_path / "metrics.csv")
    env.metrics_log = [{
        "stage": "Coachella Stage", "time": 0, "occupancy": 0,
        "queue_length": 0, "total_served": 0, "total_reneged": 0,
        "avg_wait_time": 0.0, "active_show": False, "current_artist": None,
    }]
    with patch("src.coachella.simulation.environment.METRICS_FILE", fake_file):
        env.save_metrics()
    assert os.path.exists(fake_file)


def test_summary_returns_all_stages(env):
    assert set(env.summary().keys()) == set(STAGES.keys())


def test_summary_structure(env):
    for stage_summary in env.summary().values():
        assert "total_served" in stage_summary
        assert "total_reneged" in stage_summary
        assert "avg_wait_time" in stage_summary


# ─────────────────────────────────────────────
# TESTES: Métricas por perfil
# ─────────────────────────────────────────────

def test_environment_has_reneged_by_profile(env):
    from src.coachella.simulation.agents import AgentType
    assert set(env.reneged_by_profile.keys()) == set(AgentType)
    assert all(v == 0 for v in env.reneged_by_profile.values())


def test_environment_has_served_by_profile(env):
    from src.coachella.simulation.agents import AgentType
    assert set(env.served_by_profile.keys()) == set(AgentType)
    assert all(v == 0 for v in env.served_by_profile.values())


def test_profile_summary_structure(env):
    result = env.profile_summary()
    assert set(result.keys()) == {"general", "fan", "vip"}
    for v in result.values():
        assert "reneged" in v and "served" in v

