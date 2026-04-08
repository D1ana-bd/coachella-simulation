"""
simulation/agents.py - Perfis de agentes e lógica de criação
Define os três tipos de festivaleiros com distribuições realistas de comportamento.
"""

import random
import numpy as np
from dataclasses import dataclass, field
from enum import Enum

from src.coachella.data.lineup import get_artist_names
from src.coachella.config import FESTIVAL_ENTRANCE


# ─────────────────────────────────────────────
# TIPO DE AGENTE
# ─────────────────────────────────────────────

class AgentType(Enum):
    GENERAL = "general"
    FAN     = "fan"
    VIP     = "vip"


# ─────────────────────────────────────────────
# PERFIL DE AGENTE
# ─────────────────────────────────────────────

@dataclass
class AgentProfile:
    """
    Parâmetros estatísticos que definem o comportamento de um tipo de agente.

    patience_mean / patience_std:
        Distribuição Normal da tolerância à espera em fila (minutos).
        Fãs têm paciência extra para os seus artistas favoritos.

    fan_patience_mean / fan_patience_std:
        Paciência especial do perfil Fã quando o artista favorito está a tocar.
        Ignorado para General e VIP.

    watch_duration_mean / watch_duration_std:
        Tempo que o agente passa a assistir ao concerto (minutos).

    num_favorites:
        Número de artistas favoritos que o agente tem.

    early_leave_prob:
        Probabilidade de o agente sair mais cedo do festival.

    proportion:
        Peso relativo na população (usado para escolher o perfil aleatoriamente).
    """
    name: str
    agent_type: AgentType

    patience_mean: float
    patience_std: float

    fan_patience_mean: float
    fan_patience_std: float

    watch_duration_mean: float
    watch_duration_std: float

    num_favorites: int
    early_leave_prob: float
    proportion: float


# ─────────────────────────────────────────────
# PERFIS DEFINIDOS
# ─────────────────────────────────────────────

PROFILES: dict[AgentType, AgentProfile] = {
    AgentType.GENERAL: AgentProfile(
        name="General",
        agent_type=AgentType.GENERAL,
        patience_mean=25.0,   # espera até ~25 min em fila
        patience_std=8.0,
        fan_patience_mean=25.0,  # não tem bónus — é igual
        fan_patience_std=8.0,
        watch_duration_mean=35.0,
        watch_duration_std=10.0,
        num_favorites=2,          # conhece alguns artistas mas não é fanático
        early_leave_prob=0.2,
        proportion=0.70,
    ),
    AgentType.FAN: AgentProfile(
        name="Fan",
        agent_type=AgentType.FAN,
        patience_mean=20.0,   # para artistas normais, paciência média-baixa
        patience_std=6.0,
        fan_patience_mean=50.0,  # para o artista favorito, espera MUITO
        fan_patience_std=10.0,
        watch_duration_mean=55.0,  # fica até ao fim
        watch_duration_std=5.0,
        num_favorites=2,           # tem 1-2 artistas que não perde
        early_leave_prob=0.05,     # raramente sai cedo
        proportion=0.20,
    ),
    AgentType.VIP: AgentProfile(
        name="VIP",
        agent_type=AgentType.VIP,
        patience_mean=10.0,   # pouca tolerância — está habituado a não esperar
        patience_std=3.0,
        fan_patience_mean=10.0,  # mesmo para favoritos, não espera muito
        fan_patience_std=3.0,
        watch_duration_mean=30.0,
        watch_duration_std=15.0,  # pode sair a meio se quiser
        num_favorites=1,
        early_leave_prob=0.35,    # sai mais cedo — tem outras coisas para fazer
        proportion=0.10,
    ),
}


# ─────────────────────────────────────────────
# AGENTE
# ─────────────────────────────────────────────

class Agent:
    """
    Representa um festivaleiro com personalidade e preferências.
    Substitui a classe Agent de events.py.
    """

    _id_counter = 0

    def __init__(self, rng: random.Random, np_rng: np.random.Generator):
        Agent._id_counter += 1
        self.id = Agent._id_counter

        # ── Escolher perfil aleatoriamente segundo proporções ─────────
        profile_list  = list(PROFILES.values())
        proportions   = [p.proportion for p in profile_list]
        self.profile  = rng.choices(profile_list, weights=proportions, k=1)[0]
        self.agent_type = self.profile.agent_type

        # ── Artistas favoritos (subconjunto aleatório do lineup) ──────
        all_artists = get_artist_names()
        num_favs = min(self.profile.num_favorites, len(all_artists))
        self.favorite_artists: list[str] = rng.sample(all_artists, k=num_favs)

        # ── Paciência base (distribuição Normal, mínimo 1 min) ────────
        raw_patience = np_rng.normal(
            self.profile.patience_mean,
            self.profile.patience_std,
        )
        self.patience: float = max(1.0, float(raw_patience))

        # ── Duração de visita ─────────────────────────────────────────
        raw_watch = np_rng.normal(
            self.profile.watch_duration_mean,
            self.profile.watch_duration_std,
        )
        self.watch_duration: float = max(5.0, float(raw_watch))

        # ── Saída antecipada ──────────────────────────────────────────
        self.leaves_early: bool = rng.random() < self.profile.early_leave_prob

        # ── Estado para visualização / métricas ──────────────────────
        self.current_stage: str | None = None
        self.status: str = "arriving"
        # arriving | moving | waiting_show | queuing | watching | leaving

        # ── Posição visual (começa na entrada do festival) ────────────
        self.x: float = float(FESTIVAL_ENTRANCE["x"])
        self.y: float = float(FESTIVAL_ENTRANCE["y"])

        # ── Métricas pessoais ─────────────────────────────────────────
        self.favorites_seen: list[str] = []   # artistas favoritos que conseguiu ver
        self.stages_visited: list[str] = []   # palcos que visitou
        self.total_wait_time: float = 0.0     # tempo total em fila
        self.reneged: bool = False  # desistiu pelo menos uma vez de uma fila

    def is_favorite(self, artist_name: str) -> bool:
        """Verifica se o artista é favorito deste agente."""
        return artist_name in self.favorite_artists

    def get_patience_for(self, artist_name: str | None, np_rng: np.random.Generator) -> float:
        """
        Retorna a paciência para um artista específico.
        Fãs têm paciência extra para os seus favoritos.
        """
        if self.agent_type == AgentType.FAN and artist_name and self.is_favorite(artist_name):
            raw = np_rng.normal(
                self.profile.fan_patience_mean,
                self.profile.fan_patience_std,
            )
        else:
            raw = np_rng.normal(
                self.profile.patience_mean,
                self.profile.patience_std,
            )
        return max(1.0, float(raw))

    def record_favorite_seen(self, artist_name: str):
        if artist_name in self.favorite_artists and artist_name not in self.favorites_seen:
            self.favorites_seen.append(artist_name)

    def __repr__(self):
        return f"Agent({self.id}, type={self.agent_type.value}, favs={self.favorite_artists})"

    @classmethod
    def reset_counter(cls):
        cls._id_counter = 0


# ─────────────────────────────────────────────
# FACTORY
# ─────────────────────────────────────────────

def create_agent(rng: random.Random, np_rng: np.random.Generator) -> Agent:
    """Cria um agente com perfil aleatório segundo as proporções definidas."""
    return Agent(rng, np_rng)