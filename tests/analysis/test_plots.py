"""
tests/analysis/test_plots.py - Testes para analysis/plots.py

Estratégia: usar matplotlib com backend não-interativo (Agg) para
correr testes sem abrir janelas. Verificamos que as funções retornam
os tipos corretos, que os eixos têm os labels esperados, e que
save_path guarda o ficheiro corretamente.

Não testamos o aspeto visual — isso é subjetivo. Testamos o contrato
da API: inputs → outputs corretos, sem erros.
"""

import pytest
import os
import matplotlib
matplotlib.use("Agg")   # backend não-interativo — sem janelas
import matplotlib.pyplot as plt
import matplotlib.axes
import pandas as pd
from unittest.mock import patch

from src.coachella.analysis.plots import (
    plot_metric_comparison,
    plot_wait_time_distribution,
    plot_renege_rate_by_profile,
    plot_gini_comparison,
    plot_occupancy_over_time,
    plot_dashboard,
    POLICY_COLORS,
    POLICY_ORDER,
)
from src.coachella.simulation.runner import run_all_policies, results_to_dataframe


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def all_results():
    with patch("src.coachella.simulation.runner.NUM_AGENTS", 15):
        with patch("src.coachella.simulation.runner.SIM_DURATION", 60):
            return run_all_policies(n_replicas=3, base_seed=100)


@pytest.fixture(scope="module")
def df(all_results):
    return results_to_dataframe(all_results)


