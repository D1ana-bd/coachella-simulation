"""
tests/simulation_tests/test_policies.py - Testes para as 4 políticas de gestão.

Cobre:
- Estrutura e defaults do PolicyConfig (Baseline)
- Parâmetros específicos de cada política
- Helpers is_congested() e agent_uses_app() e agent_follows_recommendation()
- Lista ALL_POLICIES com as 4 políticas na ordem certa
"""

import pytest
from src.coachella.simulation.policies import (
    PolicyConfig,
    BASELINE,
    INFORMATIVE_APP,
    ACTIVE_MANAGEMENT,
    VIP_PRIORITY,
    ALL_POLICIES,
    PRIORITY_VIP,
    PRIORITY_FAN,
    PRIORITY_GENERAL,
)


# ─────────────────────────────────────────────
# PRIORIDADES
# ─────────────────────────────────────────────

class TestPriorities:
    def test_vip_has_highest_priority(self):
        """VIP tem o menor número → maior prioridade no SimPy."""
        assert PRIORITY_VIP < PRIORITY_FAN < PRIORITY_GENERAL

    def test_priority_values(self):
        assert PRIORITY_VIP == 0
        assert PRIORITY_FAN == 1
        assert PRIORITY_GENERAL == 2


# ─────────────────────────────────────────────
# BASELINE
# ─────────────────────────────────────────────

class TestBaseline:
    def test_name(self):
        assert BASELINE.name == "Baseline"

    def test_app_disabled(self):
        assert BASELINE.app_enabled is False

    def test_active_management_disabled(self):
        assert BASELINE.active_management is False

    def test_vip_priority_disabled(self):
        assert BASELINE.vip_priority is False

    def test_app_adoption_all_zero(self):
        for rate in BASELINE.app_adoption_rate.values():
            assert rate == 0.0

    def test_compliance_all_zero(self):
        for rate in BASELINE.compliance_rate.values():
            assert rate == 0.0

    def test_info_delay_zero(self):
        assert BASELINE.info_delay == 0.0


# ─────────────────────────────────────────────
# INFORMATIVE APP
# ─────────────────────────────────────────────

class TestInformativeApp:
    def test_name(self):
        assert INFORMATIVE_APP.name == "Informative App"

    def test_app_enabled(self):
        assert INFORMATIVE_APP.app_enabled is True

    def test_active_management_disabled(self):
        assert INFORMATIVE_APP.active_management is False

    def test_vip_priority_disabled(self):
        assert INFORMATIVE_APP.vip_priority is False

    def test_adoption_rates_in_range(self):
        for profile, rate in INFORMATIVE_APP.app_adoption_rate.items():
            assert 0.0 < rate <= 1.0, f"Taxa inválida para {profile}: {rate}"

    def test_fan_has_highest_adoption(self):
        """Fãs são os mais atentos ao lineup — devem ter maior taxa de adoção."""
        rates = INFORMATIVE_APP.app_adoption_rate
        assert rates["fan"] >= rates["general"]
        assert rates["fan"] >= rates["vip"]

    def test_info_delay_positive(self):
        assert INFORMATIVE_APP.info_delay > 0.0


# ─────────────────────────────────────────────
# ACTIVE MANAGEMENT
# ─────────────────────────────────────────────

class TestActiveManagement:
    def test_name(self):
        assert ACTIVE_MANAGEMENT.name == "Active Management"

    def test_app_enabled(self):
        assert ACTIVE_MANAGEMENT.app_enabled is True

    def test_active_management_enabled(self):
        assert ACTIVE_MANAGEMENT.active_management is True

    def test_vip_priority_disabled(self):
        assert ACTIVE_MANAGEMENT.vip_priority is False

    def test_congestion_threshold_valid(self):
        assert 0.0 < ACTIVE_MANAGEMENT.congestion_threshold <= 1.0

    def test_compliance_rates_in_range(self):
        for profile, rate in ACTIVE_MANAGEMENT.compliance_rate.items():
            assert 0.0 <= rate <= 1.0, f"Taxa inválida para {profile}: {rate}"

    def test_vip_lowest_compliance(self):
        """VIPs tendem a ignorar recomendações — menor compliance."""
        rates = ACTIVE_MANAGEMENT.compliance_rate
        assert rates["vip"] < rates["general"]
        assert rates["vip"] < rates["fan"]


# ─────────────────────────────────────────────
# VIP PRIORITY
# ─────────────────────────────────────────────

