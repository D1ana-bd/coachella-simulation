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
# ASSETS DO MENU
# ─────────────────────────────────────────────

import os
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "src", "coachella", "assets")

_menu_bg   = None
_sprites   = {}

def _load_menu_assets():
    global _menu_bg, _sprites
    if _menu_bg is not None:
        return

    # Fundo
    try:
        img = pygame.image.load(os.path.join(ASSETS_DIR, "fundo_menu.png")).convert()
        _menu_bg = pygame.transform.scale(img, (WINDOW_WIDTH, WINDOW_HEIGHT))
    except Exception as e:
        logger.warning("fundo_menu.png não carregado: %s", e)
        _menu_bg = None

    # Sprites (pequenos, para os cards)
    for key, fname in [("general","stripe_geral.png"),("fan","stripe_FAN.png"),("vip","stripe_VIP.png")]:
        try:
            img = pygame.image.load(os.path.join(ASSETS_DIR, fname)).convert_alpha()
            img.set_colorkey((0, 0, 0))
            _sprites[key] = pygame.transform.scale(img, (38, 38))
        except:
            _sprites[key] = None


# ─────────────────────────────────────────────
# ASSETS DO MENU
# ─────────────────────────────────────────────

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "coachella", "assets")

_menu_bg    = None
_sprites    = {}
_fonts      = {}

def _load_menu_assets():
    global _menu_bg, _sprites, _fonts

    if _fonts:
        return  # já carregado

    font_path = os.path.join(ASSETS_DIR, "PressStart2P-Regular.ttf")

    def pf(size):
        try:
            return pygame.font.Font(font_path, size)
        except:
            return pygame.font.SysFont("monospace", size, bold=True)

    _fonts = {
        "title":  pf(18),
        "sub":    pf(7),
        "card":   pf(10),
        "desc":   pf(7),
        "hint":   pf(6),
        "badge":  pf(11),
    }

    # Fundo
    try:
        img = pygame.image.load(os.path.join(ASSETS_DIR, "fundo_menu.png")).convert()
        _menu_bg = pygame.transform.scale(img, (WINDOW_WIDTH, WINDOW_HEIGHT))
    except Exception as e:
        logger.warning("fundo_menu.png não carregado: %s", e)
        _menu_bg = None

    # Sprites
    for key, fname in [("general","stripe_geral.png"), ("fan","stripe_FAN.png"), ("vip","stripe_VIP.png")]:
        try:
            img = pygame.image.load(os.path.join(ASSETS_DIR, fname)).convert_alpha()
            img.set_colorkey((0, 0, 0))
            _sprites[key] = pygame.transform.scale(img, (48, 48))
        except:
            _sprites[key] = None


# ─────────────────────────────────────────────
# MENU
# ─────────────────────────────────────────────

POLICY_COLORS = [
    (100, 180, 255),   # Baseline     — azul
    (100, 220, 150),   # Informative  — verde
    (255, 160,  80),   # Active Mgmt  — laranja
    (255, 200,  50),   # VIP Priority — dourado
]

POLICY_SPRITE_KEYS = ["general", "fan", "general", "vip"]

POLICY_DESCRIPTIONS = [
    "Sem app. Agentes livres.",
    "App com filas em tempo real.",
    "Recomendacoes dinamicas.",
    "Fila VIP + Yuma exclusivo.",
]

def _draw_pixel_border(surface, rect, color, thickness=3):
    """Borda estilo pixel art — cantos quadrados, linha dupla."""
    x, y, w, h = rect
    # Linha exterior
    pygame.draw.rect(surface, color, (x, y, w, h), thickness)
    # Linha interior mais escura
    dark = tuple(max(0, c - 60) for c in color)
    pygame.draw.rect(surface, dark, (x + thickness + 1, y + thickness + 1,
                                      w - (thickness + 1) * 2,
                                      h - (thickness + 1) * 2), 1)

