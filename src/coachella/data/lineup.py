"""
data/lineup.py - Lineup real do Coachella 2023
Artistas, palcos e horários expressos em minutos desde o início da simulação.
Minuto 0 = 12:00 (meio-dia). Minuto 480 = 20:00.

Horários simplificados para caberem na janela de simulação de 8h.
"""

# ─────────────────────────────────────────────
# LINEUP
# Estrutura: lista de dicts com:
#   - artist:   nome do artista
#   - stage:    nome do palco (tem de corresponder às keys de STAGES no config.py)
#   - start:    minuto de início (relativo ao início da simulação)
#   - duration: duração em minutos
# ─────────────────────────────────────────────

LINEUP: list[dict] = [
    # ── Main Stage ────────────────────────────────────────────────────
    {"artist": "Bad Bunny",       "stage": "Main Stage", "start": 420, "duration": 60},  # headliner
    {"artist": "Rosalía",         "stage": "Main Stage", "start": 300, "duration": 60},
    {"artist": "Burna Boy",       "stage": "Main Stage", "start": 180, "duration": 60},
    {"artist": "Becky G",         "stage": "Main Stage", "start": 60,  "duration": 60},

    # ── Sahara Stage ──────────────────────────────────────────────────
    {"artist": "Kaytranada",      "stage": "Sahara Stage", "start": 360, "duration": 45},
    {"artist": "Anitta",          "stage": "Sahara Stage", "start": 240, "duration": 45},
    {"artist": "Diplo",           "stage": "Sahara Stage", "start": 120, "duration": 45},
    {"artist": "Fisher",          "stage": "Sahara Stage", "start": 30,  "duration": 45},

    # ── Outdoor Stage ─────────────────────────────────────────────────
    {"artist": "Gorillaz",        "stage": "Outdoor Stage", "start": 330, "duration": 40},
    {"artist": "Blur",            "stage": "Outdoor Stage", "start": 210, "duration": 40},
    {"artist": "Labrinth",        "stage": "Outdoor Stage", "start": 90,  "duration": 40},
    {"artist": "Sza",             "stage": "Outdoor Stage", "start": 0,   "duration": 40},
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_artist_names() -> list[str]:
    """Retorna lista de todos os nomes de artistas."""
    return [entry["artist"] for entry in LINEUP]


def get_show(artist: str) -> dict | None:
    """Retorna o dict do show de um artista, ou None se não existir."""
    for entry in LINEUP:
        if entry["artist"] == artist:
            return entry
    return None


def get_shows_at_stage(stage_name: str) -> list[dict]:
    """Retorna todos os shows de um palco específico, ordenados por hora."""
    return sorted(
        [entry for entry in LINEUP if entry["stage"] == stage_name],
        key=lambda e: e["start"]
    )


def get_active_show(stage_name: str, current_time: float) -> dict | None:
    """Retorna o show ativo num palco no tempo atual, ou None."""
    for entry in LINEUP:
        if entry["stage"] == stage_name:
            if entry["start"] <= current_time < entry["start"] + entry["duration"]:
                return entry
    return None


def get_next_show(stage_name: str, current_time: float) -> dict | None:
    """Retorna o próximo show num palco após o tempo atual, ou None."""
    upcoming = [
        e for e in LINEUP
        if e["stage"] == stage_name and e["start"] > current_time
    ]
    return min(upcoming, key=lambda e: e["start"]) if upcoming else None