class TestVIPPriority:
    def test_name(self):
        assert VIP_PRIORITY.name == "VIP Priority"

    def test_vip_priority_enabled(self):
        assert VIP_PRIORITY.vip_priority is True

    def test_active_management_enabled(self):
        assert VIP_PRIORITY.active_management is True

    def test_app_enabled(self):
        assert VIP_PRIORITY.app_enabled is True

    def test_inherits_same_rates_as_active(self):
        """VIP Priority baseia-se na Gestão Ativa — taxas devem ser iguais."""
        assert VIP_PRIORITY.app_adoption_rate == ACTIVE_MANAGEMENT.app_adoption_rate
        assert VIP_PRIORITY.compliance_rate == ACTIVE_MANAGEMENT.compliance_rate
        assert VIP_PRIORITY.congestion_threshold == ACTIVE_MANAGEMENT.congestion_threshold


# ─────────────────────────────────────────────
# ALL_POLICIES
# ─────────────────────────────────────────────

class TestAllPolicies:
    def test_has_four_policies(self):
        assert len(ALL_POLICIES) == 4

    def test_order(self):
        names = [p.name for p in ALL_POLICIES]
        assert names == ["Baseline", "Informative App", "Active Management", "VIP Priority"]

    def test_all_have_unique_names(self):
        names = [p.name for p in ALL_POLICIES]
        assert len(names) == len(set(names))


# ─────────────────────────────────────────────
# HELPER: is_congested()
# ─────────────────────────────────────────────

class TestIsCongested:
    def test_above_threshold(self):
        assert ACTIVE_MANAGEMENT.is_congested(occupancy=90, capacity=100) is True

    def test_below_threshold(self):
        assert ACTIVE_MANAGEMENT.is_congested(occupancy=50, capacity=100) is False

    def test_exactly_at_threshold(self):
        # 85/100 = 0.85 — exatamente no threshold → congestionado
        assert ACTIVE_MANAGEMENT.is_congested(occupancy=85, capacity=100) is True

    def test_zero_capacity(self):
        assert ACTIVE_MANAGEMENT.is_congested(occupancy=0, capacity=0) is False

    def test_baseline_never_triggers(self):
        """Baseline não tem gestão ativa — o threshold existe mas não é usado."""
        # is_congested() é um helper puro, funciona em qualquer PolicyConfig
        assert BASELINE.is_congested(occupancy=100, capacity=100) is True


# ─────────────────────────────────────────────
# HELPER: agent_uses_app()
# ─────────────────────────────────────────────

class TestAgentUsesApp:
    def test_baseline_never_uses_app(self):
        """Baseline tem taxa 0 — nenhum agente usa a app."""
        import random
        rng = random.Random(42)
        results = [BASELINE.agent_uses_app("general", rng) for _ in range(100)]
        assert all(r is False for r in results)

    def test_informative_app_general_uses_app(self):
        """Com taxa 0.65, a maioria dos agentes gerais usa a app."""
        import random
        rng = random.Random(42)
        results = [INFORMATIVE_APP.agent_uses_app("general", rng) for _ in range(1000)]
        rate = sum(results) / len(results)
        assert 0.55 < rate < 0.75  # tolerância de ±10%

    def test_informative_app_fan_uses_app_more(self):
        """Fãs têm taxa 0.90 — quase todos usam a app."""
        import random
        rng = random.Random(42)
        results = [INFORMATIVE_APP.agent_uses_app("fan", rng) for _ in range(1000)]
        rate = sum(results) / len(results)
        assert rate > 0.80

    def test_unknown_profile_returns_false(self):
        """Perfil desconhecido → taxa 0.0 → nunca usa app."""
        import random
        rng = random.Random(42)
        assert INFORMATIVE_APP.agent_uses_app("unknown_profile", rng) is False


# ─────────────────────────────────────────────
# HELPER: agent_follows_recommendation()
# ─────────────────────────────────────────────

class TestAgentFollowsRecommendation:
    def test_baseline_never_follows(self):
        """Baseline tem compliance 0 — nenhum agente segue recomendações."""
        import random
        rng = random.Random(42)
        results = [BASELINE.agent_follows_recommendation("general", rng) for _ in range(100)]
        assert all(r is False for r in results)

    def test_active_management_general_follows(self):
        """General tem 70% de compliance."""
        import random
        rng = random.Random(42)
        results = [ACTIVE_MANAGEMENT.agent_follows_recommendation("general", rng) for _ in range(1000)]
        rate = sum(results) / len(results)
        assert 0.60 < rate < 0.80

    def test_vip_follows_less_than_general(self):
        """VIPs seguem recomendações menos que o público geral."""
        import random
        rng = random.Random(42)
        vip_results = [ACTIVE_MANAGEMENT.agent_follows_recommendation("vip", rng) for _ in range(1000)]
        gen_results = [ACTIVE_MANAGEMENT.agent_follows_recommendation("general", rng) for _ in range(1000)]
        assert sum(vip_results) < sum(gen_results)