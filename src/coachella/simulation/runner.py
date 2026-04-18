"""
simulation/runner.py - Executor de múltiplas réplicas por política.

Responsabilidades:
    - Correr N réplicas independentes de cada política (seed diferente por réplica)
    - Recolher métricas estruturadas de cada réplica
    - Agregar resultados prontos para análise estatística (statistics.py)

Separação de responsabilidades:
    runner.py    → recolhe dados brutos por réplica
    statistics.py → calcula Gini, intervalos de confiança, testes de hipótese
"""

import logging
import pandas as pd
from src.coachella.simulation.environment import FestivalEnvironment
from src.coachella.simulation.events import agent_arrivals, concert_scheduler
from src.coachella.simulation.policies import PolicyConfig, ALL_POLICIES
from src.coachella.simulation.agents import AgentType
from src.coachella.config import SIM_DURATION, NUM_AGENTS

logger = logging.getLogger(__name__)

# Número de réplicas padrão — 30 garante normalidade assintótica (TLC)
DEFAULT_REPLICAS = 30


# ─────────────────────────────────────────────
# EXECUÇÃO DE UMA RÉPLICA
# ─────────────────────────────────────────────

def run_single(policy: PolicyConfig, seed: int) -> dict:
    """
    Corre uma réplica completa da simulação com uma política e seed específicos.

    Cada réplica é completamente independente — seed diferente garante
    variabilidade entre réplicas e reproducibilidade dos resultados.

    Retorna um dict com todas as métricas recolhidas.
    """
    festival = FestivalEnvironment(seed=seed, policy=policy)
    env = festival.env

    # Registar processos base
    festival.setup()

    # Registar concert schedulers para cada palco
    for stage in festival.stages.values():
        env.process(concert_scheduler(env, stage))

    # Registar chegadas de agentes
    env.process(agent_arrivals(env, festival))

    # Correr simulação completa
    env.run(until=SIM_DURATION)

    # ── Recolher métricas agregadas ───────────────────────────────────
    total_served  = sum(s.total_served  for s in festival.stages.values())
    total_reneged = sum(s.total_reneged for s in festival.stages.values())
    total_agents  = total_served + total_reneged

    # Tempo médio de espera global (média ponderada por palco)
    all_wait_times = []
    for stage in festival.stages.values():
        all_wait_times.extend(stage.wait_times)
    avg_wait_time = sum(all_wait_times) / len(all_wait_times) if all_wait_times else 0.0

    # Throughput: agentes servidos por hora
    hours = SIM_DURATION / 60.0
    throughput = total_served / hours if hours > 0 else 0.0

    # Taxa de desistência global
    renege_rate = total_reneged / total_agents if total_agents > 0 else 0.0

    # Métricas por perfil
    profile_metrics = {}
    for agent_type in AgentType:
        key = agent_type.value
        served  = festival.served_by_profile.get(agent_type, 0)
        reneged = festival.reneged_by_profile.get(agent_type, 0)
        total   = served + reneged
        profile_metrics[f"served_{key}"]      = served
        profile_metrics[f"reneged_{key}"]     = reneged
        profile_metrics[f"renege_rate_{key}"] = reneged / total if total > 0 else 0.0

    # Métricas por palco
    stage_metrics = {}
    for name, stage in festival.stages.items():
        safe_name = name.lower().replace(" ", "_")
        stage_metrics[f"served_{safe_name}"]    = stage.total_served
        stage_metrics[f"reneged_{safe_name}"]   = stage.total_reneged
        stage_metrics[f"avg_wait_{safe_name}"]  = round(stage.avg_wait_time(), 2)

    result = {
        "policy":        policy.name,
        "seed":          seed,
        # Métricas globais
        "total_served":  total_served,
        "total_reneged": total_reneged,
        "avg_wait_time": round(avg_wait_time, 4),
        "throughput":    round(throughput, 4),
        "renege_rate":   round(renege_rate, 4),
        # Wait times individuais — usados para Gini e distribuições
        "wait_times":    all_wait_times,
        **profile_metrics,
        **stage_metrics,
    }

    logger.info("Réplica concluída | policy=%s seed=%d served=%d reneged=%d avg_wait=%.2f",
                policy.name, seed, total_served, total_reneged, avg_wait_time)

    return result


# ─────────────────────────────────────────────
# EXECUÇÃO DE N RÉPLICAS — UMA POLÍTICA
# ─────────────────────────────────────────────

def run_policy(policy: PolicyConfig,
               n_replicas: int = DEFAULT_REPLICAS,
               base_seed: int = 100) -> list[dict]:
    """
    Corre N réplicas independentes de uma política.

    Seeds são geradas deterministicamente a partir de base_seed:
        seed_i = base_seed + i
    Isto garante reproducibilidade total dos resultados.

    Args:
        policy:     PolicyConfig a simular
        n_replicas: número de réplicas (default: 30)
        base_seed:  seed base para a sequência de seeds

    Returns:
        Lista de dicts com métricas, uma entrada por réplica.
    """
    logger.info("A iniciar %d réplicas para política '%s'...", n_replicas, policy.name)
    results = []

    for i in range(n_replicas):
        seed = base_seed + i
        try:
            result = run_single(policy, seed=seed)
            results.append(result)
        except Exception as e:
            logger.error("Erro na réplica %d (seed=%d, policy=%s): %s",
                         i, seed, policy.name, e)

    logger.info("Política '%s' concluída: %d/%d réplicas com sucesso.",
                policy.name, len(results), n_replicas)
    return results


# ─────────────────────────────────────────────
# EXECUÇÃO DE TODAS AS POLÍTICAS
# ─────────────────────────────────────────────

def run_all_policies(n_replicas: int = DEFAULT_REPLICAS,
                     base_seed: int = 100) -> dict[str, list[dict]]:
    """
    Corre N réplicas para cada uma das 4 políticas.

    Returns:
        Dict {policy_name: [lista de métricas por réplica]}

    Exemplo:
        results = run_all_policies(n_replicas=30)
        results["Baseline"]          # lista de 30 dicts
        results["VIP Priority"][0]   # métricas da 1ª réplica VIP
    """
    all_results = {}

    for policy in ALL_POLICIES:
        all_results[policy.name] = run_policy(
            policy,
            n_replicas=n_replicas,
            base_seed=base_seed,
        )

    logger.info("Todas as políticas concluídas. Total de réplicas: %d",
                n_replicas * len(ALL_POLICIES))
    return all_results


# ─────────────────────────────────────────────
# CONVERSÃO PARA DATAFRAME
# ─────────────────────────────────────────────

def results_to_dataframe(all_results: dict[str, list[dict]]) -> pd.DataFrame:
    """
    Converte o output de run_all_policies() num DataFrame Pandas.

    Remove a coluna 'wait_times' (lista aninhada) — fica nos dicts originais
    para análise de distribuições no statistics.py.

    Returns:
        DataFrame com uma linha por réplica e colunas por métrica.
    """
    rows = []
    for policy_results in all_results.values():
        for result in policy_results:
            row = {k: v for k, v in result.items() if k != "wait_times"}
            rows.append(row)

    return pd.DataFrame(rows)