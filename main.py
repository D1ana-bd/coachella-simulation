"""
main.py - Entry point da simulação Coachella
Orquestra o SimPy, o mapa NetworkX e a visualização Pygame.
"""

import sys
import threading
import pygame
from src.coachella.utils.logger import get_logger
from src.coachella.config import (
    RANDOM_SEED, SIM_DURATION, NUM_AGENTS,
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, SIM_SPEED,
    COLORS,
)
from src.coachella.simulation import FestivalEnvironment, agent_arrivals
from src.coachella.visualization import FestivalMap

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# SIMULAÇÃO (corre numa thread separada)
# ─────────────────────────────────────────────

def run_simulation(festival: FestivalEnvironment, done_flag: threading.Event):
    """
    Corre a simulação SimPy numa thread separada para não bloquear o Pygame.
    Corre passo a passo para sincronizar com a visualização.
    Quando terminar, sinaliza através do done_flag.
    """
    import time

    logger.info("A iniciar simulação | Agentes: %d | Duração: %d min", NUM_AGENTS, SIM_DURATION)
    festival.setup()
    festival.env.process(agent_arrivals(festival.env, festival))

    # Correr passo a passo para o Pygame conseguir capturar os agentes em movimento
    while festival.env.peek() < SIM_DURATION:
        festival.env.step()
        time.sleep(0.001 / SIM_SPEED)

    festival.save_metrics()
    logger.info("Simulação concluída.")
    logger.info("Resumo final: %s", festival.summary())
    done_flag.set()


# ─────────────────────────────────────────────
# HUD — informação em tempo real
# ─────────────────────────────────────────────

def draw_hud(surface: pygame.Surface, festival: FestivalEnvironment, sim_time: float, done: bool):
    """Desenha o painel de informação no canto superior esquerdo."""
    font_title = pygame.font.SysFont("monospace", 14, bold=True)
    font_info  = pygame.font.SysFont("monospace", 12)

    # Converter minutos simulados para hora real (minuto 0 = 12:00)
    real_hours   = int(12 + sim_time // 60)
    real_minutes = int(sim_time % 60)
    clock_str    = f"{real_hours:02d}:{real_minutes:02d}"

    lines = [
        f"COACHELLA SIMULATION",
        f"Hora: {clock_str}  |  t={sim_time:.1f} min",
        f"Agentes ativos: {len(festival.active_agents)}",
        "",
        "── PALCOS ──────────────────",
    ]

    for name, stage in festival.stages.items():
        status = "CHEIO" if stage.is_full else f"{stage.occupancy}/{stage.capacity}"
        show_str = ""
        from src.coachella.data.lineup import get_active_show
        active = get_active_show(name, sim_time)
        if active:
            show_str = f" ♪ {active['artist']}"
        lines.append(f"{name[:12]}: {status} | f:{stage.queue_length}{show_str}")

    lines += ["", "── PERFIS ──────────────────"]
    for profile_name, data in festival.profile_summary().items():
        lines.append(f"{profile_name:8s}: ✓{data['served']}  ✗{data['reneged']}")

    if done:
        lines += ["", "✓ Simulação terminada!", "  Prima Q para sair."]

    # Fundo semitransparente
    panel_w = 300
    panel_h = len(lines) * 18 + 20
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 160))
    surface.blit(panel, (10, 10))

    y = 18
    for i, line in enumerate(lines):
        font = font_title if i == 0 else font_info
        text = font.render(line, True, COLORS["text"])
        surface.blit(text, (18, y))
        y += 18


# ─────────────────────────────────────────────
# LOOP PRINCIPAL PYGAME
# ─────────────────────────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Coachella Crowd Simulation — Fase 2")
    clock = pygame.time.Clock()

    # Inicializar ambiente e mapa
    festival = FestivalEnvironment(seed=RANDOM_SEED)
    festival_map = FestivalMap()

    # Correr simulação numa thread separada
    done_flag = threading.Event()
    sim_thread = threading.Thread(
        target=run_simulation,
        args=(festival, done_flag),
        daemon=True,
    )
    sim_thread.start()

    logger.info("Pygame inicializado. A correr visualização...")

    running = True
    while running:
        # ── Eventos ──────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False

        # ── Rendering ────────────────────────────────────────────────
        screen.fill(COLORS["background"])

        # Mapa (grafo + palcos + agentes)
        festival_map.draw(screen, festival=festival)

        # HUD com métricas em tempo real
        sim_time = festival.env.now
        draw_hud(screen, festival, sim_time, done=done_flag.is_set())

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    logger.info("Visualização encerrada.")
    sys.exit(0)


if __name__ == "__main__":
    main()