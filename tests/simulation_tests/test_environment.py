"""
tests/test_environment.py - Testes unitários para FestivalEnvironment e Stage
"""

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
    """Cria um FestivalEnvironment limpo para cada teste."""
    return FestivalEnvironment(seed=42)


@pytest.fixture
def stage(env):
    """Retorna o Main Stage do ambiente de teste."""
    return env.stages["Main Stage"]


# ─────────────────────────────────────────────
# TESTES: FestivalEnvironment - Inicialização
# ─────────────────────────────────────────────

def test_environment_creates_all_stages(env):
    """Verifica se todos os palcos definidos no config são criados."""
    assert set(env.stages.keys()) == set(STAGES.keys())


def test_environment_stages_are_stage_instances(env):
    """Verifica se todos os palcos são instâncias de Stage."""
    for stage in env.stages.values():
        assert isinstance(stage, Stage)


def test_environment_initial_metrics_empty(env):
    """O histórico de métricas começa vazio antes de correr a simulação."""
    assert env.metrics_log == []


def test_environment_initial_agents_empty(env):
    """Sem agentes ativos no início."""
    assert env.active_agents == []


def test_environment_creates_output_dir(tmp_path):
    """Verifica se o diretório de output é criado ao inicializar."""
    fake_output = str(tmp_path / "test_data/")
    with patch("src.coachella.simulation.environment.OUTPUT_DIR", fake_output):
        with patch("src.coachella.simulation.environment.METRICS_FILE", fake_output + "metrics.csv"):
            fe = FestivalEnvironment()
    assert os.path.exists(fake_output)


# ─────────────────────────────────────────────
# TESTES: Stage - Estado inicial
# ─────────────────────────────────────────────

def test_stage_initial_occupancy_zero(stage):
    """Palco começa vazio."""
    assert stage.occupancy == 0


def test_stage_initial_queue_empty(stage):
    """Fila começa vazia."""
    assert stage.queue_length == 0


def test_stage_not_full_initially(stage):
    """Palco não está cheio no início."""
    assert not stage.is_full


def test_stage_capacity_matches_config(stage):
    """Capacidade do palco corresponde ao config."""
    assert stage.capacity == STAGES["Main Stage"]["capacity"]


def test_stage_popularity_matches_config(stage):
    """Popularidade do palco corresponde ao config."""
    assert stage.popularity == STAGES["Main Stage"]["popularity"]


# ─────────────────────────────────────────────
# TESTES: Stage - Shows
# ─────────────────────────────────────────────

def test_stage_no_active_show_at_start(stage):
    """No tempo 0, verifica se há show ativo (depende do config)."""
    # Main Stage: shows_start = [60, 180, 300, 420] → t=0 não tem show
    assert not stage.has_active_show()


def test_stage_active_show_during_show(stage):
    """Durante um show, has_active_show() deve retornar True."""
    # Forçar o tempo do ambiente para dentro de um show
    stage.env._now = 60  # início do primeiro show do Main Stage
    assert stage.has_active_show()


def test_stage_next_show_in_returns_positive(stage):
    """next_show_in() deve retornar valor positivo no início da simulação."""
    result = stage.next_show_in()
    assert result > 0


def test_stage_next_show_in_returns_minus_one_after_last_show(stage):
    """Depois do último show, next_show_in() retorna -1."""
    stage.env._now = 9999  # bem depois do último show
    assert stage.next_show_in() == -1


# ─────────────────────────────────────────────
# TESTES: Stage - Métricas
# ─────────────────────────────────────────────

def test_stage_avg_wait_time_zero_initially(stage):
    """Média de espera é 0 quando não há registos."""
    assert stage.avg_wait_time() == 0.0


def test_stage_record_wait_updates_avg(stage):
    """Registar tempos de espera atualiza a média corretamente."""
    stage.record_wait(10.0)
    stage.record_wait(20.0)
    assert stage.avg_wait_time() == 15.0


def test_stage_snapshot_has_required_keys(stage):
    """Snapshot contém todas as chaves esperadas."""
    snap = stage.snapshot()
    expected_keys = {"stage", "time", "occupancy", "queue_length",
                     "total_served", "total_reneged", "avg_wait_time", "active_show"}
    assert expected_keys == set(snap.keys())


def test_stage_snapshot_values_match_state(stage):
    """Valores do snapshot refletem o estado real do palco."""
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
    """choose_stage() retorna uma instância de Stage."""
    result = env.choose_stage()
    assert isinstance(result, Stage)


def test_choose_stage_excludes_specified_stages(env):
    """choose_stage() não retorna palcos na lista de exclusão."""
    exclude = ["Main Stage", "Sahara Stage"]
    result = env.choose_stage(exclude=exclude)
    assert result.name not in exclude


def test_choose_stage_returns_none_when_all_full(env):
    """Se todas as filas estiverem cheias, retorna None."""
    # Forçar fila cheia em todos os palcos mockando queue_length
    for stage in env.stages.values():
        stage.resource.queue.extend([MagicMock()] * 51)  # > MAX_QUEUE_LENGTH
    result = env.choose_stage()
    assert result is None


def test_choose_stage_returns_none_when_all_excluded(env):
    """Se todos os palcos forem excluídos, retorna None."""
    all_stages = list(env.stages.keys())
    result = env.choose_stage(exclude=all_stages)
    assert result is None


# ─────────────────────────────────────────────
# TESTES: FestivalEnvironment - Métricas & Run
# ─────────────────────────────────────────────

def test_collect_metrics_populates_log(env):
    """Após correr a simulação, o metrics_log deve ter entradas."""
    env.setup()
    env.run(duration=METRICS_INTERVAL + 1)  # um intervalo completo
    assert len(env.metrics_log) > 0


def test_collect_metrics_one_entry_per_stage_per_interval(env):
    """Número de entradas = nº de palcos × nº de intervalos completos."""
    env.setup()
    env.run(duration=METRICS_INTERVAL + 1)
    # 1 intervalo completo → 1 snapshot por palco
    num_stages = len(STAGES)
    assert len(env.metrics_log) == num_stages


def test_save_metrics_creates_csv(env, tmp_path):
    """save_metrics() cria um ficheiro CSV no caminho definido."""
    fake_file = str(tmp_path / "metrics.csv")
    env.metrics_log = [{"stage": "Main Stage", "time": 0, "occupancy": 0,
                        "queue_length": 0, "total_served": 0, "total_reneged": 0,
                        "avg_wait_time": 0.0, "active_show": False}]
    with patch("src.coachella.simulation.environment.METRICS_FILE", fake_file):
        env.save_metrics()
    assert os.path.exists(fake_file)


def test_summary_returns_all_stages(env):
    """summary() retorna uma entrada para cada palco."""
    result = env.summary()
    assert set(result.keys()) == set(STAGES.keys())


def test_summary_structure(env):
    """summary() tem as chaves certas por palco."""
    result = env.summary()
    for stage_summary in result.values():
        assert "total_served" in stage_summary
        assert "total_reneged" in stage_summary
        assert "avg_wait_time" in stage_summary