def _draw_banner(surface, x, y, number, color, font):
    """Banner vertical com número — estilo Stardew Valley."""
    bw, bh = 30, 44
    # Corpo do banner
    pygame.draw.rect(surface, color, (x, y, bw, bh))
    # Triângulo na base (ponta do banner)
    pts = [(x, y + bh), (x + bw // 2, y + bh + 10), (x + bw, y + bh)]
    pygame.draw.polygon(surface, color, pts)
    # Borda
    pygame.draw.rect(surface, (0, 0, 0), (x, y, bw, bh), 2)
    pygame.draw.polygon(surface, (0, 0, 0), pts, 2)
    # Número
    num_surf = font.render(str(number), True, (20, 15, 5))
    surface.blit(num_surf, (x + bw // 2 - num_surf.get_width() // 2,
                             y + bh // 2 - num_surf.get_height() // 2))


def draw_menu(surface: pygame.Surface, selected: int, hover: int):
    _load_menu_assets()

    # ── Fundo ─────────────────────────────────────────────────────────
    if _menu_bg:
        surface.blit(_menu_bg, (0, 0))
    else:
        surface.fill((20, 15, 10))

    # Overlay leve para legibilidade
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 60))
    surface.blit(overlay, (0, 0))

    f = _fonts

    # ── Painel central ────────────────────────────────────────────────
    panel_w, panel_h = 560, 490
    panel_x = WINDOW_WIDTH // 2 - panel_w // 2
    panel_y = 45

    # Fundo pergaminho
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((210, 175, 100, 225))
    surface.blit(panel, (panel_x, panel_y))

    # Borda pixel art dupla — castanho escuro
    _draw_pixel_border(surface, (panel_x, panel_y, panel_w, panel_h), (120, 80, 30), 4)

    # Cantos decorativos (quadradinhos pixel art)
    corner_col = (160, 110, 40)
    for cx, cy in [(panel_x, panel_y), (panel_x + panel_w - 12, panel_y),
                   (panel_x, panel_y + panel_h - 12), (panel_x + panel_w - 12, panel_y + panel_h - 12)]:
        pygame.draw.rect(surface, corner_col, (cx, cy, 12, 12))
        pygame.draw.rect(surface, (80, 50, 15), (cx, cy, 12, 12), 2)

    # ── Título ────────────────────────────────────────────────────────
    title = f["title"].render("COACHELLA SIMULATION", True, (80, 40, 10))
    # Sombra
    title_sh = f["title"].render("COACHELLA SIMULATION", True, (160, 110, 40))
    tx = WINDOW_WIDTH // 2 - title.get_width() // 2
    surface.blit(title_sh, (tx + 2, panel_y + 18))
    surface.blit(title, (tx, panel_y + 16))

    # Linha decorativa sob título
    pygame.draw.line(surface, (120, 80, 30),
                     (panel_x + 30, panel_y + 44),
                     (panel_x + panel_w - 30, panel_y + 44), 2)
    pygame.draw.line(surface, (160, 120, 60),
                     (panel_x + 30, panel_y + 47),
                     (panel_x + panel_w - 30, panel_y + 47), 1)

    sub = f["sub"].render("SELECIONA UMA POLITICA DE GESTAO DE MULTIDOES", True, (100, 60, 20))
    surface.blit(sub, (WINDOW_WIDTH // 2 - sub.get_width() // 2, panel_y + 52))

    # ── Cards ─────────────────────────────────────────────────────────
    card_w  = panel_w - 50
    card_h  = 76
    card_x  = panel_x + 25
    start_y = panel_y + 72
    gap     = 8

    for i, policy in enumerate(ALL_POLICIES):
        cy       = start_y + i * (card_h + gap)
        is_hover = (i == hover)
        is_sel   = (i == selected)
        col      = POLICY_COLORS[i]

        # Fundo do card — mais claro se hover
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        if is_hover:
            card_surf.fill((255, 235, 170, 230))
        elif is_sel:
            card_surf.fill((245, 220, 140, 220))
        else:
            card_surf.fill((190, 155, 80, 200))
        surface.blit(card_surf, (card_x, cy))

        # Borda do card
        border_col = col if (is_hover or is_sel) else (120, 85, 35)
        border_w   = 3 if (is_hover or is_sel) else 2
        pygame.draw.rect(surface, border_col, (card_x, cy, card_w, card_h), border_w)

        # Banner com número
        _draw_banner(surface, card_x + 8, cy + 8, i + 1, col, f["badge"])

        # Sprite do agente
        sprite = _sprites.get(POLICY_SPRITE_KEYS[i])
        if sprite:
            surface.blit(sprite, (card_x + 48, cy + card_h // 2 - 24))

        # Nome da política
        name_surf = f["card"].render(policy.name.upper(), True, col)
        # Sombra do nome
        name_sh   = f["card"].render(policy.name.upper(), True, (50, 30, 5))
        nx = card_x + 108
        surface.blit(name_sh, (nx + 1, cy + 13))
        surface.blit(name_surf, (nx, cy + 12))

        # Descrição
        desc_surf = f["desc"].render(POLICY_DESCRIPTIONS[i], True, (70, 45, 15))
        surface.blit(desc_surf, (nx, cy + 34))

        # Seta animada se hover
        if is_hover:
            arrow = f["card"].render(">", True, col)
            surface.blit(arrow, (card_x + card_w - arrow.get_width() - 14,
                                  cy + card_h // 2 - arrow.get_height() // 2))

    # ── Hint ──────────────────────────────────────────────────────────
    hint_y = panel_y + panel_h - 22
    hint = f["hint"].render(
        "< >  ou  1 2 3 4  para navegar   |   ENTER iniciar   |   Q sair",
        True, (80, 50, 15)
    )
    surface.blit(hint, (WINDOW_WIDTH // 2 - hint.get_width() // 2, hint_y))


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