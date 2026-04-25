"""
simulation/events.py - Processos de eventos dos agentes no SimPy
Define o ciclo de vida completo de um agente: chegada → fila → palco → saída.
"""

import simpy
import math
from src.coachella.utils.logger import get_logger
from src.coachella.config import (
    SERVICE_TIME_MEAN, SERVICE_TIME_STD,
    NUM_AGENTS, MAX_WAIT_FOR_SHOW, STAGES,
    AGENT_MOVE_SPEED, ARRIVAL_WAVES, MAX_QUEUE_LENGTH
)
from src.coachella.simulation.environment import FestivalEnvironment, Stage
from src.coachella.simulation.agents import Agent, AgentType, create_agent
from src.coachella.data.lineup import get_active_show, get_next_show, get_shows_at_stage

logger = get_logger(__name__)

from src.coachella.simulation.policies import (
    BASELINE, PRIORITY_VIP, PRIORITY_FAN, PRIORITY_GENERAL
)

AGENT_PRIORITY = {
    AgentType.VIP:     PRIORITY_VIP,
    AgentType.FAN:     PRIORITY_FAN,
    AgentType.GENERAL: PRIORITY_GENERAL,
}

# ─────────────────────────────────────────────
# PROCESSO: MOVIMENTO VISUAL
# ─────────────────────────────────────────────

