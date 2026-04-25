"""
config.py - Configurações centrais da simulação coachella
Todos os parâmetros do festival, agentes e visualização ficam aqui.
"""

# ─────────────────────────────────────────────
# SIMULAÇÃO GERAL
# ─────────────────────────────────────────────
RANDOM_SEED = 42
SIM_DURATION = 480          # minutos (ex: 8h de festival, 12:00 → 20:00)
NUM_AGENTS = 200            # agentes na fase 1 (escalar depois)
AGENT_SPAWN_RATE = 2.0      # média de chegadas por minuto (distribuição Poisson)
NUM_REPLICAS = 30       # réplicas por política (garante normalidade assintótica — TLC)

# ─────────────────────────────────────────────
# PALCOS (stages)
# ─────────────────────────────────────────────
STAGES = {
    "Coachella Stage": {
        "capacity": 3000, "x": 450, "y": 100,
        "popularity": 0.35, "vip_only": False,
    },
    "Sahara": {
        "capacity": 2500, "x": 180, "y": 420,
        "popularity": 0.25, "vip_only": False,
    },
    "Outdoor Theatre": {
        "capacity": 2000, "x": 720, "y": 120,
        "popularity": 0.15, "vip_only": False,
    },
    "Mojave": {
        "capacity": 1000, "x": 720, "y": 420,
        "popularity": 0.10, "vip_only": False,
    },
    "Gobi": {
        "capacity": 800, "x": 620, "y": 320,
        "popularity": 0.07, "vip_only": False,
    },
    "Sonora": {
        "capacity": 600, "x": 580, "y": 220,
        "popularity": 0.04, "vip_only": False,
    },
    "Do Lab": {
        "capacity": 500, "x": 450, "y": 470,
        "popularity": 0.04, "vip_only": False,
    },
    "Yuma": {
        "capacity": 400, "x": 120, "y": 310,
        "popularity": 0.10, "vip_only": True,
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
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 600
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
    {"start": 0,   "end": 120, "rate": 1.0},   # abertura — fluxo tranquilo
    {"start": 120, "end": 240, "rate": 2.5},   # aquecimento
    {"start": 240, "end": 360, "rate": 4.0},   # pré-headliners — pico
    {"start": 360, "end": 480, "rate": 2.0},   # headliners — já toda a gente chegou
]