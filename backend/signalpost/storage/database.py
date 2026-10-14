import hashlib
import json
import logging
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

from signalpost.config import settings
from signalpost.schemas.profile import CompanyProfile
from signalpost.storage.models import (
    CompanyHistoryModel,
    CompanyProfileModel,
    FactModel,
)
from sqlmodel import Session, SQLModel, create_engine, select

logger = logging.getLogger(__name__)

# Connect_args needed for SQLite thread concurrency
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Creates database tables if they do not exist, and applies lightweight schema migrations."""
    SQLModel.metadata.create_all(engine)
    try:
        with engine.connect() as conn:
            result = conn.exec_driver_sql("PRAGMA table_info(company_profiles)")
            columns = [row[1] for row in result.fetchall()]
            if columns and "is_tracked" not in columns:
                conn.exec_driver_sql("ALTER TABLE company_profiles ADD COLUMN is_tracked BOOLEAN DEFAULT 0")
                conn.commit()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Schema migration check: {e}")


def get_session() -> Generator[Session, None, None]:
    """Yields a database session."""
    with Session(engine) as session:
        yield session


def compute_fact_hash(field_name: str, value: Any) -> str:
    """Generates a deterministic SHA256 hash of a fact's content."""
    normalized = f"{field_name}:{json.dumps(value, sort_keys=True, ensure_ascii=False)}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def is_profile_fresh(org_number: str, session: Session, max_age_days: int = 7) -> bool:
    """
    Checks if an existing profile is fresh within the configured TTL.
    Used for the resume/skip feature in batch runs.
    """
    stmt = select(CompanyProfileModel).where(CompanyProfileModel.org_number == org_number)
    existing = session.exec(stmt).first()
    if not existing:
        return False

    try:
        last_checked = datetime.fromisoformat(existing.last_checked_at)
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
        return last_checked >= cutoff
    except (ValueError, TypeError):
        return False


def get_profile_by_orgnr(org_number: str, session: Session) -> CompanyProfile | None:
    """Retrieves a stored profile by organization number."""
    stmt = select(CompanyProfileModel).where(CompanyProfileModel.org_number == org_number)
    model = session.exec(stmt).first()
    if not model or not model.raw_json:
        return None

    try:
        return CompanyProfile.model_validate(model.raw_json)
    except (ValueError, TypeError, KeyError) as e:
        logger.warning(f"Error deserializing stored profile {org_number}: {e}")
        return None


def get_profile_history(org_number: str, session: Session) -> list[CompanyHistoryModel]:
    """Retrieves the version history / change diffs for an organization."""
    stmt = (
        select(CompanyHistoryModel)
        .where(CompanyHistoryModel.org_number == org_number)
        .order_by(CompanyHistoryModel.changed_at.desc())
    )
    return list(session.exec(stmt).all())


