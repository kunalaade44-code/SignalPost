from typing import Any

from sqlmodel import JSON, Column, Field, SQLModel


class CompanyProfileModel(SQLModel, table=True):
    __tablename__ = "company_profiles"

    org_number: str = Field(primary_key=True, index=True, max_length=9)
    legal_name: str = Field(index=True)
    status: str = Field(index=True)
    org_form: str
    registered_date: str | None = None
    nace_codes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    address: str | None = None
    municipality: str | None = Field(default=None, index=True)
    municipality_number: str | None = None
    employees: int | None = None
    vat_registered: bool | None = None
    website: str | None = None
    contact: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    roles: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    financials: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    description: str | None = None
    social_links: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    facts_count: int = Field(default=0)
    profile_updated_at: str
    last_checked_at: str
    history_ref: str | None = None
    is_tracked: bool = Field(default=False, index=True)
    raw_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class FactModel(SQLModel, table=True):
    __tablename__ = "company_facts"

    id: int | None = Field(default=None, primary_key=True)
    org_number: str = Field(index=True, max_length=9)
    field_name: str = Field(index=True)
    value: Any = Field(sa_column=Column(JSON))
    source_url: str
    source_type: str = Field(index=True)
    retrieved_at: str
    evidence: str
    match_signals: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    confidence: float
    explanation: str
    content_hash: str = Field(index=True)
    is_stale: bool = Field(default=False)


class CompanyHistoryModel(SQLModel, table=True):
    __tablename__ = "company_history"

    id: int | None = Field(default=None, primary_key=True)
    org_number: str = Field(index=True, max_length=9)
    revision_ref: str = Field(index=True)
    changed_at: str
    change_reason: str
    field_name: str
    old_value: Any | None = Field(default=None, sa_column=Column(JSON))
    new_value: Any | None = Field(default=None, sa_column=Column(JSON))


class RunModel(SQLModel, table=True):
    __tablename__ = "execution_runs"

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(unique=True, index=True)
    started_at: str
    completed_at: str | None = None
    total_companies: int = Field(default=0)
    processed_count: int = Field(default=0)
    successful_count: int = Field(default=0)
    failed_count: int = Field(default=0)
    requests_used: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    duration_seconds: float | None = None
    status: str = Field(default="RUNNING", index=True)
