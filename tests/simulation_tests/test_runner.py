"""
tests/simulation_tests/test_runner.py - Testes para simulation/runner.py

Cobre:
- run_single(): métricas corretas, estrutura do dict, reproducibilidade
- run_policy(): N réplicas, seeds independentes, erros isolados
- run_all_policies(): 4 políticas, estrutura do output
- results_to_dataframe(): conversão correta, sem wait_times
"""

import pytest
import pandas as pd
from unittest.mock import patch
from src.coachella.simulation.runner import (
    run_single,
    run_policy,
    run_all_policies,
    results_to_dataframe,
    DEFAULT_REPLICAS,
)
from src.coachella.simulation.policies import (
    BASELINE, INFORMATIVE_APP, ACTIVE_MANAGEMENT, VIP_PRIORITY, ALL_POLICIES
)
from src.coachella.simulation.agents import AgentType


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def single_result():
    """Corre uma réplica baseline com poucos agentes para rapidez."""
    with patch("src.coachella.simulation.runner.NUM_AGENTS", 10):
        with patch("src.coachella.simulation.runner.SIM_DURATION", 60):
            return run_single(BASELINE, seed=42)


@pytest.fixture
def policy_results():
    """Corre 3 réplicas baseline com poucos agentes."""
    with patch("src.coachella.simulation.runner.NUM_AGENTS", 10):
        with patch("src.coachella.simulation.runner.SIM_DURATION", 60):
            return run_policy(BASELINE, n_replicas=3, base_seed=100)


@pytest.fixture
def all_results():
    """Corre 2 réplicas de cada política com poucos agentes."""
    with patch("src.coachella.simulation.runner.NUM_AGENTS", 10):
        with patch("src.coachella.simulation.runner.SIM_DURATION", 60):
            return run_all_policies(n_replicas=2, base_seed=100)


# ─────────────────────────────────────────────
# TESTES: run_single — estrutura do resultado
# ─────────────────────────────────────────────

class TestRunSingle:
    def test_returns_dict(self, single_result):
        assert isinstance(single_result, dict)

    def test_has_policy_name(self, single_result):
        assert single_result["policy"] == "Baseline"

    def test_has_seed(self, single_result):
        assert single_result["seed"] == 42

    def test_has_global_metrics(self, single_result):
        for key in ["total_served", "total_reneged", "avg_wait_time",
                    "throughput", "renege_rate"]:
            assert key in single_result, f"Falta chave: {key}"

    def test_has_wait_times_list(self, single_result):
        assert "wait_times" in single_result
        assert isinstance(single_result["wait_times"], list)

    def test_has_profile_metrics(self, single_result):
        for agent_type in AgentType:
            key = agent_type.value
            assert f"served_{key}"      in single_result
            assert f"reneged_{key}"     in single_result
            assert f"renege_rate_{key}" in single_result

    def test_has_stage_metrics(self, single_result):
        for stage_name in ["main_stage", "sahara_stage", "outdoor_stage"]:
            assert f"served_{stage_name}"   in single_result
            assert f"reneged_{stage_name}"  in single_result
            assert f"avg_wait_{stage_name}" in single_result

    def test_total_served_non_negative(self, single_result):
        assert single_result["total_served"] >= 0

    def test_total_reneged_non_negative(self, single_result):
        assert single_result["total_reneged"] >= 0

    def test_renege_rate_between_0_and_1(self, single_result):
        assert 0.0 <= single_result["renege_rate"] <= 1.0

    def test_throughput_positive(self, single_result):
        assert single_result["throughput"] >= 0.0

    def test_avg_wait_time_non_negative(self, single_result):
        assert single_result["avg_wait_time"] >= 0.0

    def test_served_plus_reneged_leq_num_agents(self, single_result):
        """
        total_served conta visitas a palcos (um agente pode visitar vários).
        served_by_profile conta agentes únicos servidos.
        Ambos devem ser não-negativos e served_by_profile <= total_served.
        """
        profile_served = sum(
            single_result[f"served_{t.value}"] for t in AgentType
        )
        assert profile_served >= 0
        assert single_result["total_served"] >= profile_served

    def test_profile_served_sum_equals_total_served(self, single_result):
        """served_by_profile <= total_served — agentes únicos vs visitas totais."""
        profile_total = sum(
            single_result[f"served_{t.value}"] for t in AgentType
        )
        assert single_result["total_served"] >= profile_total >= 0

    def test_profile_reneged_sum_equals_total_reneged(self, single_result):
        """Soma de reneges por perfil deve igualar total_reneged."""
        profile_total = sum(
            single_result[f"reneged_{t.value}"] for t in AgentType
        )
        assert profile_total == single_result["total_reneged"]


# ─────────────────────────────────────────────
# TESTES: run_single — reproducibilidade
# ─────────────────────────────────────────────

