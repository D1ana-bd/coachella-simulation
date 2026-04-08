import pytest
import simpy
import os
from unittest.mock import patch, MagicMock
from src.coachella.simulation.environment import FestivalEnvironment, Stage
from src.coachella.config import STAGES, METRICS_INTERVAL, OUTPUT_DIR, METRICS_FILE


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def env():
    return FestivalEnvironment(seed=42)


@pytest.fixture
def stage(env):
    return env.stages["Main Stage"]


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
    """FestivalEnvironment tem np_rng para distribuições Normais."""
    import numpy as np
    assert isinstance(env.np_rng, np.random.Generator)


def test_environment_creates_output_dir(tmp_path):
    fake_output = str(tmp_path / "test_data/")
    with patch("src.coachella.simulation.environment.OUTPUT_DIR", fake_output):
        with patch("src.coachella.simulation.environment.METRICS_FILE", fake_output + "metrics.csv"):
            fe = FestivalEnvironment()
    assert os.path.exists(fake_output)


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
    assert stage.capacity == STAGES["Main Stage"]["capacity"]


def test_stage_popularity_matches_config(stage):
    assert stage.popularity == STAGES["Main Stage"]["popularity"]


def test_stage_has_no_show_duration_attr(stage):
    """show_duration e shows_start foram removidos — vivem no lineup.py."""
    assert not hasattr(stage, "show_duration")
    assert not hasattr(stage, "shows_start")


# ─────────────────────────────────────────────
# TESTES: Stage - Shows (via lineup.py)
# ─────────────────────────────────────────────

def test_stage_no_active_show_at_start(stage):
    """Main Stage: primeiro show (Becky G) começa em t=60 → t=0 sem show."""
    assert not stage.has_active_show()


def test_stage_active_show_during_show(stage):
    """t=65 está dentro do show Becky G (start=60, duration=60)."""
    stage.env._now = 65
    assert stage.has_active_show()


def test_stage_no_active_show_between_shows(stage):
    """t=130 está entre o Becky G (60-120) e o Burna Boy (180-240)."""
    stage.env._now = 130
    assert not stage.has_active_show()


def test_stage_next_show_in_returns_positive(stage):
    """t=0: próximo show do Main Stage é Becky G em t=60 → 60 min."""
    result = stage.next_show_in()
    assert result == pytest.approx(60.0)


def test_stage_next_show_in_returns_minus_one_after_last_show(stage):
    """Depois do último show, next_show_in() retorna -1."""
    stage.env._now = 9999
    assert stage.next_show_in() == -1


def test_outdoor_stage_has_active_show_at_start():
    """Outdoor Stage: SZA começa em t=0 → show ativo imediatamente."""
    fe = FestivalEnvironment(seed=0)
    outdoor = fe.stages["Outdoor Stage"]
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
    """t=0: Main Stage sem show → current_artist é None."""
    snap = stage.snapshot()
    assert snap["current_artist"] is None


def test_stage_snapshot_current_artist_during_show(stage):
    """t=65: Becky G a tocar → current_artist é 'Becky G'."""
    stage.env._now = 65
    snap = stage.snapshot()
    assert snap["current_artist"] == "Becky G"


def test_stage_snapshot_values_match_state(stage):
    stage.record_wait(5.0)
    stage.total_served = 3
    snap = stage.snapshot()
    assert snap["stage"] == "Main Stage"
    assert snap["occupancy"] == 0
    assert snap["total_served"] == 3
    assert snap["avg_wait_time"] == 5.0


# ─────────────────────────────────────────────
# TESTES: FestivalEnvironment - choose_stage
# ─────────────────────────────────────────────

def test_choose_stage_returns_stage_instance(env):
    assert isinstance(env.choose_stage(), Stage)


def test_choose_stage_excludes_specified_stages(env):
    exclude = ["Main Stage", "Sahara Stage"]
    result = env.choose_stage(exclude=exclude)
    assert result.name not in exclude


def test_choose_stage_returns_none_when_all_full(env):
    for stage in env.stages.values():
        stage.resource.queue.extend([MagicMock()] * 51)
    assert env.choose_stage() is None


def test_choose_stage_returns_none_when_all_excluded(env):
    all_stages = list(env.stages.keys())
    assert env.choose_stage(exclude=all_stages) is None


# ─────────────────────────────────────────────
# TESTES: FestivalEnvironment - Métricas & Run
# ─────────────────────────────────────────────

def test_collect_metrics_populates_log(env):
    env.setup()
    env.run(duration=METRICS_INTERVAL + 1)
    assert len(env.metrics_log) > 0


def test_collect_metrics_one_entry_per_stage_per_interval(env):
    """t=0 e t=10 → 2 snapshots × 3 palcos = 6 entradas."""
    env.setup()
    env.run(duration=METRICS_INTERVAL + 1)
    assert len(env.metrics_log) == len(STAGES) * 2


def test_save_metrics_creates_csv(env, tmp_path):
    fake_file = str(tmp_path / "metrics.csv")
    env.metrics_log = [{
        "stage": "Main Stage", "time": 0, "occupancy": 0,
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