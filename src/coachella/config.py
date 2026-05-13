"""
config.py - Configurações centrais da simulação coachella
Todos os parâmetros do festival, agentes e visualização ficam aqui.
"""

# ─────────────────────────────────────────────
# SIMULAÇÃO GERAL
# ─────────────────────────────────────────────
RANDOM_SEED = 42
SIM_DURATION = 480          # minutos (ex: 8h de festival, 12:00 → 20:00)
NUM_AGENTS = 10000            # agentes na fase 4
AGENT_SPAWN_RATE = 2.0      # média de chegadas por minuto (distribuição Poisson)
NUM_REPLICAS = 30       # réplicas por política (garante normalidade assintótica — TLC)

# ─────────────────────────────────────────────
# PALCOS (stages)
# ─────────────────────────────────────────────
STAGES = {
    "Coachella Stage": {
        "capacity": 500, "x": 500, "y": 95,
        "popularity": 0.35, "vip_only": False,
    },
    "Sahara": {
        "capacity": 400, "x": 229, "y": 629,
        "popularity": 0.25, "vip_only": False,
    },
    "Outdoor Theatre": {
        "capacity": 300, "x": 850, "y": 110,
        "popularity": 0.15, "vip_only": False,
    },
    "Mojave": {
        "capacity": 200, "x": 894, "y": 553,
        "popularity": 0.10, "vip_only": False,
    },
    "Gobi": {
        "capacity": 150, "x": 715, "y": 492,
        "popularity": 0.07, "vip_only": False,
    },
    "Sonora": {
        "capacity": 100, "x": 696, "y": 315,
        "popularity": 0.04, "vip_only": False,
    },
    "Do Lab": {
        "capacity": 100, "x": 593, "y": 687,
        "popularity": 0.04, "vip_only": False,
    },
    "Yuma": {
        "capacity": 80, "x": 105, "y": 390,
        "popularity": 0.10, "vip_only": True,
    },
}

FESTIVAL_ENTRANCE = {"x": 483, "y": 684}

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
MAX_WAIT_FOR_SHOW = 20  # minutos máximos que um agente espera pelo próximo show
# ENTRADA DO FESTIVAL
FESTIVAL_ENTRANCE = {"x": 450, "y": 500}   # ponto fixo de entrada
AGENT_MOVE_SPEED = 80                        # pixels por segundo simulado

# ─────────────────────────────────────────────
# MÉTRICAS & OUTPUT
# ─────────────────────────────────────────────
METRICS_INTERVAL = 10           # recolher métricas a cada X minutos de sim
OUTPUT_DIR = "src/coachella/data/"
METRICS_FILE = OUTPUT_DIR + "metrics.csv"
LOG_FILE = OUTPUT_DIR + "simulation.log"

# ─────────────────────────────────────────────
# VISUALIZAÇÃO (Pygame)
# ─────────────────────────────────────────────
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 800
FPS = 30
SIM_SPEED = 0.5                 # multiplicador de velocidade da simulação

# Cores (RGB)
COLORS = {
    "background": (30, 30, 30),
    "stage": (70, 130, 180),
    "stage_full": (220, 50, 50),
    "agent": (100, 220, 100),
    "queue": (255, 200, 50),
    "text": (240, 240, 240),
    "grid": (50, 50, 50),
    "agent_general": (100, 220, 100),   # verde — geral
    "agent_fan":     (255, 100, 180),   # rosa — fã
    "agent_vip":     (255, 215, 0),     # dourado — VIP
}

STAGE_RADIUS = 40               # raio visual do palco em px
AGENT_RADIUS = 4                # raio visual do agente em px

# ─────────────────────────────────────────────
# PERFIS DE AGENTES
# ─────────────────────────────────────────────
AGENT_PROFILES = {
    "general": {"proportion": 0.70},
    "fan":     {"proportion": 0.20},
    "vip":     {"proportion": 0.10},
}

# ─────────────────────────────────────────────
# CHEGADAS (ondas temporais)
# ─────────────────────────────────────────────
ARRIVAL_WAVES = [
    {"start": 0,   "end": 120, "rate": 8.0},   # abertura
    {"start": 120, "end": 240, "rate": 20.0},  # aquecimento
    {"start": 240, "end": 360, "rate": 32.0},  # pico pré-headliners
    {"start": 360, "end": 480, "rate": 16.0},  # headliners
]