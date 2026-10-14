import time

from signalpost.agent.budget import BudgetManager


class TestBudgetManager:
    def test_budget_initialization(self):
        manager = BudgetManager(max_requests=100, max_cost_usd=5.0, max_time_seconds=60)
        snap = manager.get_snapshot()

        assert snap.requests_used == 0
        assert snap.requests_left == 100
        assert snap.cost_usd == 0.0
        assert snap.cost_left_usd == 5.0
        assert snap.is_exhausted is False
        assert manager.can_make_request() is True
        assert manager.can_spend_cost(0.01) is True

    def test_request_limit_enforcement(self):
        manager = BudgetManager(max_requests=5)

        assert manager.record_request(3) is True
        assert manager.requests_used == 3
        assert manager.can_make_request() is True

        assert manager.record_request(2) is True
        assert manager.requests_used == 5
        # At cap: cannot make further requests
        assert manager.can_make_request() is False
        assert manager.record_request(1) is False

    def test_cost_limit_enforcement(self):
        manager = BudgetManager(max_cost_usd=0.10)

        assert manager.record_cost(0.05) is True
        assert manager.can_spend_cost(0.04) is True
        assert manager.record_cost(0.04) is True
        assert manager.can_spend_cost(0.02) is False

    def test_deadline_detection(self):
        # Set a 1-second deadline
        manager = BudgetManager(max_time_seconds=1)
        assert manager.is_time_up(buffer_seconds=0.0) is False

        time.sleep(1.1)
        assert manager.is_time_up(buffer_seconds=0.0) is True
        assert manager.can_make_request() is False

    def test_graceful_degradation_skips_optional_enrichment(self):
        manager = BudgetManager(max_requests=100, per_company_request_budget=5)

        # Company under budget: do not skip
        assert manager.should_skip_optional_enrichment(current_company_requests=2) is False

        # Company reached per-company budget limit: skip
        assert manager.should_skip_optional_enrichment(current_company_requests=5) is True

        # When global requests are low (< 50 left): skip
        manager.record_request(60)  # 40 left
        assert manager.should_skip_optional_enrichment(current_company_requests=1) is True
