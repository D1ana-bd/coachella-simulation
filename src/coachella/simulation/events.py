"""
simulation/events.py - Processos de eventos dos agentes no SimPy
Define o ciclo de vida completo de um agente: chegada → fila → palco → saída.
Inclui o concert_scheduler que gere a abertura/fecho dos palcos por horários.
"""

import simpy
import random
import math
from src.coachella.utils.logger import get_logger
from src.coachella.config import (
    PATIENCE_MIN, PATIENCE_MAX,
    WATCH_DURATION_MIN, WATCH_DURATION_MAX,
    SERVICE_TIME_MEAN, SERVICE_TIME_STD,
    NUM_AGENTS, AGENT_SPAWN_RATE,
    MAX_WAIT_FOR_SHOW, STAGES,
    FESTIVAL_ENTRANCE, AGENT_MOVE_SPEED,
)
from src.coachella.simulation.environment import FestivalEnvironment, Stage

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# AGENTE
# ─────────────────────────────────────────────

class Agent:
    """
    Representa um festivaleiro.
    Cada agente tem um id único, paciência, duração de visita e posição visual.
    """

    _id_counter = 0

    def __init__(self, rng: random.Random):
        Agent._id_counter += 1
        self.id = Agent._id_counter
        self.patience = rng.uniform(PATIENCE_MIN, PATIENCE_MAX)
        self.watch_duration = rng.uniform(WATCH_DURATION_MIN, WATCH_DURATION_MAX)

        # Estado para visualização / métricas
        self.current_stage: str | None = None
        self.status: str = "arriving"   # arriving | moving | waiting_show | queuing | watching | leaving

        # Posição visual atual (começa na entrada do festival)
        self.x: float = float(FESTIVAL_ENTRANCE["x"])
        self.y: float = float(FESTIVAL_ENTRANCE["y"])

    def __repr__(self):
        return f"Agent({self.id}, status={self.status})"

    @classmethod
    def reset_counter(cls):
        """Útil para testes — reseta o contador de IDs."""
        cls._id_counter = 0


# ─────────────────────────────────────────────
# PROCESSO: MOVIMENTO VISUAL
# ─────────────────────────────────────────────

def move_agent(env: simpy.Environment, agent: Agent, target_x: float, target_y: float):
    """
    Processo SimPy que move o agente gradualmente da posição atual até ao destino.
    A velocidade é definida por AGENT_MOVE_SPEED (pixels por minuto simulado).
    """
    agent.status = "moving"

    dx = target_x - agent.x
    dy = target_y - agent.y
    distance = math.sqrt(dx ** 2 + dy ** 2)

    if distance < 1:
        yield env.timeout(0)
        return

    # Tempo de viagem em minutos simulados
    travel_time = distance / AGENT_MOVE_SPEED
    steps = max(1, int(travel_time * 30))   # ~30 steps por minuto simulado
    step_time = travel_time / steps

    for _ in range(steps):
        agent.x += dx / steps
        agent.y += dy / steps
        yield env.timeout(step_time)


# ─────────────────────────────────────────────
# PROCESSO: CONCERT SCHEDULER
# ─────────────────────────────────────────────

def concert_scheduler(env: simpy.Environment, stage: Stage):
    """
    Processo SimPy que gere o ciclo de vida dos concertos num palco.
    Abre o palco no início de cada show e fecha-o no fim.
    """
    for show_start in sorted(stage.shows_start):
        wait = show_start - env.now
        if wait > 0:
            yield env.timeout(wait)

        stage.is_open = True
        logger.info("t=%.1f | '%s' — show iniciado!", env.now, stage.name)

        yield env.timeout(stage.show_duration)

        stage.is_open = False
        logger.info("t=%.1f | '%s' — show terminado.", env.now, stage.name)

    logger.info("'%s' — sem mais shows.", stage.name)


# ─────────────────────────────────────────────
# PROCESSO: VISITA AO PALCO
# ─────────────────────────────────────────────

