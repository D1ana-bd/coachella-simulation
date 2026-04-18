"""
tests/analysis/test_statistics.py - Testes para analysis/statistics.py

Cobre:
- confidence_interval(): casos base, edge cases, nível de confiança
- summary_statistics(): estrutura, métricas corretas, erro em métrica inválida
- gini_coefficient(): igualdade perfeita, desigualdade máxima, casos edge
- gini_by_policy(): estrutura, valores válidos
- compare_policies(): estrutura, p-values válidos, significância
- full_report(): chaves obrigatórias, métricas disponíveis
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch
from src.coachella.analysis.statistics import (
    confidence_interval,
    summary_statistics,
    gini_coefficient,
    gini_by_policy,
    compare_policies,
    full_report,
)
from src.coachella.simulation.policies import ALL_POLICIES
from src.coachella.simulation.runner import run_all_policies, results_to_dataframe


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def all_results():
    """Corre 5 réplicas de cada política com poucos agentes — partilhado pelo módulo."""
    with patch("src.coachella.simulation.runner.NUM_AGENTS", 15):
        with patch("src.coachella.simulation.runner.SIM_DURATION", 60):
            return run_all_policies(n_replicas=5, base_seed=100)


@pytest.fixture(scope="module")
def df(all_results):
    return results_to_dataframe(all_results)


# ─────────────────────────────────────────────
# TESTES: confidence_interval
# ─────────────────────────────────────────────

class TestConfidenceInterval:
    def test_returns_tuple_of_two(self):
        result = confidence_interval([1, 2, 3, 4, 5])
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_lower_leq_upper(self):
        lo, hi = confidence_interval([10, 20, 30, 40, 50])
        assert lo <= hi

    def test_mean_inside_interval(self):
        data = [10, 20, 30, 40, 50]
        lo, hi = confidence_interval(data)
        mean = np.mean(data)
        assert lo <= mean <= hi

    def test_larger_sample_narrower_interval(self):
        """Mais dados → intervalo mais estreito."""
        small = [10, 20, 30, 40, 50]
        large = small * 20
        lo_s, hi_s = confidence_interval(small)
        lo_l, hi_l = confidence_interval(large)
        assert (hi_l - lo_l) < (hi_s - lo_s)

    def test_single_value_returns_mean_mean(self):
        lo, hi = confidence_interval([42.0])
        assert lo == hi == 42.0

    def test_empty_list_returns_zero_zero(self):
        lo, hi = confidence_interval([])
        assert lo == 0.0 and hi == 0.0

    def test_identical_values_narrow_interval(self):
        """Sem variância → intervalo muito estreito (ou igual)."""
        lo, hi = confidence_interval([5.0] * 30)
        assert hi - lo < 0.01

    def test_higher_confidence_wider_interval(self):
        """IC 99% deve ser mais largo que IC 95%."""
        data = list(range(1, 31))
        lo_95, hi_95 = confidence_interval(data, confidence=0.95)
        lo_99, hi_99 = confidence_interval(data, confidence=0.99)
        assert (hi_99 - lo_99) > (hi_95 - lo_95)

    def test_numpy_array_input(self):
        """Aceita numpy arrays além de listas."""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        lo, hi = confidence_interval(data)
        assert lo <= hi


# ─────────────────────────────────────────────
# TESTES: gini_coefficient
# ─────────────────────────────────────────────

class TestGiniCoefficient:
    def test_perfect_equality_returns_zero(self):
        """Todos esperam o mesmo → Gini = 0."""
        assert gini_coefficient([10, 10, 10, 10]) == pytest.approx(0.0, abs=1e-6)

    def test_maximum_inequality(self):
        """Um agente espera tudo, os outros nada → Gini próximo de 1."""
        data = [0, 0, 0, 0, 100]
        gini = gini_coefficient(data)
        assert gini > 0.6

    def test_returns_between_zero_and_one(self):
        """Gini deve estar sempre entre 0 e 1."""
        data = [1, 5, 10, 20, 50, 100]
        gini = gini_coefficient(data)
        assert 0.0 <= gini <= 1.0

    def test_empty_list_returns_zero(self):
        assert gini_coefficient([]) == 0.0

    def test_all_zeros_returns_zero(self):
        assert gini_coefficient([0, 0, 0, 0]) == 0.0

    def test_single_value_returns_zero(self):
        """Um único valor → sem desigualdade."""
        assert gini_coefficient([42.0]) == pytest.approx(0.0, abs=1e-6)

    def test_higher_inequality_higher_gini(self):
        """Distribuição mais desigual deve ter Gini mais alto."""
        equal    = [10, 10, 10, 10]
        unequal  = [1, 1, 1, 100]
        assert gini_coefficient(unequal) > gini_coefficient(equal)

    def test_numpy_array_input(self):
        data = np.array([5.0, 10.0, 15.0, 20.0])
        gini = gini_coefficient(data)
        assert 0.0 <= gini <= 1.0

    def test_ignores_negative_values(self):
        """Valores negativos são removidos antes do cálculo."""
        with_neg    = gini_coefficient([-5, 10, 10, 10])
        without_neg = gini_coefficient([10, 10, 10])
        assert with_neg == pytest.approx(without_neg, abs=1e-6)


# ─────────────────────────────────────────────
# TESTES: gini_by_policy
# ─────────────────────────────────────────────

class TestGiniByPolicy:
    def test_returns_dataframe(self, all_results):
        result = gini_by_policy(all_results)
        assert isinstance(result, pd.DataFrame)

    def test_has_all_policies(self, all_results):
        result = gini_by_policy(all_results)
        policy_names = set(result["policy"].values)
        expected = {p.name for p in ALL_POLICIES}
        assert policy_names == expected

    def test_has_required_columns(self, all_results):
        result = gini_by_policy(all_results)
        for col in ["policy", "gini_mean", "gini_std", "ci_lower", "ci_upper"]:
            assert col in result.columns

    def test_gini_values_between_0_and_1(self, all_results):
        result = gini_by_policy(all_results)
        assert (result["gini_mean"] >= 0.0).all()
        assert (result["gini_mean"] <= 1.0).all()

    def test_ci_lower_leq_ci_upper(self, all_results):
        result = gini_by_policy(all_results)
        assert (result["ci_lower"] <= result["ci_upper"]).all()


# ─────────────────────────────────────────────
# TESTES: summary_statistics
# ─────────────────────────────────────────────

class TestSummaryStatistics:
    def test_returns_dataframe(self, df):
        result = summary_statistics(df, "avg_wait_time")
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self, df):
        result = summary_statistics(df, "avg_wait_time")
        for col in ["policy", "mean", "std", "ci_lower", "ci_upper", "n"]:
            assert col in result.columns

    def test_has_all_policies(self, df):
        result = summary_statistics(df, "avg_wait_time")
        assert set(result["policy"]) == {p.name for p in ALL_POLICIES}

    def test_mean_inside_ci(self, df):
        result = summary_statistics(df, "avg_wait_time")
        for _, row in result.iterrows():
            assert row["ci_lower"] <= row["mean"] <= row["ci_upper"]

    def test_std_non_negative(self, df):
        result = summary_statistics(df, "avg_wait_time")
        assert (result["std"] >= 0).all()

    def test_n_equals_replicas(self, df):
        """Cada política tem 5 réplicas."""
        result = summary_statistics(df, "avg_wait_time")
        assert (result["n"] == 5).all()

    def test_invalid_metric_raises_value_error(self, df):
        with pytest.raises(ValueError, match="não encontrada"):
            summary_statistics(df, "metrica_que_nao_existe")

    def test_throughput_metric(self, df):
        """Throughput deve ser analisável."""
        result = summary_statistics(df, "throughput")
        assert len(result) == 4  # 4 políticas

    def test_renege_rate_metric(self, df):
        result = summary_statistics(df, "renege_rate")
        assert (result["mean"] >= 0).all()
        assert (result["mean"] <= 1).all()


# ─────────────────────────────────────────────
# TESTES: compare_policies
# ─────────────────────────────────────────────

class TestComparePolicies:
    def test_returns_dataframe(self, df):
        result = compare_policies(df, "avg_wait_time")
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self, df):
        result = compare_policies(df, "avg_wait_time")
        for col in ["policy_a", "policy_b", "statistic", "p_value",
                    "significant", "effect_size"]:
            assert col in result.columns

    def test_correct_number_of_pairs(self, df):
        """4 políticas → C(4,2) = 6 pares."""
        result = compare_policies(df, "avg_wait_time")
        assert len(result) == 6

    def test_p_values_between_0_and_1(self, df):
        result = compare_policies(df, "avg_wait_time")
        assert (result["p_value"] >= 0.0).all()
        assert (result["p_value"] <= 1.0).all()

    def test_effect_size_non_negative(self, df):
        result = compare_policies(df, "avg_wait_time")
        assert (result["effect_size"] >= 0.0).all()

    def test_significant_is_boolean(self, df):
        result = compare_policies(df, "avg_wait_time")
        assert result["significant"].dtype == bool

    def test_no_self_comparisons(self, df):
        """Não deve haver comparações de uma política consigo mesma."""
        result = compare_policies(df, "avg_wait_time")
        for _, row in result.iterrows():
            assert row["policy_a"] != row["policy_b"]

    def test_sorted_by_p_value(self, df):
        """Resultados devem estar ordenados por p_value ascendente."""
        result = compare_policies(df, "avg_wait_time")
        p_values = result["p_value"].values
        assert all(p_values[i] <= p_values[i+1] for i in range(len(p_values)-1))

    def test_invalid_metric_raises(self, df):
        with pytest.raises(ValueError):
            compare_policies(df, "metrica_invalida")

    def test_custom_alpha(self, df):
        """Alpha diferente muda o resultado de 'significant'."""
        result_05  = compare_policies(df, "avg_wait_time", alpha=0.05)
        result_001 = compare_policies(df, "avg_wait_time", alpha=0.001)
        # Com alpha mais baixo, menos comparações são significativas
        assert result_001["significant"].sum() <= result_05["significant"].sum()


# ─────────────────────────────────────────────
# TESTES: full_report
# ─────────────────────────────────────────────

class TestFullReport:
    def test_returns_dict(self, all_results, df):
        report = full_report(all_results, df)
        assert isinstance(report, dict)

    def test_has_required_keys(self, all_results, df):
        report = full_report(all_results, df)
        assert "summary" in report
        assert "comparisons" in report
        assert "gini" in report

    def test_summary_is_dict_of_dataframes(self, all_results, df):
        report = full_report(all_results, df)
        assert isinstance(report["summary"], dict)
        for metric, result in report["summary"].items():
            assert isinstance(result, pd.DataFrame), f"summary['{metric}'] não é DataFrame"

    def test_comparisons_is_dict_of_dataframes(self, all_results, df):
        report = full_report(all_results, df)
        assert isinstance(report["comparisons"], dict)
        for metric, result in report["comparisons"].items():
            assert isinstance(result, pd.DataFrame)

    def test_gini_is_dataframe(self, all_results, df):
        report = full_report(all_results, df)
        assert isinstance(report["gini"], pd.DataFrame)

    def test_avg_wait_time_in_summary(self, all_results, df):
        report = full_report(all_results, df)
        assert "avg_wait_time" in report["summary"]

    def test_throughput_in_summary(self, all_results, df):
        report = full_report(all_results, df)
        assert "throughput" in report["summary"]

    def test_renege_rate_in_summary(self, all_results, df):
        report = full_report(all_results, df)
        assert "renege_rate" in report["summary"]

    def test_gini_has_all_policies(self, all_results, df):
        report = full_report(all_results, df)
        gini_policies = set(report["gini"]["policy"].values)
        expected = {p.name for p in ALL_POLICIES}
        assert gini_policies == expected