@pytest.fixture(scope="module")
def sample_metrics_log():
    """Metrics log sintético para testar plot_occupancy_over_time."""
    rows = []
    for t in range(0, 61, 10):
        for stage in ["Main Stage", "Sahara Stage", "Outdoor Stage"]:
            rows.append({
                "stage": stage,
                "time": t,
                "occupancy": max(0, 10 + t // 5),
                "queue_length": 2,
                "total_served": t,
                "total_reneged": 1,
                "avg_wait_time": 5.0,
                "active_show": t > 0,
                "current_artist": "Test Artist" if t > 0 else None,
            })
    return rows


@pytest.fixture(autouse=True)
def close_figures():
    """Fecha todas as figuras após cada teste para evitar memory leaks."""
    yield
    plt.close("all")


# ─────────────────────────────────────────────
# TESTES: POLICY_COLORS e POLICY_ORDER
# ─────────────────────────────────────────────

class TestConstants:
    def test_policy_colors_has_all_policies(self):
        for policy in POLICY_ORDER:
            assert policy in POLICY_COLORS

    def test_policy_order_has_four_entries(self):
        assert len(POLICY_ORDER) == 4

    def test_policy_colors_are_hex(self):
        for color in POLICY_COLORS.values():
            assert color.startswith("#")
            assert len(color) == 7


# ─────────────────────────────────────────────
# TESTES: plot_metric_comparison
# ─────────────────────────────────────────────

class TestPlotMetricComparison:
    def test_returns_axes(self, df):
        ax = plot_metric_comparison(df, "avg_wait_time")
        assert isinstance(ax, matplotlib.axes.Axes)

    def test_accepts_existing_ax(self, df):
        fig, ax = plt.subplots()
        result = plot_metric_comparison(df, "avg_wait_time", ax=ax)
        assert result is ax

    def test_ylabel_set(self, df):
        ax = plot_metric_comparison(df, "avg_wait_time", ylabel="Minutos")
        assert ax.get_ylabel() == "Minutos"

    def test_title_set(self, df):
        ax = plot_metric_comparison(df, "avg_wait_time", title="Teste")
        assert ax.get_title() == "Teste"

    def test_correct_number_of_bars(self, df):
        ax = plot_metric_comparison(df, "avg_wait_time")
        bars = [p for p in ax.patches if hasattr(p, "get_height")]
        assert len(bars) == 4  # 4 políticas

    def test_throughput_metric(self, df):
        ax = plot_metric_comparison(df, "throughput")
        assert isinstance(ax, matplotlib.axes.Axes)

    def test_renege_rate_metric(self, df):
        ax = plot_metric_comparison(df, "renege_rate")
        assert isinstance(ax, matplotlib.axes.Axes)

    def test_saves_file(self, df, tmp_path):
        save_path = str(tmp_path / "metric_comparison.png")
        plot_metric_comparison(df, "avg_wait_time", save_path=save_path)
        assert os.path.exists(save_path)

    def test_ylim_starts_at_zero(self, df):
        ax = plot_metric_comparison(df, "avg_wait_time")
        assert ax.get_ylim()[0] == 0.0


# ─────────────────────────────────────────────
# TESTES: plot_wait_time_distribution
# ─────────────────────────────────────────────

class TestPlotWaitTimeDistribution:
    def test_returns_axes(self, all_results):
        ax = plot_wait_time_distribution(all_results)
        assert isinstance(ax, matplotlib.axes.Axes)

    def test_accepts_existing_ax(self, all_results):
        fig, ax = plt.subplots()
        result = plot_wait_time_distribution(all_results, ax=ax)
        assert result is ax

    def test_ylabel_set(self, all_results):
        ax = plot_wait_time_distribution(all_results)
        assert "Espera" in ax.get_ylabel() or "Wait" in ax.get_ylabel()

    def test_title_set(self, all_results):
        ax = plot_wait_time_distribution(all_results)
        assert ax.get_title() != ""

    def test_saves_file(self, all_results, tmp_path):
        save_path = str(tmp_path / "wait_distribution.png")
        plot_wait_time_distribution(all_results, save_path=save_path)
        assert os.path.exists(save_path)


# ─────────────────────────────────────────────
# TESTES: plot_renege_rate_by_profile
# ─────────────────────────────────────────────

class TestPlotRenegeRateByProfile:
    def test_returns_axes(self, df):
        ax = plot_renege_rate_by_profile(df)
        assert isinstance(ax, matplotlib.axes.Axes)

    def test_accepts_existing_ax(self, df):
        fig, ax = plt.subplots()
        result = plot_renege_rate_by_profile(df, ax=ax)
        assert result is ax

    def test_ylabel_set(self, df):
        ax = plot_renege_rate_by_profile(df)
        assert ax.get_ylabel() != ""

    def test_title_set(self, df):
        ax = plot_renege_rate_by_profile(df)
        assert ax.get_title() != ""

    def test_has_legend(self, df):
        ax = plot_renege_rate_by_profile(df)
        assert ax.get_legend() is not None

    def test_saves_file(self, df, tmp_path):
        save_path = str(tmp_path / "renege_profile.png")
        plot_renege_rate_by_profile(df, save_path=save_path)
        assert os.path.exists(save_path)


# ─────────────────────────────────────────────
# TESTES: plot_gini_comparison
# ─────────────────────────────────────────────

class TestPlotGiniComparison:
    def test_returns_axes(self, all_results):
        ax = plot_gini_comparison(all_results)
        assert isinstance(ax, matplotlib.axes.Axes)

    def test_accepts_existing_ax(self, all_results):
        fig, ax = plt.subplots()
        result = plot_gini_comparison(all_results, ax=ax)
        assert result is ax

    def test_ylabel_set(self, all_results):
        ax = plot_gini_comparison(all_results)
        assert "Gini" in ax.get_ylabel()

    def test_title_set(self, all_results):
        ax = plot_gini_comparison(all_results)
        assert "Gini" in ax.get_title()

    def test_correct_number_of_bars(self, all_results):
        ax = plot_gini_comparison(all_results)
        bars = [p for p in ax.patches if hasattr(p, "get_height")]
        assert len(bars) == 4

    def test_ylim_starts_at_zero(self, all_results):
        ax = plot_gini_comparison(all_results)
        assert ax.get_ylim()[0] == 0.0

    def test_saves_file(self, all_results, tmp_path):
        save_path = str(tmp_path / "gini.png")
        plot_gini_comparison(all_results, save_path=save_path)
        assert os.path.exists(save_path)


# ─────────────────────────────────────────────
# TESTES: plot_occupancy_over_time
# ─────────────────────────────────────────────

class TestPlotOccupancyOverTime:
    def test_returns_axes(self, sample_metrics_log):
        ax = plot_occupancy_over_time(sample_metrics_log, "Baseline")
        assert isinstance(ax, matplotlib.axes.Axes)

    def test_accepts_existing_ax(self, sample_metrics_log):
        fig, ax = plt.subplots()
        result = plot_occupancy_over_time(sample_metrics_log, "Baseline", ax=ax)
        assert result is ax

    def test_title_contains_policy_name(self, sample_metrics_log):
        ax = plot_occupancy_over_time(sample_metrics_log, "VIP Priority")
        assert "VIP Priority" in ax.get_title()

    def test_xlabel_set(self, sample_metrics_log):
        ax = plot_occupancy_over_time(sample_metrics_log, "Baseline")
        assert ax.get_xlabel() != ""

    def test_has_legend(self, sample_metrics_log):
        ax = plot_occupancy_over_time(sample_metrics_log, "Baseline")
        assert ax.get_legend() is not None

    def test_three_lines_for_three_stages(self, sample_metrics_log):
        ax = plot_occupancy_over_time(sample_metrics_log, "Baseline")
        assert len(ax.get_lines()) == 3

    def test_empty_metrics_log_returns_ax(self):
        """Metrics log vazio não deve lançar erro."""
        fig, ax = plt.subplots()
        result = plot_occupancy_over_time([], "Baseline", ax=ax)
        assert result is ax

    def test_saves_file(self, sample_metrics_log, tmp_path):
        save_path = str(tmp_path / "occupancy.png")
        plot_occupancy_over_time(sample_metrics_log, "Baseline",
                                 save_path=save_path)
        assert os.path.exists(save_path)


# ─────────────────────────────────────────────
# TESTES: plot_dashboard
# ─────────────────────────────────────────────

class TestPlotDashboard:
    def test_returns_figure(self, all_results, df):
        fig = plot_dashboard(all_results, df)
        assert isinstance(fig, plt.Figure)

    def test_has_four_axes(self, all_results, df):
        fig = plot_dashboard(all_results, df)
        assert len(fig.get_axes()) == 4

    def test_saves_file(self, all_results, df, tmp_path):
        save_path = str(tmp_path / "dashboard.png")
        plot_dashboard(all_results, df, save_path=save_path)
        assert os.path.exists(save_path)

    def test_figure_size(self, all_results, df):
        fig = plot_dashboard(all_results, df)
        w, h = fig.get_size_inches()
        assert w > 10 and h > 8