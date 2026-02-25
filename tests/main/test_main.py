"""
tests/test_main.py - Testes unitários para main.py
Testa a inicialização, a thread de simulação, o HUD e o loop principal.
"""

import pytest
import threading
import pygame
from unittest.mock import patch, MagicMock, call
from src.coachella.simulation import FestivalEnvironment, agent_arrivals
from src.coachella.visualization import FestivalMap
from main import run_simulation, draw_hud


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def festival():
    return FestivalEnvironment(seed=42)


@pytest.fixture
def done_flag():
    return threading.Event()


@pytest.fixture
def surface():
    pygame.init()
    s = pygame.Surface((900, 600))
    yield s
    pygame.quit()


# ─────────────────────────────────────────────
# TESTES: run_simulation
# ─────────────────────────────────────────────

def test_run_simulation_sets_done_flag(festival, done_flag):
    """Após correr, done_flag deve estar set."""
    with patch("main.NUM_AGENTS", 5):
        with patch("main.SIM_DURATION", 60):
            run_simulation(festival, done_flag)
    assert done_flag.is_set()


def test_run_simulation_produces_metrics(festival, done_flag):
    """Após a simulação, deve haver métricas recolhidas."""
    with patch("main.NUM_AGENTS", 5):
        with patch("main.SIM_DURATION", 60):
            run_simulation(festival, done_flag)
    assert len(festival.metrics_log) > 0


def test_run_simulation_serves_agents(festival, done_flag):
    """Pelo menos alguns agentes devem ser servidos."""
    with patch("main.NUM_AGENTS", 10):
        with patch("main.SIM_DURATION", 300):
            run_simulation(festival, done_flag)
    total_served = sum(s.total_served for s in festival.stages.values())
    assert total_served > 0


def test_run_simulation_in_thread(festival, done_flag):
    """run_simulation deve funcionar corretamente numa thread separada."""
    with patch("main.NUM_AGENTS", 5):
        with patch("main.SIM_DURATION", 60):
            thread = threading.Thread(
                target=run_simulation,
                args=(festival, done_flag),
                daemon=True,
            )
            thread.start()
            thread.join(timeout=10)

    assert done_flag.is_set()
    assert not thread.is_alive()


def test_run_simulation_creates_csv(festival, done_flag, tmp_path):
    """Após a simulação, o ficheiro de métricas deve ser criado."""
    fake_file = str(tmp_path / "metrics.csv")
    with patch("main.NUM_AGENTS", 5):
        with patch("main.SIM_DURATION", 60):
            with patch("src.coachella.simulation.environment.METRICS_FILE", fake_file):
                run_simulation(festival, done_flag)
    import os
    assert os.path.exists(fake_file)


# ─────────────────────────────────────────────
# TESTES: draw_hud
# ─────────────────────────────────────────────

def test_draw_hud_does_not_raise(festival, surface):
    """draw_hud() não deve lançar exceções."""
    try:
        draw_hud(surface, festival, sim_time=0.0, done=False)
    except Exception as e:
        pytest.fail(f"draw_hud() lançou exceção inesperada: {e}")


def test_draw_hud_done_does_not_raise(festival, surface):
    """draw_hud() com done=True não deve lançar exceções."""
    try:
        draw_hud(surface, festival, sim_time=120.0, done=True)
    except Exception as e:
        pytest.fail(f"draw_hud() com done=True lançou exceção: {e}")


def test_draw_hud_modifies_surface(festival, surface):
    """draw_hud() deve modificar a surface."""
    surface.fill((0, 0, 0))
    draw_hud(surface, festival, sim_time=10.0, done=False)
    pixels = pygame.surfarray.array3d(surface)
    assert pixels.max() > 0


def test_draw_hud_shows_all_stages(festival, surface):
    """HUD deve referenciar todos os palcos (verificado indiretamente via rendering)."""
    # Não rebenta mesmo com todos os palcos com agentes
    for stage in festival.stages.values():
        stage.total_served = 5
    try:
        draw_hud(surface, festival, sim_time=50.0, done=False)
    except Exception as e:
        pytest.fail(f"draw_hud() com stages preenchidos lançou exceção: {e}")


# ─────────────────────────────────────────────
# TESTES: main() — loop Pygame mockado
# ─────────────────────────────────────────────

def test_main_exits_on_quit_event():
    """main() deve terminar quando recebe evento QUIT."""
    quit_event = MagicMock()
    quit_event.type = pygame.QUIT

    with patch("main.pygame.init"), \
         patch("main.pygame.display.set_mode", return_value=MagicMock()), \
         patch("main.pygame.display.set_caption"), \
         patch("main.pygame.display.flip"), \
         patch("main.pygame.quit"), \
         patch("main.pygame.time.Clock", return_value=MagicMock()), \
         patch("main.pygame.event.get", side_effect=[[quit_event]]), \
         patch("main.draw_hud"), \
         patch("main.threading.Thread") as mock_thread, \
         patch("main.sys.exit") as mock_exit, \
         patch("main.FestivalEnvironment"), \
         patch("main.FestivalMap"):

        mock_thread.return_value.start = MagicMock()

        from main import main
        main()

    mock_exit.assert_called_once_with(0)


def test_main_exits_on_q_keydown():
    """main() deve terminar quando o utilizador prime Q."""
    q_event = MagicMock()
    q_event.type = pygame.KEYDOWN
    q_event.key = pygame.K_q

    with patch("main.pygame.init"), \
         patch("main.pygame.display.set_mode", return_value=MagicMock()), \
         patch("main.pygame.display.set_caption"), \
         patch("main.pygame.display.flip"), \
         patch("main.pygame.quit"), \
         patch("main.pygame.time.Clock", return_value=MagicMock()), \
         patch("main.pygame.event.get", side_effect=[[q_event]]), \
         patch("main.draw_hud"), \
         patch("main.threading.Thread") as mock_thread, \
         patch("main.sys.exit") as mock_exit, \
         patch("main.FestivalEnvironment"), \
         patch("main.FestivalMap"):

        mock_thread.return_value.start = MagicMock()

        from main import main
        main()

    mock_exit.assert_called_once_with(0)


def test_main_starts_simulation_thread():
    """main() deve lançar a thread de simulação."""
    quit_event = MagicMock()
    quit_event.type = pygame.QUIT

    with patch("main.pygame.init"), \
         patch("main.pygame.display.set_mode", return_value=MagicMock()), \
         patch("main.pygame.display.set_caption"), \
         patch("main.pygame.display.flip"), \
         patch("main.pygame.quit"), \
         patch("main.pygame.time.Clock", return_value=MagicMock()), \
         patch("main.pygame.event.get", side_effect=[[quit_event]]), \
         patch("main.draw_hud"), \
         patch("main.threading.Thread") as mock_thread, \
         patch("main.sys.exit"), \
         patch("main.FestivalEnvironment"), \
         patch("main.FestivalMap"):

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        from main import main
        main()

    mock_thread_instance.start.assert_called_once()