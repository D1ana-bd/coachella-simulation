"""
analysis/statistics.py - Análise estatística comparativa das 4 políticas.

Funções:
    confidence_interval()  — IC 95% via t-Student (n=30, amostras pequenas)
    summary_statistics()   — média, desvio padrão, IC por política
    gini_coefficient()     — desigualdade na experiência entre agentes (Política VIP)
    compare_policies()     — Mann-Whitney U test entre pares de políticas
    full_report()          — relatório completo pronto para plots e apresentação

Nota metodológica:
    Usamos Mann-Whitney U em vez de t-test porque os tempos de espera de
    simulações tendem a ter distribuições assimétricas (muitos zeros quando
    não há fila, cauda longa quando há congestionamento). Mann-Whitney é
    não-paramétrico e não assume normalidade — mais robusto e correto
    academicamente para este tipo de dados.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# INTERVALO DE CONFIANÇA
# ─────────────────────────────────────────────

def confidence_interval(data: list | np.ndarray,
                        confidence: float = 0.95) -> tuple[float, float]:
    """
    Calcula o intervalo de confiança via t-Student.

    Usa t-Student em vez de z-normal porque n=30 é uma amostra pequena —
    o t-Student é mais conservador e correto para n < 100.

    Args:
        data:       lista ou array de valores numéricos
        confidence: nível de confiança (default: 0.95)

    Returns:
        Tuplo (lower, upper) com os limites do intervalo.
        Retorna (mean, mean) se n < 2.
    """
    data = np.asarray(data, dtype=float)
    n = len(data)

    if n < 2:
        mean = float(np.mean(data)) if n == 1 else 0.0
        return (mean, mean)

    mean = np.mean(data)
    se   = stats.sem(data)          # erro padrão da média
    margin = se * stats.t.ppf((1 + confidence) / 2, df=n - 1)

    return (float(mean - margin), float(mean + margin))


# ─────────────────────────────────────────────
# ESTATÍSTICAS SUMÁRIAS POR POLÍTICA
# ─────────────────────────────────────────────

def summary_statistics(df: pd.DataFrame,
                       metric: str,
                       confidence: float = 0.95) -> pd.DataFrame:
    """
    Calcula média, desvio padrão e IC por política para uma métrica.

    Args:
        df:         DataFrame de run_all_policies() → results_to_dataframe()
        metric:     nome da coluna a analisar (ex: "avg_wait_time")
        confidence: nível de confiança para o IC (default: 0.95)

    Returns:
        DataFrame com colunas: policy, mean, std, ci_lower, ci_upper, n
        Ordenado pela média (ascendente).
    """
    if metric not in df.columns:
        raise ValueError(f"Métrica '{metric}' não encontrada no DataFrame. "
                         f"Colunas disponíveis: {list(df.columns)}")

    rows = []
    for policy_name, group in df.groupby("policy"):
        values = group[metric].dropna().values
        mean   = float(np.mean(values))
        std    = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        ci_lo, ci_hi = confidence_interval(values, confidence)

        rows.append({
            "policy":   policy_name,
            "mean":     round(mean, 4),
            "std":      round(std, 4),
            "ci_lower": round(ci_lo, 4),
            "ci_upper": round(ci_hi, 4),
            "n":        len(values),
        })

    return pd.DataFrame(rows).sort_values("mean").reset_index(drop=True)


# ─────────────────────────────────────────────
# COEFICIENTE DE GINI
# ─────────────────────────────────────────────

def gini_coefficient(wait_times: list | np.ndarray) -> float:
    """
    Calcula o coeficiente de Gini dos tempos de espera.

    O Gini mede desigualdade na experiência entre agentes:
        0.0 → todos esperam exatamente o mesmo (perfeita igualdade)
        1.0 → um agente espera tudo, os outros nada (máxima desigualdade)

    Usado para quantificar o impacto de equidade da Política VIP:
    esperamos que VIP Priority tenha Gini mais alto que Baseline.

    Fórmula: G = (2 * sum(i * x_i)) / (n * sum(x_i)) - (n+1)/n
    onde x_i são os valores ordenados.

    Args:
        wait_times: lista de tempos de espera individuais

    Returns:
        Coeficiente de Gini entre 0.0 e 1.0.
        Retorna 0.0 se todos os valores forem iguais ou lista vazia.
    """
    wait_times = np.asarray(wait_times, dtype=float)
    wait_times = wait_times[wait_times >= 0]  # remover negativos (não devem existir)

    n = len(wait_times)
    if n == 0:
        return 0.0

    total = np.sum(wait_times)
    if total == 0:
        return 0.0

    sorted_wt = np.sort(wait_times)
    indices   = np.arange(1, n + 1)
    gini = (2 * np.sum(indices * sorted_wt)) / (n * total) - (n + 1) / n

    return float(np.clip(gini, 0.0, 1.0))


def gini_by_policy(all_results: dict[str, list[dict]]) -> pd.DataFrame:
    """
    Calcula o Gini médio por política usando os wait_times individuais.

    Agrega os wait_times de todas as réplicas de cada política e
    calcula o Gini médio e IC.

    Args:
        all_results: output de run_all_policies()

    Returns:
        DataFrame com colunas: policy, gini_mean, gini_std, ci_lower, ci_upper
    """
    rows = []
    for policy_name, replicas in all_results.items():
        gini_values = []
        for replica in replicas:
            wt = replica.get("wait_times", [])
            if wt:
                gini_values.append(gini_coefficient(wt))

        if not gini_values:
            continue

        mean   = float(np.mean(gini_values))
        std    = float(np.std(gini_values, ddof=1)) if len(gini_values) > 1 else 0.0
        ci_lo, ci_hi = confidence_interval(gini_values)

        rows.append({
            "policy":     policy_name,
            "gini_mean":  round(mean, 4),
            "gini_std":   round(std, 4),
            "ci_lower":   round(ci_lo, 4),
            "ci_upper":   round(ci_hi, 4),
            "n_replicas": len(gini_values),
        })

    return pd.DataFrame(rows).sort_values("gini_mean").reset_index(drop=True)


# ─────────────────────────────────────────────
# COMPARAÇÃO ENTRE POLÍTICAS (Mann-Whitney U)
# ─────────────────────────────────────────────

def compare_policies(df: pd.DataFrame,
                     metric: str,
                     alpha: float = 0.05) -> pd.DataFrame:
    """
    Testa se há diferenças estatisticamente significativas entre pares de políticas.

    Usa Mann-Whitney U (não-paramétrico) em vez de t-test porque:
    - Tempos de espera têm distribuições assimétricas (não Normais)
    - Mann-Whitney não assume normalidade
    - É mais robusto para amostras de simulação

    Para cada par (A, B):
        H0: as distribuições de A e B são iguais
        H1: as distribuições são diferentes (two-sided)

    Args:
        df:     DataFrame com coluna "policy" e a métrica
        metric: métrica a comparar
        alpha:  nível de significância (default: 0.05)

    Returns:
        DataFrame com colunas:
            policy_a, policy_b, statistic, p_value, significant, effect_size
        effect_size: r = Z / sqrt(N) — convenção de Cohen para Mann-Whitney
    """
    if metric not in df.columns:
        raise ValueError(f"Métrica '{metric}' não encontrada.")

    policies = df["policy"].unique()
    rows = []

    for i, pol_a in enumerate(policies):
        for pol_b in policies[i + 1:]:
            values_a = df[df["policy"] == pol_a][metric].dropna().values
            values_b = df[df["policy"] == pol_b][metric].dropna().values

            if len(values_a) < 2 or len(values_b) < 2:
                continue

            stat, p_value = stats.mannwhitneyu(
                values_a, values_b, alternative="two-sided"
            )

            # Effect size r = Z / sqrt(N)
            n_total = len(values_a) + len(values_b)
            z_score = stats.norm.ppf(1 - p_value / 2)
            effect_size = abs(z_score) / np.sqrt(n_total)

            rows.append({
                "policy_a":    pol_a,
                "policy_b":    pol_b,
                "statistic":   round(float(stat), 4),
                "p_value":     round(float(p_value), 6),
                "significant": bool(p_value < alpha),
                "effect_size": round(float(effect_size), 4),
            })

    return pd.DataFrame(rows).sort_values("p_value").reset_index(drop=True)


# ─────────────────────────────────────────────
# RELATÓRIO COMPLETO
# ─────────────────────────────────────────────

def full_report(all_results: dict[str, list[dict]],
                df: pd.DataFrame) -> dict:
    """
    Gera um relatório completo com todas as análises estatísticas.

    Agrega summary_statistics, compare_policies e gini_by_policy
    para as métricas principais, num único dict pronto para
    passar ao plots.py ou exportar para a apresentação.

    Args:
        all_results: output de run_all_policies() (para Gini)
        df:          DataFrame de results_to_dataframe()

    Returns:
        Dict com chaves:
            "summary"       → dict {metric: DataFrame de summary_statistics}
            "comparisons"   → dict {metric: DataFrame de compare_policies}
            "gini"          → DataFrame de gini_by_policy
    """
    key_metrics = [
        "avg_wait_time",
        "throughput",
        "renege_rate",
        "served_general",
        "served_vip",
        "reneged_general",
        "reneged_vip",
    ]

    # Filtrar métricas que existem no DataFrame
    available_metrics = [m for m in key_metrics if m in df.columns]

    summary     = {}
    comparisons = {}

    for metric in available_metrics:
        try:
            summary[metric]     = summary_statistics(df, metric)
            comparisons[metric] = compare_policies(df, metric)
        except Exception as e:
            logger.warning("Erro ao calcular estatísticas para '%s': %s", metric, e)

    gini = gini_by_policy(all_results)

    logger.info("Relatório completo gerado: %d métricas analisadas.", len(summary))

    return {
        "summary":     summary,
        "comparisons": comparisons,
        "gini":        gini,
    }