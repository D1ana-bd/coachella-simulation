"""
main.py - Entry point da simulação Coachella
Orquestra o SimPy, o mapa NetworkX e a visualização Pygame.
Menu inicial para selecionar política de gestão.
"""

import sys
import threading
import pygame
import pygame.gfxdraw
from src.coachella.utils.logger import get_logger
from src.coachella.config import (
    RANDOM_SEED, SIM_DURATION, NUM_AGENTS,
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, SIM_SPEED,
    COLORS,
)
from src.coachella.simulation import FestivalEnvironment, agent_arrivals
from src.coachella.simulation.policies import ALL_POLICIES
from src.coachella.visualization import FestivalMap

logger = get_logger(__name__)

# ─────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────
HUD_WIDTH      = 280          # painel lateral direito
MAP_WIDTH      = WINDOW_WIDTH - HUD_WIDTH
MAP_HEIGHT     = WINDOW_HEIGHT

# Cores extra para o menu
MENU_BG        = (15, 15, 25)
MENU_CARD      = (30, 30, 50)
MENU_CARD_HOV  = (50, 50, 90)
MENU_ACCENT    = (255, 200, 50)
MENU_TEXT      = (230, 230, 230)
MENU_SUBTEXT   = (150, 150, 170)
POLICY_COLORS  = [
    (100, 180, 255),   # Baseline     — azul claro
    (100, 220, 150),   # Informative  — verde
    (255, 160,  80),   # Active Mgmt  — laranja
    (255, 200,  50),   # VIP Priority — dourado
]

# ─────────────────────────────────────────────
# SIMULAÇÃO (thread separada)
# ─────────────────────────────────────────────

def run_simulation(festival: FestivalEnvironment, done_flag: threading.Event):
    import time
    from src.coachella.simulation.events import concert_scheduler

    logger.info("A iniciar simulação | Agentes: %d | Duração: %d min", NUM_AGENTS, SIM_DURATION)
    festival.setup()

    for stage in festival.stages.values():
        festival.env.process(concert_scheduler(festival.env, stage))

    festival.env.process(agent_arrivals(festival.env, festival))

    while festival.env.peek() < SIM_DURATION:
        festival.env.step()
        time.sleep(0.001 / SIM_SPEED)

    festival.save_metrics()
    logger.info("Simulação concluída. %s", festival.summary())
    done_flag.set()


# ─────────────────────────────────────────────
# MENU — escolha de política
# ─────────────────────────────────────────────

POLICY_DESCRIPTIONS = [
    "Sem app. Agentes escolhem livremente.",
    "App mostra filas e lotação em tempo real.",
    "Recomendações dinâmicas e controlo de acesso.",
    "Fila prioritária VIP + palco exclusivo Yuma.",
]