def visit_stage(env: simpy.Environment, agent: Agent, stage: Stage, festival: FestivalEnvironment):
    """
    Processo SimPy que modela a visita de um agente a um palco.

    Fluxo:
        1. Mover-se visualmente até ao palco
        2. Verificar se há show ativo ou próximo dentro do threshold
        3. Esperar pelo show se necessário
        4. Entrar na fila (request ao recurso)
        5. Aguardar com paciência limitada (renege se demorar)
        6. Ser processado na entrada (service time)
        7. Assistir ao concerto (watch duration)
        8. Sair e libertar o recurso
    """
    # ── 1. Mover até ao palco ─────────────────────────────────────────
    target_x = float(STAGES[stage.name]["x"])
    target_y = float(STAGES[stage.name]["y"])
    yield env.process(move_agent(env, agent, target_x, target_y))

    # ── 2. Verificar estado do palco ──────────────────────────────────
    if not stage.is_open:
        next_show = stage.next_show_in()

        if next_show == -1 or next_show > MAX_WAIT_FOR_SHOW:
            logger.debug("t=%.1f | Agent %d — '%s' fechado, sem show próximo.",
                         env.now, agent.id, stage.name)
            yield env.process(try_another_stage(env, agent, festival,
                                                exclude=[stage.name], time_spent=0.0))
            return

        # Esperar pelo próximo show
        agent.status = "waiting_show"
        agent.current_stage = stage.name
        logger.debug("t=%.1f | Agent %d — aguarda show em '%s' (%.1f min).",
                     env.now, agent.id, stage.name, next_show)
        yield env.timeout(next_show)

    # ── 3. Entrar na fila ─────────────────────────────────────────────
    arrival_time = env.now
    agent.status = "queuing"
    agent.current_stage = stage.name

    logger.debug("t=%.1f | Agent %d → fila '%s' (paciência: %.1f min)",
                 env.now, agent.id, stage.name, agent.patience)

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

            service_time = max(0.0, festival.rng.gauss(SERVICE_TIME_MEAN, SERVICE_TIME_STD))
            yield env.timeout(service_time)

            yield env.timeout(agent.watch_duration)

            agent.status = "leaving"
            logger.debug("t=%.1f | Agent %d saiu de '%s'", env.now, agent.id, stage.name)

        else:
            # ── Desistiu da fila (renege) ─────────────────────────────
            stage.total_reneged += 1
            agent.status = "leaving"
            time_spent = env.now - arrival_time

            logger.debug("t=%.1f | Agent %d desistiu da fila '%s' após %.1f min",
                         env.now, agent.id, stage.name, agent.patience)

            yield env.process(try_another_stage(env, agent, festival,
                                                exclude=[stage.name],
                                                time_spent=time_spent))

    # Remover da lista de agentes ativos
    if agent in festival.active_agents:
        festival.active_agents.remove(agent)


# ─────────────────────────────────────────────
# PROCESSO: TENTAR OUTRO PALCO
# ─────────────────────────────────────────────

def try_another_stage(env: simpy.Environment, agent: Agent, festival: FestivalEnvironment,
                      exclude: list[str], time_spent: float = 0.0):
    """
    Após desistir de um palco, o agente tenta escolher outro.
    A paciência é descontada pelo tempo já gasto.
    """
    agent.patience = max(0.0, agent.patience - time_spent)

    alternative = festival.choose_stage(exclude=exclude)

    if alternative is not None:
        logger.debug("t=%.1f | Agent %d tenta alternativa: '%s'",
                     env.now, agent.id, alternative.name)
        yield env.process(visit_stage(env, agent, alternative, festival))
    else:
        agent.status = "leaving"
        logger.debug("t=%.1f | Agent %d foi embora (sem alternativas)", env.now, agent.id)
        yield env.timeout(0)


# ─────────────────────────────────────────────
# PROCESSO: CHEGADA DE AGENTES
# ─────────────────────────────────────────────

def agent_arrivals(env: simpy.Environment, festival: FestivalEnvironment):
    """
    Processo gerador que simula a chegada de agentes ao festival.
    As chegadas seguem uma distribuição exponencial (processo de Poisson).
    """
    Agent.reset_counter()

    for _ in range(NUM_AGENTS):
        interarrival = festival.rng.expovariate(AGENT_SPAWN_RATE)
        yield env.timeout(interarrival)

        agent = Agent(festival.rng)
        festival.active_agents.append(agent)

        stage = festival.choose_stage()

        if stage is not None:
            logger.debug("t=%.1f | Agent %d chegou → '%s'", env.now, agent.id, stage.name)
            env.process(visit_stage(env, agent, stage, festival))
        else:
            agent.status = "leaving"
            festival.active_agents.remove(agent)
            logger.debug("t=%.1f | Agent %d foi embora (festival cheio)", env.now, agent.id)