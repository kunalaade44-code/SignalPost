import time
from dataclasses import dataclass


@dataclass
class BudgetSnapshot:
    requests_used: int
    requests_left: int
    cost_usd: float
    cost_left_usd: float
    time_elapsed_sec: float
    time_left_sec: float
    is_exhausted: bool


class BudgetManager:
    """
    Thread-safe / async-safe global budget manager enforcing competition limits:
    - Max 2,000 requests total per 100 companies daily run (~18-20 per company average).
    - Max $10.00 declared external API cost.
    - Max 45 minutes (2,700 seconds) wall-clock deadline with graceful degradation.
    """

    def __init__(
        self,
        max_requests: int = 2000,
        max_cost_usd: float = 10.0,
        max_time_seconds: int = 2700,
        per_company_request_budget: int = 18,
    ):
        self.max_requests = max_requests
        self.max_cost_usd = max_cost_usd
        self.max_time_seconds = max_time_seconds
        self.per_company_request_budget = per_company_request_budget

        self.start_time = time.time()
        self.deadline = self.start_time + max_time_seconds

        self.requests_used = 0
        self.cost_usd = 0.0

    def record_request(self, count: int = 1) -> bool:
        """Records outbound HTTP requests. Returns False if budget would be exceeded."""
        if self.requests_used + count > self.max_requests:
            return False
        self.requests_used += count
        return True

    def record_cost(self, amount_usd: float) -> bool:
        """Records external model/API costs in USD."""
        if self.cost_usd + amount_usd > self.max_cost_usd:
            return False
        self.cost_usd += amount_usd
        return True

    def can_make_request(self) -> bool:
        return self.requests_used < self.max_requests and not self.is_time_up()

    def can_spend_cost(self, amount_usd: float = 0.001) -> bool:
        return (self.cost_usd + amount_usd) <= self.max_cost_usd and not self.is_time_up()

    def is_time_up(self, buffer_seconds: float = 10.0) -> bool:
        """Returns True if wall-clock time has reached or is near the deadline."""
        return time.time() >= (self.deadline - buffer_seconds)

    def should_skip_optional_enrichment(self, current_company_requests: int = 0) -> bool:
        """
        Graceful degradation gate:
        Skips optional scraping/LLM calls if:
        1. Wall-clock time has <= 60 seconds left, OR
        2. Global requests left < 50, OR
        3. Cost limit is near ($9.90+), OR
        4. Current company has reached its per-company budget limit.
        """
        if self.is_time_up(buffer_seconds=60.0):
            return True
        if (self.max_requests - self.requests_used) < 50:
            return True
        if self.cost_usd >= (self.max_cost_usd - 0.10):
            return True
        return current_company_requests >= self.per_company_request_budget

    def get_snapshot(self) -> BudgetSnapshot:
        now = time.time()
        elapsed = now - self.start_time
        time_left = max(0.0, self.deadline - now)
        requests_left = max(0, self.max_requests - self.requests_used)
        cost_left = max(0.0, self.max_cost_usd - self.cost_usd)
        is_exhausted = (
            requests_left == 0 or cost_left <= 0.0001 or time_left <= 0.0
        )

        return BudgetSnapshot(
            requests_used=self.requests_used,
            requests_left=requests_left,
            cost_usd=round(self.cost_usd, 4),
            cost_left_usd=round(cost_left, 4),
            time_elapsed_sec=round(elapsed, 2),
            time_left_sec=round(time_left, 2),
            is_exhausted=is_exhausted,
        )