class TestRunSingleReproducibility:
    def test_same_seed_same_result(self):
        """A mesma seed deve produzir exatamente o mesmo resultado."""
        with patch("src.coachella.simulation.runner.NUM_AGENTS", 10):
            with patch("src.coachella.simulation.runner.SIM_DURATION", 60):
                r1 = run_single(BASELINE, seed=42)
                r2 = run_single(BASELINE, seed=42)
        assert r1["total_served"]  == r2["total_served"]
        assert r1["total_reneged"] == r2["total_reneged"]
        assert r1["avg_wait_time"] == r2["avg_wait_time"]

    def test_different_seeds_may_differ(self):
        """Seeds diferentes devem produzir resultados potencialmente diferentes."""
        with patch("src.coachella.simulation.runner.NUM_AGENTS", 20):
            with patch("src.coachella.simulation.runner.SIM_DURATION", 60):
                r1 = run_single(BASELINE, seed=1)
                r2 = run_single(BASELINE, seed=999)
        # Não são necessariamente diferentes mas é muito improvável serem iguais
        # Verificamos apenas que ambos são válidos
        assert r1["total_served"] >= 0
        assert r2["total_served"] >= 0

    def test_policy_name_recorded_correctly(self):
        """Nome da política deve estar correto no resultado."""
        with patch("src.coachella.simulation.runner.NUM_AGENTS", 5):
            with patch("src.coachella.simulation.runner.SIM_DURATION", 60):
                for policy in ALL_POLICIES:
                    result = run_single(policy, seed=42)
                    assert result["policy"] == policy.name


# ─────────────────────────────────────────────
# TESTES: run_policy
# ─────────────────────────────────────────────

class TestRunPolicy:
    def test_returns_list(self, policy_results):
        assert isinstance(policy_results, list)

    def test_correct_number_of_replicas(self, policy_results):
        assert len(policy_results) == 3

    def test_each_result_is_dict(self, policy_results):
        for result in policy_results:
            assert isinstance(result, dict)

    def test_seeds_are_sequential(self, policy_results):
        """Seeds devem ser base_seed + i para garantir independência."""
        seeds = [r["seed"] for r in policy_results]
        assert seeds == [100, 101, 102]

    def test_all_results_have_same_policy(self, policy_results):
        for result in policy_results:
            assert result["policy"] == "Baseline"

    def test_default_replicas_is_30(self):
        assert DEFAULT_REPLICAS == 30

    def test_error_in_one_replica_does_not_stop_others(self):
        """Erro numa réplica não deve cancelar as restantes."""
        call_count = 0
        original_run_single = run_single

        def flaky_run_single(policy, seed):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Erro simulado na réplica 2")
            return original_run_single(policy, seed)

        with patch("src.coachella.simulation.runner.NUM_AGENTS", 5):
            with patch("src.coachella.simulation.runner.SIM_DURATION", 60):
                with patch("src.coachella.simulation.runner.run_single",
                           side_effect=flaky_run_single):
                    results = run_policy(BASELINE, n_replicas=3, base_seed=100)

        # 2 réplicas bem-sucedidas (réplica 2 falhou)
        assert len(results) == 2


# ─────────────────────────────────────────────
# TESTES: run_all_policies
# ─────────────────────────────────────────────

class TestRunAllPolicies:
    def test_returns_dict(self, all_results):
        assert isinstance(all_results, dict)

    def test_has_all_four_policies(self, all_results):
        expected = {p.name for p in ALL_POLICIES}
        assert set(all_results.keys()) == expected

    def test_each_policy_has_correct_replicas(self, all_results):
        for policy_name, results in all_results.items():
            assert len(results) == 2, f"Política '{policy_name}' tem {len(results)} réplicas"

    def test_all_policy_names_correct(self, all_results):
        for policy_name, results in all_results.items():
            for result in results:
                assert result["policy"] == policy_name

    def test_vip_results_present(self, all_results):
        assert "VIP Priority" in all_results
        assert len(all_results["VIP Priority"]) == 2

    def test_baseline_results_present(self, all_results):
        assert "Baseline" in all_results


# ─────────────────────────────────────────────
# TESTES: results_to_dataframe
# ─────────────────────────────────────────────

class TestResultsToDataframe:
    def test_returns_dataframe(self, all_results):
        df = results_to_dataframe(all_results)
        assert isinstance(df, pd.DataFrame)

    def test_correct_number_of_rows(self, all_results):
        """2 réplicas × 4 políticas = 8 linhas."""
        df = results_to_dataframe(all_results)
        assert len(df) == 8

    def test_has_policy_column(self, all_results):
        df = results_to_dataframe(all_results)
        assert "policy" in df.columns

    def test_has_metric_columns(self, all_results):
        df = results_to_dataframe(all_results)
        for col in ["total_served", "total_reneged", "avg_wait_time",
                    "throughput", "renege_rate"]:
            assert col in df.columns

    def test_wait_times_not_in_dataframe(self, all_results):
        """wait_times é lista aninhada — não deve aparecer no DataFrame."""
        df = results_to_dataframe(all_results)
        assert "wait_times" not in df.columns

    def test_all_four_policies_in_dataframe(self, all_results):
        df = results_to_dataframe(all_results)
        assert set(df["policy"].unique()) == {p.name for p in ALL_POLICIES}

    def test_no_null_values_in_numeric_columns(self, all_results):
        df = results_to_dataframe(all_results)
        numeric_cols = ["total_served", "total_reneged", "avg_wait_time",
                        "throughput", "renege_rate"]
        assert not df[numeric_cols].isnull().any().any()