from typing import Any, TypedDict

from signalpost.schemas.profile import (
    CompanyProfile,
    Fact,
    FinancialYear,
    RejectedFact,
    Role,
)


class AgentState(TypedDict, total=False):
    # Inputs
    org_number: str
    target_date: str | None

    # Validation
    is_valid_orgnr: bool
    checksum_error: str | None

    # Registry Data
    found_in_registry: bool
    legal_name: str
    status: str  # ACTIVE, BANKRUPT, IN_LIQUIDATION, DISSOLVED, NOT_FOUND
    org_form: str
    registered_date: str | None
    nace_codes: list[str]
    address: str | None
    municipality: str | None
    municipality_number: str | None
    employees: int | None
    vat_registered: bool | None
    website: str | None

    # Sub-entities
    roles: list[Role]
    financials: list[FinancialYear]
    contact: dict[str, Any]
    social_links: list[str]
    description: str | None

    # Web Crawl & Matching
    candidate_urls: list[str]
    web_crawl_data: dict[str, Any] | None
    is_matched_entity: bool
    match_signals: list[str]

    # Facts & Provenance
    facts: list[Fact]
    rejected_facts: list[RejectedFact]
    warnings: list[str]

    # Metadata & Accounting
    requests_used: int
    cost_usd: float
    start_time: float
    duration_ms: int
    history_ref: str | None
    profile_updated_at: str
    last_checked_at: str

    # Execution control
    stop_early: bool
    error: str | None

    # Output
    final_profile: CompanyProfile | None
