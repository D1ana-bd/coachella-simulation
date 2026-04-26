"""
run_analysis.py - Ponto de entrada para a análise comparativa das 4 políticas.

Uso:
    python run_analysis.py              # 30 réplicas por política (default)
    python run_analysis.py --replicas 5 # réplicas reduzidas para teste rápido

Output:
    results/dashboard.png       — dashboard com os 4 gráficos principais
    results/metrics_report.csv  — tabela comparativa das métricas
    results/gini_report.csv     — coeficiente de Gini por política
    results/comparisons/        — testes Mann-Whitney por métrica
    Terminal                    — resumo das conclusões principais
"""

import os
import sys
import argparse
import logging
import pandas as pd

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Análise comparativa das 4 políticas de gestão do festival."
    )
    parser.add_argument(
        "--replicas", type=int, default=None,
        help="Número de réplicas por política (default: NUM_REPLICAS do config.py)"
    )
    parser.add_argument(
        "--seed", type=int, default=100,
        help="Seed base para reproducibilidade (default: 100)"
    )
    parser.add_argument(
        "--output", type=str, default="results",
        help="Pasta de output para gráficos e CSVs (default: results/)"
    )
    parser.add_argument(
        "--no-plots", action="store_true",
        help="Não gerar gráficos (útil para CI ou ambientes sem display)"
    )
    return parser.parse_args()


def setup_output_dir(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "comparisons"), exist_ok=True)
    logger.info("Output dir: %s", output_dir)


# ─────────────────────────────────────────────
# RESUMO NO TERMINAL
# ─────────────────────────────────────────────

def print_summary(report: dict):
    """Imprime um resumo legível das conclusões principais."""
    print("\n" + "═" * 60)
    print("  RESUMO DA ANÁLISE COMPARATIVA")
    print("═" * 60)

    # Tempo médio de espera
    if "avg_wait_time" in report["summary"]:
        df_wait = report["summary"]["avg_wait_time"]
        best    = df_wait.iloc[0]  # menor média (já ordenado asc)
        worst   = df_wait.iloc[-1]
        print(f"\n  Tempo Médio de Espera:")
        print(f"   Melhor : {best['policy']:25s} → {best['mean']:.2f} min "
              f"(IC 95%: [{best['ci_lower']:.2f}, {best['ci_upper']:.2f}])")
        print(f"   Pior   : {worst['policy']:25s} → {worst['mean']:.2f} min")

    # Throughput
    if "throughput" in report["summary"]:
        df_tp = report["summary"]["throughput"].sort_values("mean", ascending=False)
        best  = df_tp.iloc[0]
        print(f"\n Throughput (agentes/hora):")
        print(f"   Melhor : {best['policy']:25s} → {best['mean']:.1f} ag/h")

    # Taxa de desistência
    if "renege_rate" in report["summary"]:
        df_rr = report["summary"]["renege_rate"]
        best  = df_rr.iloc[0]
        print(f"\n  Taxa de Desistência:")
        print(f"   Menor  : {best['policy']:25s} → {best['mean']:.1%}")

    # Gini
    if not report["gini"].empty:
        gini_df = report["gini"].sort_values("gini_mean")
        most_equal   = gini_df.iloc[0]
        least_equal  = gini_df.iloc[-1]
        print(f"\n   Equidade (Coeficiente de Gini):")
        print(f"   Mais igual    : {most_equal['policy']:20s} → Gini = {most_equal['gini_mean']:.3f}")
        print(f"   Mais desigual : {least_equal['policy']:20s} → Gini = {least_equal['gini_mean']:.3f}")

    # Diferenças estatisticamente significativas
    if "avg_wait_time" in report["comparisons"]:
        comp_df  = report["comparisons"]["avg_wait_time"]
        sig      = comp_df[comp_df["significant"]]
        print(f"\n Diferenças Significativas (avg_wait_time, α=0.05):")
        if sig.empty:
            print("   Nenhuma diferença significativa encontrada.")
        else:
            for _, row in sig.iterrows():
                print(f"   {row['policy_a']:22s} vs {row['policy_b']:22s} "
                      f"→ p={row['p_value']:.4f}, r={row['effect_size']:.3f}")

    print("\n" + "═" * 60 + "\n")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    args = parse_args()

    # Imports aqui para não atrasar o --help
    from src.coachella.config import NUM_REPLICAS
    from src.coachella.simulation.runner import run_all_policies, results_to_dataframe
    from src.coachella.analysis.statistics import full_report
    from src.coachella.analysis.plots import (
        plot_dashboard, plot_occupancy_over_time,
        plot_metric_comparison, plot_wait_time_distribution,
    )

    n_replicas = args.replicas or NUM_REPLICAS
    setup_output_dir(args.output)

    # ── 1. Correr simulações ──────────────────────────────────────────
    logger.info("A correr %d réplicas × 4 políticas (seed base: %d)...",
                n_replicas, args.seed)
    logger.info("Tempo estimado: ~%d segundos", n_replicas * 4 * 2)

    all_results = run_all_policies(n_replicas=n_replicas, base_seed=args.seed)
    df          = results_to_dataframe(all_results)

    # ── 2. Análise estatística ────────────────────────────────────────
    logger.info("A calcular estatísticas...")
    report = full_report(all_results, df)

    # ── 3. Guardar CSVs ───────────────────────────────────────────────
    logger.info("A guardar CSVs...")

    # Tabela comparativa principal
    summary_rows = []
    for metric, summary_df in report["summary"].items():
        summary_df = summary_df.copy()
        summary_df["metric"] = metric
        summary_rows.append(summary_df)

    if summary_rows:
        metrics_report = pd.concat(summary_rows, ignore_index=True)
        metrics_path   = os.path.join(args.output, "metrics_report.csv")
        metrics_report.to_csv(metrics_path, index=False)
        logger.info("Guardado: %s", metrics_path)

    # Gini
    gini_path = os.path.join(args.output, "gini_report.csv")
    report["gini"].to_csv(gini_path, index=False)
    logger.info("Guardado: %s", gini_path)

    # Comparações Mann-Whitney por métrica
    for metric, comp_df in report["comparisons"].items():
        safe_metric = metric.replace("/", "_")
        comp_path   = os.path.join(args.output, "comparisons", f"{safe_metric}.csv")
        comp_df.to_csv(comp_path, index=False)

    logger.info("Comparações guardadas em %s/comparisons/", args.output)

    # Raw results
    raw_path = os.path.join(args.output, "raw_results.csv")
    df.to_csv(raw_path, index=False)
    logger.info("Resultados brutos guardados: %s", raw_path)

    # ── 4. Gráficos ───────────────────────────────────────────────────
    if not args.no_plots:
        import matplotlib
        matplotlib.use("Agg")
        logger.info("A gerar gráficos...")

        # Dashboard principal
        dashboard_path = os.path.join(args.output, "dashboard.png")
        from src.coachella.analysis.plots import plot_dashboard
        plot_dashboard(all_results, df, save_path=dashboard_path)
        logger.info("Dashboard guardado: %s", dashboard_path)

        # Throughput separado
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 5))
        plot_metric_comparison(df, "throughput",
                               title="Throughput por Política",
                               ylabel="Agentes / hora",
                               ax=ax)
        tp_path = os.path.join(args.output, "throughput.png")
        fig.savefig(tp_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Throughput guardado: %s", tp_path)

    # ── 5. Resumo terminal ────────────────────────────────────────────
    print_summary(report)

    logger.info("Análise completa! Output em: %s/", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())