def move_agent(env: simpy.Environment, agent: Agent, target_x: float, target_y: float):
    """
    Processo SimPy puramente visual — move o agente da posição atual ao destino.
    Não tem impacto na lógica da simulação, só na visualização.
    """
    agent.status = "moving"

    dx = target_x - agent.x
    dy = target_y - agent.y
    distance = math.sqrt(dx ** 2 + dy ** 2)

    if distance < 1:
        yield env.timeout(0)
        return

    travel_time = distance / AGENT_MOVE_SPEED
    steps = max(1, int(travel_time * 30))
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
    Gere o ciclo de vida dos concertos num palco.
    Abre o palco no início de cada show e fecha-o no fim.
    Usa o lineup.py como fonte de verdade dos horários.
    """
    shows = get_shows_at_stage(stage.name)  # já ordenados por start

    for show in shows:
        wait = show["start"] - env.now
        if wait > 0:
            yield env.timeout(wait)

        stage.is_open = True
        logger.info("t=%.1f | '%s' — %s iniciou!", env.now, stage.name, show["artist"])

        yield env.timeout(show["duration"])

        stage.is_open = False
        logger.info("t=%.1f | '%s' — %s terminou.", env.now, stage.name, show["artist"])

    logger.info("'%s' — sem mais shows.", stage.name)


# ─────────────────────────────────────────────
# HELPER: ESCOLHA DE PALCO INTELIGENTE
# ─────────────────────────────────────────────

def choose_stage_for_agent(agent: Agent, festival: FestivalEnvironment,
                            exclude: list[str] = None) -> Stage | None:
    """
    Escolhe o palco para um agente com base nos seus artistas favoritos.

    Lógica:
    - Se houver um artista favorito a tocar agora ou em breve (< MAX_WAIT_FOR_SHOW),
      o agente tenta ir a esse palco primeiro.
    - Caso contrário, usa a escolha ponderada por popularidade normal.
    """
    exclude = exclude or []

    # ── App informativa: evitar palcos congestionados ─────────────────
    if festival.policy.app_enabled and festival.policy.agent_uses_app(agent.agent_type.value, festival.rng):
        non_congested = [
            name for name, stage in festival.stages.items()
            if name not in exclude
               and not festival.get_stage_info_for_agent(name)["is_congested"]
               and stage.queue_length < MAX_QUEUE_LENGTH
        ]
        if non_congested:
            exclude_congested = [
                name for name in festival.stages
                if name not in non_congested
            ]
            exclude = list(set(exclude + exclude_congested))

    # Verificar se algum favorito está a tocar ou vai tocar em breve
    for artist in agent.favorite_artists:
        show = get_next_show_or_active(artist, festival.env.now)
        if show is None:
            continue
        stage_name = show["stage"]
        if stage_name in exclude:
            continue
        stage = festival.stages.get(stage_name)
        if stage is None or stage.queue_length >= 50:
            continue

        # Show ativo ou a começar dentro do threshold de espera
        time_until = max(0.0, show["start"] - festival.env.now)
        if time_until <= MAX_WAIT_FOR_SHOW:
            logger.debug("t=%.1f | Agent %d → favorito '%s' em '%s' (em %.1f min)",
                         festival.env.now, agent.id, artist, stage_name, time_until)
            return stage

    # Fallback: escolha ponderada por popularidade
    return festival.choose_stage(exclude=exclude, agent_type=agent.agent_type)


def get_next_show_or_active(artist: str, current_time: float) -> dict | None:
    """
    Retorna o show de um artista se estiver ativo agora ou ainda por começar.
    """
    from src.coachella.data.lineup import get_show
    show = get_show(artist)
    if show is None:
        return None
    end_time = show["start"] + show["duration"]
    if current_time <= end_time:
        return show
    return None


# ─────────────────────────────────────────────
# PROCESSO: VISITA AO PALCO
# ─────────────────────────────────────────────

def visit_stage(env: simpy.Environment, agent: Agent, stage: Stage,
                festival: FestivalEnvironment):
    """
    Ciclo de vida completo de um agente num palco:
    mover → verificar show → fila (com renege) → assistir → sair.
    """
    # ── 1. Mover até ao palco (visual) ───────────────────────────────
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

        agent.status = "waiting_show"
        agent.current_stage = stage.name
        logger.debug("t=%.1f | Agent %d — aguarda show em '%s' (%.1f min).",
                     env.now, agent.id, stage.name, next_show)
        yield env.timeout(next_show)

    # ── 3. Determinar paciência para este palco ───────────────────────
    active = get_active_show(stage.name, env.now)
    current_artist = active["artist"] if active else None
    agent.patience = agent.get_patience_for(current_artist, festival.np_rng)

    # ── 4. Entrar na fila ─────────────────────────────────────────────
    arrival_time = env.now
    agent.status = "queuing"
    agent.current_stage = stage.name

    logger.debug("t=%.1f | Agent %d [%s] → fila '%s' (paciência: %.1f min)",
                 env.now, agent.id, agent.agent_type.value, stage.name, agent.patience)

    priority = AGENT_PRIORITY.get(agent.agent_type, PRIORITY_GENERAL)
    req_kwargs = {"priority": priority} if festival.policy.vip_priority else {}
    with stage.resource.request(**req_kwargs) as request:
        result = yield request | env.timeout(agent.patience)

        if request in result:
            # ── Conseguiu entrar ──────────────────────────────────────
            wait_time = env.now - arrival_time
            stage.record_wait(wait_time)
            stage.total_served += 1
            agent.total_wait_time += wait_time
            agent.status = "watching"

            logger.debug("t=%.1f | Agent %d entrou em '%s' (espera: %.1f min)",
                         env.now, agent.id, stage.name, wait_time)

            service_time = max(0.0, festival.rng.gauss(SERVICE_TIME_MEAN, SERVICE_TIME_STD))
            yield env.timeout(service_time)

            # Saída antecipada — agente sai mais cedo se leaves_early
            if agent.leaves_early:
                actual_watch = agent.watch_duration * festival.rng.uniform(0.3, 0.8)
            else:
                actual_watch = agent.watch_duration
            yield env.timeout(actual_watch)

            festival.served_by_profile[agent.agent_type] += 1

            # Registar artista favorito visto
            if current_artist:
                agent.record_favorite_seen(current_artist)
                if agent.is_favorite(current_artist):
                    logger.debug("t=%.1f | Agent %d [%s] viu favorito '%s'! 🎵",
                                 env.now, agent.id, agent.agent_type.value, current_artist)

            if stage.name not in agent.stages_visited:
                agent.stages_visited.append(stage.name)

            agent.status = "leaving"
            logger.debug("t=%.1f | Agent %d saiu de '%s'", env.now, agent.id, stage.name)

        else:
            # ── Desistiu da fila (renege) ─────────────────────────────
            stage.total_reneged += 1
            agent.reneged = True
            festival.reneged_by_profile[agent.agent_type] += 1
            agent.status = "leaving"
            time_spent = env.now - arrival_time

            logger.debug("t=%.1f | Agent %d [%s] desistiu da fila '%s' após %.1f min",
                         env.now, agent.id, agent.agent_type.value, stage.name, time_spent)

            # ── Gestão ativa: recomendar alternativa ──────────────────
            # Se o palco está congestionado e o agente segue a recomendação,
            # exclui explicitamente este palco da próxima tentativa.
            # Caso contrário, comportamento normal (já exclui o palco atual).
            if (festival.policy.active_management
                    and festival.policy.is_congested(stage.occupancy, stage.capacity)
                    and festival.policy.agent_follows_recommendation(
                        agent.agent_type.value, festival.rng)):
                logger.debug("t=%.1f | Agent %d [%s] seguiu recomendação — evita '%s'",
                             festival.env.now, agent.id, agent.agent_type.value, stage.name)

            yield env.process(try_another_stage(env, agent, festival,
                                                exclude=[stage.name],
                                                time_spent=time_spent))

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

    alternative = choose_stage_for_agent(agent, festival, exclude=exclude)

    if alternative is not None:
        logger.debug("t=%.1f | Agent %d tenta alternativa: '%s'",
                     env.now, agent.id, alternative.name)
        yield env.process(visit_stage(env, agent, alternative, festival))
    else:
        agent.status = "leaving"
        logger.debug("t=%.1f | Agent %d foi embora (sem alternativas)", env.now, agent.id)
        yield env.timeout(0)


# ─────────────────────────────────────────────
# PROCESSO: CHEGADA DE AGENTES (ondas temporais)
# ─────────────────────────────────────────────

def agent_arrivals(env: simpy.Environment, festival: FestivalEnvironment):
    """
    Simula a chegada de agentes ao festival em ondas temporais.

    Em vez de uma taxa constante, usa ARRIVAL_WAVES para modelar:
    - Abertura tranquila
    - Aquecimento a meio do dia
    - Pico pré-headliners
    - Abrandamento durante os headliners

    Cada onda tem uma taxa Poisson própria (expovariate).
    O número total de agentes é distribuído proporcionalmente pela duração de cada onda.
    """
    Agent.reset_counter()

    total_duration = sum(w["end"] - w["start"] for w in ARRIVAL_WAVES)

    # Distribuir agentes pelas ondas sem perder nenhum por arredondamento
    wave_counts = []
    remaining = NUM_AGENTS
    for i, wave in enumerate(ARRIVAL_WAVES):
        if i == len(ARRIVAL_WAVES) - 1:
            wave_counts.append(remaining)
        else:
            wave_duration = wave["end"] - wave["start"]
            count = round(NUM_AGENTS * (wave_duration / total_duration))
            wave_counts.append(count)
            remaining -= count

    for wave, wave_agents in zip(ARRIVAL_WAVES, wave_counts):
        rate = wave["rate"]

        for _ in range(wave_agents):
            interarrival = festival.rng.expovariate(rate)
            yield env.timeout(interarrival)

            agent = create_agent(festival.rng, festival.np_rng)
            festival.active_agents.append(agent)

            stage = choose_stage_for_agent(agent, festival)

            if stage is not None:
                logger.debug("t=%.1f | Agent %d [%s] chegou → '%s'",
                             env.now, agent.id, agent.agent_type.value, stage.name)
                env.process(visit_stage(env, agent, stage, festival))
            else:
                agent.status = "leaving"
                festival.active_agents.remove(agent)
                logger.debug("t=%.1f | Agent %d foi embora (festival cheio)", env.now, agent.id)