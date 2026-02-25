"""
simulation/events.py - Processos de eventos dos agentes no SimPy
Define o ciclo de vida completo de um agente: chegada → fila → palco → saída.
"""

import simpy
import random
from src.coachella.utils.logger import get_logger
from src.coachella.config import (
    PATIENCE_MIN, PATIENCE_MAX,
    WATCH_DURATION_MIN, WATCH_DURATION_MAX,
    SERVICE_TIME_MEAN, SERVICE_TIME_STD,
    NUM_AGENTS, AGENT_SPAWN_RATE,
)
from src.coachella.simulation.environment import FestivalEnvironment, Stage

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# AGENTE
# ─────────────────────────────────────────────

class Agent:
    """
    Representa um festivaleiro.
    Cada agente tem um id único, paciência e duração de visita aleatórias.
    """

    _id_counter = 0

    def __init__(self, rng: random.Random):
        Agent._id_counter += 1
        self.id = Agent._id_counter
        self.patience = rng.uniform(PATIENCE_MIN, PATIENCE_MAX)
        self.watch_duration = rng.uniform(WATCH_DURATION_MIN, WATCH_DURATION_MAX)

        # Estado para visualização / métricas
        self.current_stage: str | None = None
        self.status: str = "arriving"  # arriving | queuing | watching | leaving

    def __repr__(self):
        return f"Agent({self.id}, status={self.status})"

    @classmethod
    def reset_counter(cls):
        """Útil para testes — reseta o contador de IDs."""
        cls._id_counter = 0


# ─────────────────────────────────────────────
# PROCESSO: VISITA AO PALCO
# ─────────────────────────────────────────────

def visit_stage(env: simpy.Environment, agent: Agent, stage: Stage, festival: FestivalEnvironment):
    """
    Processo SimPy que modela a visita de um agente a um palco.

    Fluxo:
        1. Entrar na fila (request ao recurso)
        2. Aguardar com paciência limitada (renege se demorar)
        3. Ser processado na entrada (service time)
        4. Assistir ao concerto (watch duration)
        5. Sair e libertar o recurso
    """
    arrival_time = env.now
    agent.status = "queuing"
    agent.current_stage = stage.name

    logger.debug("t=%.1f | Agent %d → fila '%s' (paciência: %.1f min)",
                 env.now, agent.id, stage.name, agent.patience)

    # Pedir lugar no palco com timeout de paciência (renege pattern do SimPy)
    with stage.resource.request() as request:
        result = yield request | env.timeout(agent.patience)

        if request in result:
            # ── Conseguiu entrar ──────────────────────────────────────
            wait_time = env.now - arrival_time
            stage.record_wait(wait_time)
            stage.total_served += 1
            agent.status = "watching"

            logger.debug("t=%.1f | Agent %d entrou em '%s' (espera: %.1f min)",
                         env.now, agent.id, stage.name, wait_time)

            # Tempo de processamento na entrada (portão)
            service_time = max(0.0, festival.rng.gauss(SERVICE_TIME_MEAN, SERVICE_TIME_STD))
            yield env.timeout(service_time)

            # Assistir ao concerto
            yield env.timeout(agent.watch_duration)

            agent.status = "leaving"
            logger.debug("t=%.1f | Agent %d saiu de '%s'", env.now, agent.id, stage.name)

        else:
            # ── Desistiu da fila (renege) ─────────────────────────────
            stage.total_reneged += 1
            agent.status = "leaving"

            logger.debug("t=%.1f | Agent %d desistiu da fila '%s' após %.1f min",
                         env.now, agent.id, stage.name, agent.patience)

            # Tenta outro palco antes de ir embora
            time_spent = env.now - arrival_time
            yield env.process(try_another_stage(env, agent, festival, exclude=[stage.name], time_spent=time_spent))

    # Remover da lista de agentes ativos
    if agent in festival.active_agents:
        festival.active_agents.remove(agent)


# ─────────────────────────────────────────────
# PROCESSO: TENTAR OUTRO PALCO
# ─────────────────────────────────────────────

def try_another_stage(env: simpy.Environment, agent: Agent, festival: FestivalEnvironment, exclude: list[str], time_spent: float = 0.0):
    """
    Após desistir de um palco, o agente tenta escolher outro.
    Se não houver alternativa, vai embora.
    """
    agent.patience = max(0.0, agent.patience - time_spent)  # desconta o tempo já gasto
    alternative = festival.choose_stage(exclude=exclude)

    if alternative is not None:
        logger.debug("t=%.1f | Agent %d tenta alternativa: '%s'",
                     env.now, agent.id, alternative.name)
        yield env.process(visit_stage(env, agent, alternative, festival))
    else:
        agent.status = "leaving"
        logger.debug("t=%.1f | Agent %d foi embora (sem alternativas)", env.now, agent.id)
        yield env.timeout(0)  # yield obrigatório num processo SimPy


# ─────────────────────────────────────────────
# PROCESSO: CHEGADA DE AGENTES
# ─────────────────────────────────────────────

def agent_arrivals(env: simpy.Environment, festival: FestivalEnvironment):
    """
    Processo gerador que simula a chegada de agentes ao festival.
    As chegadas seguem uma distribuição exponencial (processo de Poisson).
    Taxa média: AGENT_SPAWN_RATE agentes por minuto.
    """
    Agent.reset_counter()

    for _ in range(NUM_AGENTS):
        # Intervalo até à próxima chegada (distribuição exponencial)
        interarrival = festival.rng.expovariate(AGENT_SPAWN_RATE)
        yield env.timeout(interarrival)

        agent = Agent(festival.rng)
        festival.active_agents.append(agent)

        # Escolher palco de destino
        stage = festival.choose_stage()

        if stage is not None:
            logger.debug("t=%.1f | Agent %d chegou → '%s'", env.now, agent.id, stage.name)
            env.process(visit_stage(env, agent, stage, festival))
        else:
            # Festival sem capacidade disponível — agente vai embora
            agent.status = "leaving"
            festival.active_agents.remove(agent)
            logger.debug("t=%.1f | Agent %d foi embora (festival cheio)", env.now, agent.id)