def draw_menu(surface: pygame.Surface, selected: int, hover: int):
    """Renderiza o ecrã de seleção de política."""
    surface.fill(MENU_BG)

    font_title  = pygame.font.SysFont("monospace", 28, bold=True)
    font_sub    = pygame.font.SysFont("monospace", 13)
    font_card   = pygame.font.SysFont("monospace", 16, bold=True)
    font_desc   = pygame.font.SysFont("monospace", 12)
    font_hint   = pygame.font.SysFont("monospace", 12)

    # ── Título ──────────────────────────────────────────────────────
    title = font_title.render("COACHELLA SIMULATION", True, MENU_ACCENT)
    surface.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 40))

    sub = font_sub.render("Seleciona uma política de gestão de multidões", True, MENU_SUBTEXT)
    surface.blit(sub, (WINDOW_WIDTH // 2 - sub.get_width() // 2, 80))

    # ── Cards de política ────────────────────────────────────────────
    card_w, card_h = 360, 90
    start_y = 130
    gap = 16

    for i, policy in enumerate(ALL_POLICIES):
        cx = WINDOW_WIDTH // 2 - card_w // 2
        cy = start_y + i * (card_h + gap)

        is_hover = (i == hover)
        is_sel   = (i == selected)

        # Fundo do card
        bg_color = MENU_CARD_HOV if is_hover else MENU_CARD
        rect = pygame.Rect(cx, cy, card_w, card_h)
        pygame.draw.rect(surface, bg_color, rect, border_radius=10)

        # Borda colorida se hover ou selecionado
        border_color = POLICY_COLORS[i] if (is_hover or is_sel) else (60, 60, 80)
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=10)

        # Número
        num = font_card.render(f"{i + 1}", True, POLICY_COLORS[i])
        surface.blit(num, (cx + 18, cy + card_h // 2 - num.get_height() // 2))

        # Nome da política
        name_surf = font_card.render(policy.name, True, MENU_TEXT)
        surface.blit(name_surf, (cx + 50, cy + 20))

        # Descrição
        desc_surf = font_desc.render(POLICY_DESCRIPTIONS[i], True, MENU_SUBTEXT)
        surface.blit(desc_surf, (cx + 50, cy + 48))

        # Badge "▶ ENTER" se hover
        if is_hover:
            badge = font_hint.render("▶  ENTER para iniciar", True, POLICY_COLORS[i])
            surface.blit(badge, (cx + card_w - badge.get_width() - 16,
                                 cy + card_h - badge.get_height() - 10))

    # ── Hint de navegação ────────────────────────────────────────────
    hint_y = start_y + len(ALL_POLICIES) * (card_h + gap) + 20
    hints = [
        "↑ ↓  ou  1 2 3 4  para navegar",
        "ENTER  para iniciar   |   Q  para sair",
    ]
    for line in hints:
        h = font_hint.render(line, True, MENU_SUBTEXT)
        surface.blit(h, (WINDOW_WIDTH // 2 - h.get_width() // 2, hint_y))
        hint_y += 22


# ─────────────────────────────────────────────
# HUD LATERAL — informação em tempo real
# ─────────────────────────────────────────────

def draw_hud(surface: pygame.Surface, festival: FestivalEnvironment,
             sim_time: float, done: bool, policy_name: str):
    """Desenha o painel lateral direito com métricas em tempo real."""
    from src.coachella.data.lineup import get_active_show

    font_title = pygame.font.SysFont("monospace", 13, bold=True)
    font_info  = pygame.font.SysFont("monospace", 11)
    font_small = pygame.font.SysFont("monospace", 10)

    hx = MAP_WIDTH  # início do painel
    panel = pygame.Surface((HUD_WIDTH, WINDOW_HEIGHT))
    panel.fill((18, 18, 32))

    # Linha separadora
    pygame.draw.line(panel, (60, 60, 90), (0, 0), (0, WINDOW_HEIGHT), 2)

    y = 12

    def write(text, font=font_info, color=COLORS["text"], indent=10):
        nonlocal y
        surf = font.render(text, True, color)
        panel.blit(surf, (indent, y))
        y += surf.get_height() + 3

    def separator():
        nonlocal y
        pygame.draw.line(panel, (50, 50, 70), (8, y + 2), (HUD_WIDTH - 8, y + 2))
        y += 10

    # ── Cabeçalho ────────────────────────────────────────────────────
    write("COACHELLA", font_title, MENU_ACCENT)
    write(f"Política: {policy_name}", color=MENU_SUBTEXT)

    real_h = int(12 + sim_time // 60)
    real_m = int(sim_time % 60)
    write(f"Hora:  {real_h:02d}:{real_m:02d}  (t={sim_time:.0f}m)", color=(180, 220, 255))
    write(f"Agentes ativos: {len(festival.active_agents)}")
    separator()

    # ── Palcos ───────────────────────────────────────────────────────
    write("PALCOS", font_title, MENU_ACCENT)
    y += 4

    for name, stage in festival.stages.items():
        ratio = stage.occupancy / stage.capacity if stage.capacity else 0
        if ratio >= 1.0:
            bar_color = (220, 60, 60)
        elif ratio >= 0.7:
            bar_color = (255, 165, 0)
        else:
            bar_color = (80, 200, 120)

        # Nome curto
        short = name[:14]
        write(short, font_small, COLORS["text"], indent=10)
        y -= (font_small.get_height() + 3)  # voltar para desenhar barra na mesma linha

        # Barra de ocupação
        bar_x, bar_y = 110, y
        bar_max = HUD_WIDTH - 120
        bar_fill = int(bar_max * min(ratio, 1.0))
        pygame.draw.rect(panel, (50, 50, 70), (bar_x, bar_y + 2, bar_max, 9), border_radius=4)
        if bar_fill > 0:
            pygame.draw.rect(panel, bar_color, (bar_x, bar_y + 2, bar_fill, 9), border_radius=4)
        y += font_small.get_height() + 3

        # Artista a tocar
        active = get_active_show(name, sim_time)
        if active:
            write(f"  ♪ {active['artist'][:20]}", font_small, (255, 215, 0), indent=12)

        # Fila
        write(f"  fila:{stage.queue_length}  ocp:{stage.occupancy}/{stage.capacity}",
              font_small, MENU_SUBTEXT, indent=12)

    separator()

    # ── Perfis ───────────────────────────────────────────────────────
    write("PERFIS", font_title, MENU_ACCENT)
    y += 4
    profile_colors = {
        "general": COLORS["agent_general"],
        "fan":     COLORS["agent_fan"],
        "vip":     COLORS["agent_vip"],
    }
    for profile_name, data in festival.profile_summary().items():
        col = profile_colors.get(profile_name, COLORS["text"])
        write(f"{profile_name:8s}  ✓{data['served']:4d}  ✗{data['reneged']:3d}",
              font_small, col, indent=10)

    separator()

    # ── Global ───────────────────────────────────────────────────────
    total_served  = sum(s.total_served  for s in festival.stages.values())
    total_reneged = sum(s.total_reneged for s in festival.stages.values())
    write("GLOBAL", font_title, MENU_ACCENT)
    write(f"Servidos:    {total_served}")
    write(f"Desistiram:  {total_reneged}")

    if done:
        separator()
        write("✓ Simulação terminada!", font_title, (100, 255, 100))
        write("Prima Q para sair.", color=MENU_SUBTEXT)

    surface.blit(panel, (hx, 0))


# ─────────────────────────────────────────────
# LOOP PRINCIPAL PYGAME
# ─────────────────────────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Coachella Crowd Simulation")
    clock = pygame.time.Clock()

    # ── FASE 1: Menu de seleção de política ──────────────────────────
    selected = 0
    hover    = 0
    in_menu  = True

    while in_menu:
        mx, my = pygame.mouse.get_pos()

        # Detectar hover nos cards
        card_w, card_h = 360, 90
        start_y = 130
        gap = 16
        hover = -1
        for i in range(len(ALL_POLICIES)):
            cx = WINDOW_WIDTH // 2 - card_w // 2
            cy = start_y + i * (card_h + gap)
            if cx <= mx <= cx + card_w and cy <= my <= cy + card_h:
                hover = i

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit(0)
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(ALL_POLICIES)
                    hover = selected
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(ALL_POLICIES)
                    hover = selected
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    selected = 0
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    selected = 1
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    selected = 2
                elif event.key in (pygame.K_4, pygame.K_KP4):
                    selected = 3
                elif event.key == pygame.K_RETURN:
                    in_menu = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hover >= 0:
                    selected = hover
                    in_menu = False

        draw_menu(screen, selected, hover)
        pygame.display.flip()
        clock.tick(FPS)

    chosen_policy = ALL_POLICIES[selected]
    logger.info("Política selecionada: %s", chosen_policy.name)

    # ── FASE 2: Simulação ────────────────────────────────────────────
    festival     = FestivalEnvironment(seed=RANDOM_SEED, policy=chosen_policy)
    festival_map = FestivalMap()

    done_flag  = threading.Event()
    sim_thread = threading.Thread(
        target=run_simulation,
        args=(festival, done_flag),
        daemon=True,
    )
    sim_thread.start()
    logger.info("Pygame inicializado. A correr visualização...")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False

        # Área do mapa (esquerda)
        map_surface = screen.subsurface(pygame.Rect(0, 0, MAP_WIDTH, MAP_HEIGHT))
        map_surface.fill(COLORS["background"])
        festival_map.draw(map_surface, festival=festival)

        # HUD lateral (direita)
        sim_time = festival.env.now
        draw_hud(screen, festival, sim_time,
                 done=done_flag.is_set(),
                 policy_name=chosen_policy.name)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    logger.info("Visualização encerrada.")
    sys.exit(0)


if __name__ == "__main__":
    main()