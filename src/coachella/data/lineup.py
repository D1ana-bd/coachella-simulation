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
    # ── Coachella Stage ───────────────────────────────────────────────
    {"artist": "Bad Bunny",       "stage": "Coachella Stage", "start": 420, "duration": 60},
    {"artist": "Rosalía",         "stage": "Coachella Stage", "start": 300, "duration": 60},
    {"artist": "Burna Boy",       "stage": "Coachella Stage", "start": 180, "duration": 60},
    {"artist": "Becky G",         "stage": "Coachella Stage", "start": 60,  "duration": 60},

    # ── Sahara ────────────────────────────────────────────────────────
    {"artist": "Kaytranada",      "stage": "Sahara", "start": 360, "duration": 45},
    {"artist": "Anitta",          "stage": "Sahara", "start": 240, "duration": 45},
    {"artist": "Diplo",           "stage": "Sahara", "start": 120, "duration": 45},
    {"artist": "Fisher",          "stage": "Sahara", "start": 30,  "duration": 45},

    # ── Outdoor Theatre ───────────────────────────────────────────────
    {"artist": "Gorillaz",        "stage": "Outdoor Theatre", "start": 330, "duration": 40},
    {"artist": "Blur",            "stage": "Outdoor Theatre", "start": 210, "duration": 40},
    {"artist": "Labrinth",        "stage": "Outdoor Theatre", "start": 90,  "duration": 40},
    {"artist": "SZA",             "stage": "Outdoor Theatre", "start": 0,   "duration": 40},

    # ── Mojave ────────────────────────────────────────────────────────
    {"artist": "Lil Uzi Vert",    "stage": "Mojave", "start": 390, "duration": 45},
    {"artist": "Doechii",         "stage": "Mojave", "start": 270, "duration": 40},
    {"artist": "Sudan Archives",  "stage": "Mojave", "start": 150, "duration": 35},
    {"artist": "Sample Minds",    "stage": "Mojave", "start": 30,  "duration": 35},

    # ── Gobi ──────────────────────────────────────────────────────────
    {"artist": "Charli XCX",      "stage": "Gobi", "start": 360, "duration": 40},
    {"artist": "Caroline Polachek","stage": "Gobi", "start": 240, "duration": 35},
    {"artist": "Wet Leg",         "stage": "Gobi", "start": 120, "duration": 35},
    {"artist": "Soft Play",       "stage": "Gobi", "start": 20,  "duration": 30},

    # ── Sonora ────────────────────────────────────────────────────────
    {"artist": "Four Tet",        "stage": "Sonora", "start": 400, "duration": 40},
    {"artist": "Mall Grab",       "stage": "Sonora", "start": 280, "duration": 35},
    {"artist": "Peggy Gou",       "stage": "Sonora", "start": 160, "duration": 35},
    {"artist": "DJ Stingray",     "stage": "Sonora", "start": 40,  "duration": 30},

    # ── Do Lab ────────────────────────────────────────────────────────
    {"artist": "Disclosure",      "stage": "Do Lab", "start": 380, "duration": 45},
    {"artist": "Jamie xx",        "stage": "Do Lab", "start": 260, "duration": 40},
    {"artist": "Caribou",         "stage": "Do Lab", "start": 140, "duration": 35},
    {"artist": "Floating Points", "stage": "Do Lab", "start": 20,  "duration": 35},

    # ── Yuma (VIP) ────────────────────────────────────────────────────
    {"artist": "Solomun",         "stage": "Yuma", "start": 360, "duration": 60},
    {"artist": "Richie Hawtin",   "stage": "Yuma", "start": 240, "duration": 50},
    {"artist": "Nina Kraviz",     "stage": "Yuma", "start": 120, "duration": 50},
    {"artist": "Ricardo Villalobos", "stage": "Yuma", "start": 0, "duration": 45},
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