def save_or_update_profile(
    profile: CompanyProfile, session: Session
) -> tuple[CompanyProfileModel, list[CompanyHistoryModel]]:
    """
    Implements Section 7 Update & Diff Policy:
    1. Computes content hashes for each newly extracted fact.
    2. Detects changes against existing stored facts.
    3. Records diffs to company_history with timestamps and reasons.
    4. Never silently drops or overwrites unchanged valid data.
    5. Updates company_profiles table with latest snapshot.
    """
    now_iso = datetime.now(UTC).isoformat()
    orgnr = profile.org_number
    history_entries: list[CompanyHistoryModel] = []

    # 1. Fetch existing profile and facts
    existing_profile = session.exec(
        select(CompanyProfileModel).where(CompanyProfileModel.org_number == orgnr)
    ).first()

    existing_facts = list(
        session.exec(select(FactModel).where(FactModel.org_number == orgnr)).all()
    )
    existing_facts_by_field = {f.field_name: f for f in existing_facts}

    revision_ref = f"rev_{int(datetime.now(UTC).timestamp())}_{orgnr}"

    # 2. Compare incoming facts with existing facts
    for new_fact in profile.facts:
        new_hash = compute_fact_hash(new_fact.field, new_fact.value)
        old_fact = existing_facts_by_field.get(new_fact.field)

        if old_fact is None:
            # Newly discovered fact
            new_model = FactModel(
                org_number=orgnr,
                field_name=new_fact.field,
                value=new_fact.value,
                source_url=new_fact.source_url,
                source_type=new_fact.source_type,
                retrieved_at=new_fact.retrieved_at,
                evidence=new_fact.evidence,
                match_signals=new_fact.match_signals,
                confidence=new_fact.confidence,
                explanation=new_fact.explanation,
                content_hash=new_hash,
                is_stale=False,
            )
            session.add(new_model)

            # Record history entry for initial fact publication
            hist = CompanyHistoryModel(
                org_number=orgnr,
                revision_ref=revision_ref,
                changed_at=now_iso,
                change_reason=f"Initial discovery of {new_fact.field}",
                field_name=new_fact.field,
                old_value=None,
                new_value=new_fact.value,
            )
            session.add(hist)
            history_entries.append(hist)

        elif old_fact.content_hash != new_hash:
            # Fact value has changed: update and record in history!
            hist = CompanyHistoryModel(
                org_number=orgnr,
                revision_ref=revision_ref,
                changed_at=now_iso,
                change_reason=f"Updated value from {new_fact.source_type}",
                field_name=new_fact.field,
                old_value=old_fact.value,
                new_value=new_fact.value,
            )
            session.add(hist)
            history_entries.append(hist)

            # Update existing fact model
            old_fact.value = new_fact.value
            old_fact.source_url = new_fact.source_url
            old_fact.retrieved_at = new_fact.retrieved_at
            old_fact.evidence = new_fact.evidence
            old_fact.confidence = new_fact.confidence
            old_fact.content_hash = new_hash
            old_fact.is_stale = False
            session.add(old_fact)

        else:
            # Fact unchanged: touch retrieved_at / verify freshness
            old_fact.retrieved_at = new_fact.retrieved_at
            old_fact.is_stale = False
            session.add(old_fact)

    # 3. Update or create the profile snapshot model
    raw_dict = profile.model_dump()
    roles_dicts = [r.model_dump() for r in profile.roles]
    financials_dicts = [f.model_dump() for f in profile.financials]
    contact_dict = profile.contact.model_dump()

    if existing_profile:
        existing_profile.legal_name = profile.legal_name
        existing_profile.status = profile.status
        existing_profile.org_form = profile.org_form
        existing_profile.registered_date = profile.registered_date
        existing_profile.nace_codes = profile.nace_codes
        existing_profile.address = profile.address
        existing_profile.municipality = profile.municipality
        existing_profile.municipality_number = profile.municipality_number
        existing_profile.employees = profile.employees
        existing_profile.vat_registered = profile.vat_registered
        existing_profile.website = profile.website
        existing_profile.contact = contact_dict
        existing_profile.roles = roles_dicts
        existing_profile.financials = financials_dicts
        existing_profile.description = profile.description
        existing_profile.social_links = profile.social_links
        existing_profile.facts_count = len(profile.facts)
        existing_profile.is_tracked = getattr(profile, "is_tracked", False) or existing_profile.is_tracked
        existing_profile.profile_updated_at = now_iso
        existing_profile.last_checked_at = now_iso
        existing_profile.history_ref = revision_ref
        existing_profile.raw_json = raw_dict
        session.add(existing_profile)
        profile_model = existing_profile
    else:
        profile_model = CompanyProfileModel(
            org_number=orgnr,
            legal_name=profile.legal_name,
            status=profile.status,
            org_form=profile.org_form,
            registered_date=profile.registered_date,
            nace_codes=profile.nace_codes,
            address=profile.address,
            municipality=profile.municipality,
            municipality_number=profile.municipality_number,
            employees=profile.employees,
            vat_registered=profile.vat_registered,
            website=profile.website,
            contact=contact_dict,
            roles=roles_dicts,
            financials=financials_dicts,
            description=profile.description,
            social_links=profile.social_links,
            facts_count=len(profile.facts),
            is_tracked=getattr(profile, "is_tracked", False),
            profile_updated_at=now_iso,
            last_checked_at=now_iso,
            history_ref=revision_ref,
            raw_json=raw_dict,
        )
        session.add(profile_model)

    session.commit()
    session.refresh(profile_model)
    return profile_model, history_entries
