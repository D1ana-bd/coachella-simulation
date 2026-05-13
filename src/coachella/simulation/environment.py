"""
simulation/environment.py - Ambiente central da simulação SimPy
Gere os palcos, filas de espera, recursos e recolha de métricas.
"""

import simpy
import random
import numpy as np
import logging
import csv
import os
from src.coachella.config import (
    STAGES, MAX_QUEUE_LENGTH, SERVICE_TIME_MEAN, SERVICE_TIME_STD,
    METRICS_INTERVAL, METRICS_FILE, OUTPUT_DIR
)

from src.coachella.data.lineup import (
    get_active_show, get_next_show, get_shows_at_stage
)


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# STAGE RESOURCE
# ─────────────────────────────────────────────

class Stage:
    """
    Representa um palco no festival.
    Usa simpy.Resource para controlar capacidade e fila de entrada.
    """

    def __init__(self, env: simpy.Environment, name: str, config: dict, policy=None):
        self.env = env
        self.name = name
        self.capacity = config["capacity"]
        self.popularity = config["popularity"]
        # horários vêm do lineup.py — não estão no config
        self.x = config["x"]
        self.y = config["y"]
        self.is_open = False  # palco fechado até ao primeiro show
        self.vip_only = config.get("vip_only", False)


        # Recurso SimPy: PriorityResource se política VIP, Resource normal caso contrário
        if policy is not None and policy.vip_priority:
            self.resource = simpy.PriorityResource(env, capacity=self.capacity)
        else:
            self.resource = simpy.Resource(env, capacity=self.capacity)

        # Métricas internas
        self.total_served = 0
        self.total_reneged = 0      # agentes que desistiram da fila
        self.wait_times = []        # lista de tempos de espera registados

    @property
    def occupancy(self) -> int:
        """Número de agentes atualmente dentro do palco."""
        return self.resource.count

    @property
    def queue_length(self) -> int:
        """Número de agentes à espera na fila."""
        return len(self.resource.queue)

    @property
    def is_full(self) -> bool:
        return self.occupancy >= self.capacity

    def has_active_show(self) -> bool:
        return get_active_show(self.name, self.env.now) is not None

    def next_show_in(self) -> float:
        show = get_next_show(self.name, self.env.now)
        return show["start"] - self.env.now if show else -1

    def record_wait(self, wait: float):
        self.wait_times.append(wait)

    def avg_wait_time(self) -> float:
        if not self.wait_times:
            return 0.0
        return sum(self.wait_times) / len(self.wait_times)

    def snapshot(self) -> dict:
        active = get_active_show(self.name, self.env.now)
        return {
            "stage": self.name,
            "time": round(self.env.now, 2),
            "occupancy": self.occupancy,
            "queue_length": self.queue_length,
            "total_served": self.total_served,
            "total_reneged": self.total_reneged,
            "avg_wait_time": round(self.avg_wait_time(), 2),
            "active_show": active is not None,
            "current_artist": active["artist"] if active else None,
        }


# ─────────────────────────────────────────────
# FESTIVAL ENVIRONMENT
# ─────────────────────────────────────────────

class FestivalEnvironment:
    """
    Ambiente principal da simulação.
    Inicializa o SimPy, cria os palcos e gere a recolha de métricas.
    """

    def __init__(self, seed: int = 42, policy=None):
        self.env = simpy.Environment()
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        # Agentes ativos (para visualização)
        self.active_agents: list = []
        self.all_agents: list = []  #

        from src.coachella.simulation.policies import BASELINE
        self.policy = policy or BASELINE

        self.stages: dict[str, Stage] = {
            name: Stage(self.env, name, cfg, policy=self.policy)
            for name, cfg in STAGES.items()
        }

        # Histórico de métricas (lista de snapshots)
        self.metrics_log: list[dict] = []

        # Agentes ativos (para visualização)
        self.active_agents: list = []

        from src.coachella.simulation.agents import AgentType
        self.reneged_by_profile: dict = {t: 0 for t in AgentType}
        self.served_by_profile: dict = {t: 0 for t in AgentType}

        # Garantir que o output dir existe
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        logger.info("FestivalEnvironment inicializado com %d palcos.", len(self.stages))

    # ── Escolha de palco ──────────────────────────────────────────────

    def choose_stage(self, exclude: list[str] = None, agent_type=None) -> Stage | None:
        """
        Escolhe um palco aleatoriamente, ponderado pela popularidade.
        Exclui palcos cheios, sem show, ou VIP-only para não-VIPs.
        """
        from src.coachella.simulation.agents import AgentType

        candidates = []
        for name, s in self.stages.items():
            if exclude and name in exclude:
                continue
            if s.queue_length >= MAX_QUEUE_LENGTH:
                continue
            if s.vip_only and agent_type != AgentType.VIP:
                continue
            candidates.append(s)

        if not candidates:
            return None

        weights = [s.popularity for s in candidates]
        return self.rng.choices(candidates, weights=weights, k=1)[0]

    def get_stage_info_for_agent(self, stage_name: str) -> dict:
        """
        Retorna informação sobre um palco para um agente com app.
        Simula o lag da informação — a lotação vista tem info_delay minutos de atraso.
        """
        stage = self.stages[stage_name]
        return {
            "occupancy": stage.occupancy,
            "queue_length": stage.queue_length,
            "capacity": stage.capacity,
            "is_congested": self.policy.is_congested(stage.occupancy, stage.capacity),
        }

    # ── Métricas ──────────────────────────────────────────────────────

    def collect_metrics(self):
        """Processo SimPy que recolhe snapshots a cada METRICS_INTERVAL minutos."""
        while True:
            for stage in self.stages.values():
                snap = stage.snapshot()
                self.metrics_log.append(snap)
                logger.debug("Snapshot: %s", snap)
            yield self.env.timeout(METRICS_INTERVAL)

    def save_metrics(self):
        """Guarda todas as métricas recolhidas num ficheiro CSV."""
        if not self.metrics_log:
            logger.warning("Sem métricas para guardar.")
            return

        fieldnames = self.metrics_log[0].keys()
        with open(METRICS_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.metrics_log)

        logger.info("Métricas guardadas em %s (%d registos).", METRICS_FILE, len(self.metrics_log))

    def summary(self) -> dict:
        """Resumo final da simulação por palco."""
        return {
            name: {
                "total_served": s.total_served,
                "total_reneged": s.total_reneged,
                "avg_wait_time": round(s.avg_wait_time(), 2),
            }
            for name, s in self.stages.items()
        }

    def profile_summary(self) -> dict:
        """Resumo de desistências e servidos por perfil de agente."""
        from src.coachella.simulation.agents import AgentType
        return {
            t.value: {
                "reneged": self.reneged_by_profile[t],
                "served": self.served_by_profile[t],
            }
            for t in AgentType
        }

    # ── Setup & Run ───────────────────────────────────────────────────

    def setup(self):
        self.env.process(self.collect_metrics())
        logger.info("Processos base registados.")

    def run(self, duration: float):
        """Corre a simulação até `duration` minutos."""
        self.env.run(until=duration)
        self.save_metrics()
        logger.info("Simulação terminada. Tempo final: %.1f min", self.env.now)