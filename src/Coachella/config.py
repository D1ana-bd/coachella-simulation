"""
config.py - Configurações centrais da simulação Coachella
Todos os parâmetros do festival, agentes e visualização ficam aqui.
"""

# ─────────────────────────────────────────────
# SIMULAÇÃO GERAL
# ─────────────────────────────────────────────
RANDOM_SEED = 42
SIM_DURATION = 480          # minutos (ex: 8h de festival, 12:00 → 20:00)
NUM_AGENTS = 200            # agentes na fase 1 (escalar depois)
AGENT_SPAWN_RATE = 2.0      # média de chegadas por minuto (distribuição Poisson)

# ─────────────────────────────────────────────
# PALCOS (stages)
# ─────────────────────────────────────────────
STAGES = {
    "Main Stage": {
        "capacity": 80,
        "x": 400,
        "y": 150,
        "show_duration": 60,        # minutos por concerto
        "shows_start": [60, 180, 300, 420],  # minutos desde início da sim
        "popularity": 0.5,          # peso na escolha do palco
    },
    "Sahara Stage": {
        "capacity": 50,
        "x": 150,
        "y": 300,
        "show_duration": 45,
        "shows_start": [30, 120, 240, 360],
        "popularity": 0.3,
    },
    "Outdoor Stage": {
        "capacity": 30,
        "x": 650,
        "y": 350,
        "show_duration": 40,
        "shows_start": [0, 90, 210, 330, 450],
        "popularity": 0.2,
    },
}

# ─────────────────────────────────────────────
# FILAS DE ESPERA
# ─────────────────────────────────────────────
MAX_QUEUE_LENGTH = 50           # tamanho máximo da fila por palco
SERVICE_TIME_MEAN = 0.5         # minutos para processar 1 agente na entrada
SERVICE_TIME_STD = 0.1

# ─────────────────────────────────────────────
# AGENTES
# ─────────────────────────────────────────────
PATIENCE_MIN = 10               # minutos mínimos que um agente espera na fila
PATIENCE_MAX = 40               # minutos máximos
WATCH_DURATION_MIN = 20         # tempo mínimo que fica a ver o concerto
WATCH_DURATION_MAX = 60         # tempo máximo

# ─────────────────────────────────────────────
# MÉTRICAS & OUTPUT
# ─────────────────────────────────────────────
METRICS_INTERVAL = 10           # recolher métricas a cada X minutos de sim
OUTPUT_DIR = "outputs/"
METRICS_FILE = OUTPUT_DIR + "metrics.csv"
LOG_FILE = OUTPUT_DIR + "simulation.log"

# ─────────────────────────────────────────────
# VISUALIZAÇÃO (Pygame)
# ─────────────────────────────────────────────
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 600
FPS = 30
SIM_SPEED = 1.0                 # multiplicador de velocidade da simulação

# Cores (RGB)
COLORS = {
    "background": (30, 30, 30),
    "stage": (70, 130, 180),
    "stage_full": (220, 50, 50),
    "agent": (100, 220, 100),
    "queue": (255, 200, 50),
    "text": (240, 240, 240),
    "grid": (50, 50, 50),
}

STAGE_RADIUS = 40               # raio visual do palco em px
AGENT_RADIUS = 4                # raio visual do agente em px