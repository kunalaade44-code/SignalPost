from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Fact(BaseModel):
    field: str = Field(..., description="Field name (e.g. legal_name, employees, revenue_2023)")
    value: Any = Field(..., description="Verbatim or validated value, or null if omitted")
    source_url: str = Field(..., description="Verifiable public URL where this fact originates")
    source_type: str = Field(
        ...,
        description="Type of source: 'registry_enheter', 'registry_regnskap', 'company_website', 'gazette', 'other'"
    )
    retrieved_at: str = Field(..., description="ISO-8601 UTC timestamp of retrieval")
    evidence: str = Field(..., description="Verbatim evidence quote, snippet or structured field path")
    match_signals: list[str] = Field(
        default_factory=list,
        description="Signals used to verify fact attribution (e.g. 'exact_orgnr', 'name_match>=0.9')"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    explanation: str = Field(..., description="Human-readable provenance and reasoning for the fact")


class RejectedFact(BaseModel):
    field: str = Field(..., description="Field attempted")
    candidate_value: Any = Field(..., description="The value that was considered")
    source_url: str = Field(..., description="URL where value was found")
    reason: str = Field(..., description="Explanation of why the fact was rejected")
    confidence: float = Field(0.0, description="Evaluated confidence score")


class Role(BaseModel):
    role: str = Field(..., description="Official role title, e.g., 'Daglig leder', 'Styrets leder'")
    name: str = Field(..., description="Full legal name of the person or entity")
    from_date: str | None = Field(None, description="Date registered or effective (YYYY-MM-DD)")
    resigned: bool | None = Field(False, description="Whether the person has resigned from the role")


class FinancialYear(BaseModel):
    year: int = Field(..., description="Fiscal year (e.g. 2023)")
    revenue: float | None = Field(None, description="Operating revenue / driftsinntekter in NOK")
    profit: float | None = Field(None, description="Operating profit / driftsresultat in NOK")
    operating_profit: float | None = Field(None, description="Operating profit / driftsresultat")
    net_profit: float | None = Field(None, description="Annual net profit / aarsresultat")
    assets: float | None = Field(None, description="Total assets / sum eiendeler")
    equity: float | None = Field(None, description="Total equity / sum egenkapital")
    currency: str = Field("NOK", description="Currency (verbatim from registry, standard NOK)")
    source_url: str = Field(..., description="Direct Brreg regnskap API endpoint URL")


class ContactInfo(BaseModel):
    email: str | None = Field(None, description="Verified company email")
    phone: str | None = Field(None, description="Verified telephone number")
    postal_address: str | None = Field(None, description="Registered postal address")
    visiting_address: str | None = Field(None, description="Registered business / visiting address")


class RunMetadata(BaseModel):
    requests: int = Field(0, description="Number of outbound HTTP requests used")
    cost_usd: float = Field(0.0, description="Declared external API cost in USD")
    duration_ms: int | None = Field(None, description="Wall-clock execution time in milliseconds")
    cached: bool | None = Field(False, description="Whether data was served from fresh cache")


class CompanyProfile(BaseModel):
    org_number: str = Field(..., description="9-digit Norwegian organization number")
    legal_name: str = Field(..., description="Official registered legal company name")
    status: str = Field(..., description="ACTIVE, BANKRUPT, IN_LIQUIDATION, DISSOLVED, DELETED")
    org_form: str = Field(..., description="Norwegian organizational form description (e.g. AS, ASA, ENK)")
    registered_date: str | None = Field(None, description="Registration date in registry (YYYY-MM-DD)")
    nace_codes: list[str] = Field(default_factory=list, description="NACE industry activity codes and titles")
    address: str | None = Field(None, description="Primary business address line")
    municipality: str | None = Field(None, description="Municipality name (e.g. OSLO, BERGEN)")
    municipality_number: str | None = Field(None, description="Official 4-digit municipality code")
    employees: int | None = Field(None, description="Number of registered employees")
    vat_registered: bool | None = Field(None, description="Registered in Merverdiavgiftsregisteret (MVA)")
    website: str | None = Field(None, description="Verified official website URL")
    contact: ContactInfo = Field(default_factory=ContactInfo, description="Verified contact details")
    roles: list[Role] = Field(default_factory=list, description="Registered corporate roles (management, board)")
    financials: list[FinancialYear] = Field(default_factory=list, description="Verbatim official annual accounts")
    description: str | None = Field(None, description="Verified company business description")
    social_links: list[str] = Field(default_factory=list, description="Verified official social media profile links")
    facts: list[Fact] = Field(default_factory=list, description="Granular verified facts with full provenance")
    rejected_facts: list[RejectedFact] = Field(
        default_factory=list,
        description="Candidate facts rejected by entity matching or validation guardrails"
    )
    profile_updated_at: str = Field(..., description="ISO-8601 UTC timestamp of last profile update")
    last_checked_at: str = Field(..., description="ISO-8601 UTC timestamp of last inspection")
    history_ref: str | None = Field(None, description="Hash or UUID of latest version revision")
    is_tracked: bool = Field(default=False, description="Whether the company is in the active watchlist")
    run_metadata: RunMetadata = Field(default_factory=RunMetadata, description="Execution resource accounting")

    @field_validator("org_number")
    @classmethod
    def validate_org_number(cls, v: str) -> str:
        clean = re.sub(r"\s+", "", v)
        if not re.fullmatch(r"^\d{9}$", clean):
            raise ValueError(f"Organization number must be exactly 9 digits, got '{v}'")
        return clean
