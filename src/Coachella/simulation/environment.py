"""
simulation/environment.py - Ambiente central da simulação SimPy
Gere os palcos, filas de espera, recursos e recolha de métricas.
"""

import simpy
import random
import logging
import csv
import os
from config import (
    STAGES, MAX_QUEUE_LENGTH, SERVICE_TIME_MEAN, SERVICE_TIME_STD,
    METRICS_INTERVAL, METRICS_FILE, OUTPUT_DIR
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

    def __init__(self, env: simpy.Environment, name: str, config: dict):
        self.env = env
        self.name = name
        self.capacity = config["capacity"]
        self.popularity = config["popularity"]
        self.show_duration = config["show_duration"]
        self.shows_start = config["shows_start"]
        self.x = config["x"]
        self.y = config["y"]

        # Recurso SimPy: capacidade = nº de pessoas que cabem dentro
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
        """Verifica se há algum concerto a decorrer no momento atual."""
        t = self.env.now
        for start in self.shows_start:
            if start <= t < start + self.show_duration:
                return True
        return False

    def next_show_in(self) -> float:
        """Minutos até ao próximo show (-1 se não houver mais)."""
        t = self.env.now
        upcoming = [s for s in self.shows_start if s > t]
        return min(upcoming) - t if upcoming else -1

    def record_wait(self, wait: float):
        self.wait_times.append(wait)

    def avg_wait_time(self) -> float:
        if not self.wait_times:
            return 0.0
        return sum(self.wait_times) / len(self.wait_times)

    def snapshot(self) -> dict:
        """Retorna um dicionário com o estado atual do palco (para métricas)."""
        return {
            "stage": self.name,
            "time": round(self.env.now, 2),
            "occupancy": self.occupancy,
            "queue_length": self.queue_length,
            "total_served": self.total_served,
            "total_reneged": self.total_reneged,
            "avg_wait_time": round(self.avg_wait_time(), 2),
            "active_show": self.has_active_show(),
        }


# ─────────────────────────────────────────────
# FESTIVAL ENVIRONMENT
# ─────────────────────────────────────────────

class FestivalEnvironment:
    """
    Ambiente principal da simulação.
    Inicializa o SimPy, cria os palcos e gere a recolha de métricas.
    """

    def __init__(self, seed: int = 42):
        self.env = simpy.Environment()
        self.rng = random.Random(seed)

        # Criar palcos a partir da config
        self.stages: dict[str, Stage] = {
            name: Stage(self.env, name, cfg)
            for name, cfg in STAGES.items()
        }

        # Histórico de métricas (lista de snapshots)
        self.metrics_log: list[dict] = []

        # Agentes ativos (para visualização)
        self.active_agents: list = []

        # Garantir que o output dir existe
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        logger.info("FestivalEnvironment inicializado com %d palcos.", len(self.stages))

    # ── Escolha de palco ──────────────────────────────────────────────

    def choose_stage(self, exclude: list[str] = None) -> Stage | None:
        """
        Escolhe um palco aleatoriamente, ponderado pela popularidade.
        Opcionalmente exclui palcos (ex: os que estão cheios ou sem show).
        """
        candidates = [
            s for name, s in self.stages.items()
            if (exclude is None or name not in exclude)
            and s.queue_length < MAX_QUEUE_LENGTH
        ]
        if not candidates:
            return None

        weights = [s.popularity for s in candidates]
        return self.rng.choices(candidates, weights=weights, k=1)[0]

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

    # ── Setup & Run ───────────────────────────────────────────────────

    def setup(self):
        """Regista os processos base no ambiente SimPy."""
        self.env.process(self.collect_metrics())
        logger.info("Processos base registados.")

    def run(self, duration: float):
        """Corre a simulação até `duration` minutos."""
        self.env.run(until=duration)
        self.save_metrics()
        logger.info("Simulação terminada. Tempo final: %.1f min", self.env.now)