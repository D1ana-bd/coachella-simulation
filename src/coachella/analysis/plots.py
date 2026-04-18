"""
analysis/plots.py - Visualizações comparativas das 4 políticas de gestão.

Cada função recebe os dados do runner/statistics e produz um gráfico
pronto para a apresentação final.

Convenções:
    - Todos os plots aceitam ax=None (standalone ou em dashboard)
    - Paleta de cores consistente por política em todos os gráficos
    - save_path opcional para guardar o ficheiro
    - Retornam o ax para composição de subplots
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from typing import Optional

from src.coachella.analysis.statistics import (
    summary_statistics,
    gini_by_policy,
    confidence_interval,
)

# ─────────────────────────────────────────────
# PALETA DE CORES — consistente em todos os gráficos
# ─────────────────────────────────────────────

POLICY_COLORS = {
    "Baseline":          "#6c757d",   # cinzento — sem intervenção
    "Informative App":   "#0d6efd",   # azul — informação
    "Active Management": "#fd7e14",   # laranja — ação
    "VIP Priority":      "#ffc107",   # dourado — VIP
}

POLICY_ORDER = ["Baseline", "Informative App", "Active Management", "VIP Priority"]


def _get_color(policy_name: str) -> str:
    return POLICY_COLORS.get(policy_name, "#333333")


def _save_if_path(fig, save_path: Optional[str]):
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")


# ─────────────────────────────────────────────
# 1. BARPLOT COM IC — comparação de métrica
# ─────────────────────────────────────────────

def plot_metric_comparison(df: pd.DataFrame,
                           metric: str,
                           title: Optional[str] = None,
                           ylabel: Optional[str] = None,
                           ax=None,
                           save_path: Optional[str] = None):
    """
    Barplot com intervalos de confiança 95% por política para uma métrica.

    Responde à pergunta central: "qual política tem melhor desempenho?"

    Args:
        df:        DataFrame de results_to_dataframe()
        metric:    coluna a visualizar (ex: "avg_wait_time")
        title:     título do gráfico (default: gerado automaticamente)
        ylabel:    label do eixo Y
        ax:        matplotlib Axes (opcional — cria figura nova se None)
        save_path: caminho para guardar o ficheiro

    Returns:
        matplotlib Axes
    """
    summary = summary_statistics(df, metric)

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(8, 5))

    # Ordenar pelas políticas na ordem definida
    summary["order"] = summary["policy"].map(
        {p: i for i, p in enumerate(POLICY_ORDER)}
    )
    summary = summary.sort_values("order").reset_index(drop=True)

    colors    = [_get_color(p) for p in summary["policy"]]
    x_pos     = np.arange(len(summary))
    bar_width = 0.5

    bars = ax.bar(x_pos, summary["mean"], width=bar_width,
                  color=colors, alpha=0.85, edgecolor="white", linewidth=1.2)

    # Intervalos de confiança
    yerr_lower = summary["mean"] - summary["ci_lower"]
    yerr_upper = summary["ci_upper"] - summary["mean"]
    ax.errorbar(x_pos, summary["mean"],
                yerr=[yerr_lower, yerr_upper],
                fmt="none", color="#333333", capsize=6, linewidth=1.5)

    # Valores em cima de cada barra
    for bar, val in zip(bars, summary["mean"]):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(yerr_upper) * 0.05,
                f"{val:.2f}", ha="center", va="bottom", fontsize=9, color="#333333")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(summary["policy"], fontsize=10)
    ax.set_ylabel(ylabel or metric.replace("_", " ").title(), fontsize=11)
    ax.set_title(title or f"{metric.replace('_', ' ').title()} por Política", fontsize=13)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(bottom=0)

    if standalone:
        plt.tight_layout()
        _save_if_path(fig, save_path)

    return ax


# ─────────────────────────────────────────────
# 2. BOXPLOT — distribuição de tempos de espera
# ─────────────────────────────────────────────

def plot_wait_time_distribution(all_results: dict,
                                ax=None,
                                save_path: Optional[str] = None):
    """
    Boxplot dos tempos de espera individuais por política.

    Mostra não só a média mas toda a distribuição — cauda longa,
    outliers e variabilidade são visíveis aqui mas não no barplot.

    Args:
        all_results: output de run_all_policies()
        ax:          matplotlib Axes (opcional)
        save_path:   caminho para guardar

    Returns:
        matplotlib Axes
    """
    # Agregar todos os wait_times de todas as réplicas por política
    data_by_policy = {}
    for policy_name in POLICY_ORDER:
        if policy_name not in all_results:
            continue
        all_wt = []
        for replica in all_results[policy_name]:
            all_wt.extend(replica.get("wait_times", []))
        if all_wt:
            data_by_policy[policy_name] = all_wt

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(9, 5))

    policies = [p for p in POLICY_ORDER if p in data_by_policy]
    data     = [data_by_policy[p] for p in policies]
    colors   = [_get_color(p) for p in policies]

    bp = ax.boxplot(data, patch_artist=True, notch=False,
                    medianprops={"color": "#333333", "linewidth": 2},
                    flierprops={"marker": "o", "markersize": 3, "alpha": 0.4})

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)

    ax.set_xticklabels(policies, fontsize=10)
    ax.set_ylabel("Tempo de Espera (min)", fontsize=11)
    ax.set_title("Distribuição de Tempos de Espera por Política", fontsize=13)
    ax.spines[["top", "right"]].set_visible(False)

    if standalone:
        plt.tight_layout()
        _save_if_path(fig, save_path)

    return ax


# ─────────────────────────────────────────────
# 3. BARPLOT AGRUPADO — renege rate por perfil
# ─────────────────────────────────────────────

def plot_renege_rate_by_profile(df: pd.DataFrame,
                                ax=None,
                                save_path: Optional[str] = None):
    """
    Barplot agrupado: taxa de desistência por perfil de agente e política.

    Mostra o impacto diferenciado das políticas em cada tipo de festivaleiro
    — análise mais profunda que as métricas globais.

    Args:
        df:        DataFrame de results_to_dataframe()
        ax:        matplotlib Axes (opcional)
        save_path: caminho para guardar

    Returns:
        matplotlib Axes
    """
    profiles    = ["general", "fan", "vip"]
    profile_labels = {"general": "General", "fan": "Fã", "vip": "VIP"}
    n_profiles  = len(profiles)
    n_policies  = len(POLICY_ORDER)
    bar_width   = 0.18
    x_pos       = np.arange(n_profiles)

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(10, 5))

    for i, policy_name in enumerate(POLICY_ORDER):
        policy_df = df[df["policy"] == policy_name]
        if policy_df.empty:
            continue

        means = []
        cis   = []
        for profile in profiles:
            col = f"renege_rate_{profile}"
            if col in policy_df.columns:
                vals = policy_df[col].dropna().values
                means.append(float(np.mean(vals)))
                lo, hi = confidence_interval(vals)
                cis.append(hi - float(np.mean(vals)))
            else:
                means.append(0.0)
                cis.append(0.0)

        offset = (i - n_policies / 2 + 0.5) * bar_width
        bars = ax.bar(x_pos + offset, means, width=bar_width,
                      color=_get_color(policy_name), alpha=0.85,
                      label=policy_name, edgecolor="white")
        ax.errorbar(x_pos + offset, means, yerr=cis,
                    fmt="none", color="#333333", capsize=4, linewidth=1.2)

    ax.set_xticks(x_pos)
    ax.set_xticklabels([profile_labels[p] for p in profiles], fontsize=11)
    ax.set_ylabel("Taxa de Desistência", fontsize=11)
    ax.set_title("Taxa de Desistência por Perfil e Política", fontsize=13)
    ax.legend(fontsize=9, framealpha=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(bottom=0, top=min(1.0, ax.get_ylim()[1] * 1.2))

    if standalone:
        plt.tight_layout()
        _save_if_path(fig, save_path)

    return ax


# ─────────────────────────────────────────────
# 4. BARPLOT GINI — equidade entre políticas
# ─────────────────────────────────────────────

def plot_gini_comparison(all_results: dict,
                         ax=None,
                         save_path: Optional[str] = None):
    """
    Barplot do coeficiente de Gini médio por política.

    Visualiza o impacto de equidade — esperamos que VIP Priority
    tenha Gini mais alto, confirmando que cria mais desigualdade
    na experiência dos festivaleiros.

    Gini = 0: todos esperam o mesmo (igualdade perfeita)
    Gini = 1: máxima desigualdade

    Args:
        all_results: output de run_all_policies()
        ax:          matplotlib Axes (opcional)
        save_path:   caminho para guardar

    Returns:
        matplotlib Axes
    """
    gini_df = gini_by_policy(all_results)

    # Ordenar por POLICY_ORDER
    gini_df["order"] = gini_df["policy"].map(
        {p: i for i, p in enumerate(POLICY_ORDER)}
    )
    gini_df = gini_df.sort_values("order").reset_index(drop=True)

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(8, 5))

    colors  = [_get_color(p) for p in gini_df["policy"]]
    x_pos   = np.arange(len(gini_df))

    bars = ax.bar(x_pos, gini_df["gini_mean"], width=0.5,
                  color=colors, alpha=0.85, edgecolor="white", linewidth=1.2)

    # IC
    yerr_lower = gini_df["gini_mean"] - gini_df["ci_lower"]
    yerr_upper = gini_df["ci_upper"]  - gini_df["gini_mean"]
    ax.errorbar(x_pos, gini_df["gini_mean"],
                yerr=[yerr_lower, yerr_upper],
                fmt="none", color="#333333", capsize=6, linewidth=1.5)

    # Valores em cima
    for bar, val in zip(bars, gini_df["gini_mean"]):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(gini_df["policy"], fontsize=10)
    ax.set_ylabel("Coeficiente de Gini", fontsize=11)
    ax.set_title("Equidade na Experiência — Coeficiente de Gini por Política", fontsize=13)
    ax.set_ylim(0, min(1.0, gini_df["ci_upper"].max() * 1.3 + 0.05))
    ax.spines[["top", "right"]].set_visible(False)

    # Anotação explicativa
    ax.text(0.98, 0.95, "Gini mais alto = mais desigualdade",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="#666666", style="italic")

    if standalone:
        plt.tight_layout()
        _save_if_path(fig, save_path)

    return ax


# ─────────────────────────────────────────────
# 5. LINHA TEMPORAL — ocupação por palco
# ─────────────────────────────────────────────

def plot_occupancy_over_time(metrics_log: list[dict],
                             policy_name: str,
                             ax=None,
                             save_path: Optional[str] = None):
    """
    Linha temporal de ocupação por palco ao longo da simulação.

    Mostra a dinâmica temporal que os gráficos estáticos não capturam:
    picos de congestionamento, efeitos dos headliners, padrões de ondas.

    Args:
        metrics_log: lista de snapshots de FestivalEnvironment.metrics_log
        policy_name: nome da política (para o título)
        ax:          matplotlib Axes (opcional)
        save_path:   caminho para guardar

    Returns:
        matplotlib Axes
    """
    if not metrics_log:
        return ax

    df_log = pd.DataFrame(metrics_log)

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(10, 5))

    stage_colors = {
        "Main Stage":    "#e63946",
        "Sahara Stage":  "#457b9d",
        "Outdoor Stage": "#2a9d8f",
    }

    for stage_name, group in df_log.groupby("stage"):
        group = group.sort_values("time")
        color = stage_colors.get(stage_name, "#333333")
        ax.plot(group["time"], group["occupancy"],
                label=stage_name, color=color, linewidth=2, alpha=0.85)
        ax.fill_between(group["time"], group["occupancy"],
                        alpha=0.08, color=color)

    ax.set_xlabel("Tempo de Simulação (min)", fontsize=11)
    ax.set_ylabel("Ocupação (agentes)", fontsize=11)
    ax.set_title(f"Ocupação por Palco ao Longo do Tempo — {policy_name}", fontsize=13)
    ax.legend(fontsize=10, framealpha=0.7)
    ax.spines[["top", "right"]].set_visible(False)

    if standalone:
        plt.tight_layout()
        _save_if_path(fig, save_path)

    return ax


# ─────────────────────────────────────────────
# DASHBOARD — todos os gráficos num só
# ─────────────────────────────────────────────

def plot_dashboard(all_results: dict,
                   df: pd.DataFrame,
                   save_path: Optional[str] = None):
    """
    Dashboard com os 4 gráficos principais lado a lado.

    Layout:
        [metric_comparison (wait)]  [wait_time_distribution]
        [renege_rate_by_profile  ]  [gini_comparison        ]

    Args:
        all_results: output de run_all_policies()
        df:          DataFrame de results_to_dataframe()
        save_path:   caminho para guardar (ex: "results/dashboard.png")

    Returns:
        matplotlib Figure
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle("Comparação das 4 Políticas de Gestão — Coachella Simulation",
                 fontsize=15, fontweight="bold", y=1.01)

    plot_metric_comparison(df, "avg_wait_time",
                           title="Tempo Médio de Espera",
                           ylabel="Minutos",
                           ax=axes[0, 0])

    plot_wait_time_distribution(all_results, ax=axes[0, 1])

    plot_renege_rate_by_profile(df, ax=axes[1, 0])

    plot_gini_comparison(all_results, ax=axes[1, 1])

    plt.tight_layout()
    _save_if_path(fig, save_path)

    return fig