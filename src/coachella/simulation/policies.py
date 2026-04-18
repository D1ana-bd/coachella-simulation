"""
simulation/policies.py - Definição das 4 políticas de gestão do festival.

Cada política é uma instância de PolicyConfig — um dataclass com parâmetros
que controlam o comportamento dos agentes e do ambiente.
O motor de simulação (environment.py, events.py) lê estes parâmetros em runtime.

Políticas:
    BASELINE          — sem app, comportamento original da Fase 2
    INFORMATIVE_APP   — agentes consultam lotação/espera antes de escolher palco
    ACTIVE_MANAGEMENT — sistema deteta congestionamento e emite recomendações
    VIP_PRIORITY      — filas com prioridade diferenciada + análise de equidade
"""

from dataclasses import dataclass, field


# ─────────────────────────────────────────────
# PRIORIDADES VIP (SimPy PriorityResource)
# Menor número = maior prioridade
# ─────────────────────────────────────────────

PRIORITY_VIP     = 0   # VIP lane — acesso imediato
PRIORITY_FAN     = 1   # Fãs — chegam cedo, posicionam-se melhor
PRIORITY_GENERAL = 2   # Público geral — sem vantagem


# ─────────────────────────────────────────────
# POLICY CONFIG
# ─────────────────────────────────────────────

@dataclass
class PolicyConfig:
    """
    Configuração de uma política de gestão do festival.

    Todos os parâmetros têm defaults que correspondem ao Baseline —
    cada política ativa apenas o que precisa, mantendo o resto igual.

    Parâmetros:
        name: str
            Nome da política (usado em logs, gráficos e tabelas).

        # ── Política 2: App Informativa ───────────────────────────────
        app_enabled: bool
            Se True, agentes com app consultam lotação e fila antes de escolher palco.

        app_adoption_rate: dict[str, float]
            Proporção de agentes de cada perfil que usa a app.
            Ex: {"general": 0.65, "fan": 0.90, "vip": 0.80}

        info_delay: float
            Lag da informação em minutos — simula que a app não é instantânea.
            A lotação que o agente vê tem X minutos de atraso.

        # ── Política 3: Gestão Ativa ──────────────────────────────────
        active_management: bool
            Se True, o sistema monitoriza congestionamento e emite recomendações.

        congestion_threshold: float
            Percentagem de ocupação (0.0–1.0) acima da qual um palco é considerado
            congestionado e o sistema emite recomendação de alternativa.

        compliance_rate: dict[str, float]
            Probabilidade de um agente de cada perfil seguir a recomendação.
            VIPs tendem a ignorar; Fãs tendem a seguir se não for o seu favorito.

        # ── Política 4: VIP Prioritário ───────────────────────────────
        vip_priority: bool
            Se True, usa simpy.PriorityResource em vez de simpy.Resource.
            Agentes têm prioridade diferenciada: VIP=0, Fan=1, General=2.
    """

    name: str

    # App informativa
    app_enabled: bool = False
    app_adoption_rate: dict = field(default_factory=lambda: {
        "general": 0.0,
        "fan":     0.0,
        "vip":     0.0,
    })
    info_delay: float = 0.0         # minutos de lag na informação

    # Gestão ativa
    active_management: bool = False
    congestion_threshold: float = 0.85     # 85% de ocupação → congestionado
    compliance_rate: dict = field(default_factory=lambda: {
        "general": 0.0,
        "fan":     0.0,
        "vip":     0.0,
    })

    # VIP prioritário
    vip_priority: bool = False

    def is_congested(self, occupancy: int, capacity: int) -> bool:
        """Retorna True se o palco estiver acima do threshold de congestionamento."""
        if capacity == 0:
            return False
        return (occupancy / capacity) >= self.congestion_threshold

    def agent_uses_app(self, agent_type_value: str, rng) -> bool:
        """Retorna True se este agente usa a app (sorteio por taxa de adoção)."""
        rate = self.app_adoption_rate.get(agent_type_value, 0.0)
        return rng.random() < rate

    def agent_follows_recommendation(self, agent_type_value: str, rng) -> bool:
        """Retorna True se o agente segue a recomendação do sistema de gestão ativa."""
        rate = self.compliance_rate.get(agent_type_value, 0.0)
        return rng.random() < rate


# ─────────────────────────────────────────────
# AS 4 POLÍTICAS
# ─────────────────────────────────────────────

BASELINE = PolicyConfig(
    name="Baseline",
    # tudo nos defaults — sem app, sem gestão ativa, sem prioridade
)

INFORMATIVE_APP = PolicyConfig(
    name="Informative App",
    app_enabled=True,
    app_adoption_rate={
        "general": 0.65,    # 65% do público geral usa a app
        "fan":     0.90,    # fãs são os mais atentos ao lineup e à lotação
        "vip":     0.80,    # VIPs usam muito mas têm acesso privilegiado de qualquer forma
    },
    info_delay=2.0,         # informação com 2 min de lag — realista para uma app
)

ACTIVE_MANAGEMENT = PolicyConfig(
    name="Active Management",
    app_enabled=True,       # gestão ativa pressupõe que a app existe
    app_adoption_rate={
        "general": 0.65,
        "fan":     0.90,
        "vip":     0.80,
    },
    info_delay=2.0,
    active_management=True,
    congestion_threshold=0.85,
    compliance_rate={
        "general": 0.70,    # público geral segue a maioria das recomendações
        "fan":     0.50,    # fãs resistem mais — se o favorito está a tocar, não saem
        "vip":     0.30,    # VIPs tendem a ignorar recomendações (confiança no acesso)
    },
)

VIP_PRIORITY = PolicyConfig(
    name="VIP Priority",
    app_enabled=True,
    app_adoption_rate={
        "general": 0.65,
        "fan":     0.90,
        "vip":     0.80,
    },
    info_delay=2.0,
    active_management=True,
    congestion_threshold=0.85,
    compliance_rate={
        "general": 0.70,
        "fan":     0.50,
        "vip":     0.30,
    },
    vip_priority=True,      # activa simpy.PriorityResource + prioridades diferenciadas
)

# Lista ordenada para iterar nas análises comparativas
ALL_POLICIES = [BASELINE, INFORMATIVE_APP, ACTIVE_MANAGEMENT, VIP_PRIORITY]