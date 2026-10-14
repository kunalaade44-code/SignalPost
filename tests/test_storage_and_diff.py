from datetime import UTC, datetime

import pytest
from signalpost.schemas.profile import CompanyProfile, Fact
from signalpost.storage.database import (
    engine,
    get_profile_by_orgnr,
    get_profile_history,
    init_db,
    is_profile_fresh,
    save_or_update_profile,
)
from signalpost.storage.models import CompanyHistoryModel, CompanyProfileModel, FactModel
from sqlmodel import Session, select


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    with Session(engine) as session:
        # Clear tables before each test
        session.exec(select(CompanyHistoryModel)).all()
        for m in [CompanyHistoryModel, FactModel, CompanyProfileModel]:
            for row in session.exec(select(m)).all():
                session.delete(row)
        session.commit()


def test_initial_save_profile_and_facts():
    now_iso = datetime.now(UTC).isoformat()
    profile = CompanyProfile(
        org_number="923609016",
        legal_name="EQUINOR ASA",
        status="ACTIVE",
        org_form="Allment aksjeselskap (ASA)",
        employees=21500,
        facts=[
            Fact(
                field="legal_name",
                value="EQUINOR ASA",
                source_url="https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
                source_type="registry_enheter",
                retrieved_at=now_iso,
                evidence="navn: EQUINOR ASA",
                match_signals=["exact_orgnr"],
                confidence=1.0,
                explanation="Official registered name",
            ),
            Fact(
                field="employees",
                value=21500,
                source_url="https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
                source_type="registry_enheter",
                retrieved_at=now_iso,
                evidence="antallAnsatte: 21500",
                match_signals=["exact_orgnr"],
                confidence=1.0,
                explanation="Official Aa-register count",
            ),
        ],
        profile_updated_at=now_iso,
        last_checked_at=now_iso,
    )

    with Session(engine) as session:
        model, history = save_or_update_profile(profile, session)
        assert model.org_number == "923609016"
        assert model.employees == 21500
        assert len(history) == 2  # 2 initial discoveries

        # Check retrieval
        stored = get_profile_by_orgnr("923609016", session)
        assert stored is not None
        assert stored.legal_name == "EQUINOR ASA"
        assert is_profile_fresh("923609016", session) is True


def test_update_and_diff_detection():
    now_iso = datetime.now(UTC).isoformat()
    profile_v1 = CompanyProfile(
        org_number="923609016",
        legal_name="EQUINOR ASA",
        status="ACTIVE",
        org_form="ASA",
        employees=21500,
        facts=[
            Fact(
                field="employees",
                value=21500,
                source_url="https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
                source_type="registry_enheter",
                retrieved_at=now_iso,
                evidence="antallAnsatte: 21500",
                match_signals=["exact_orgnr"],
                confidence=1.0,
                explanation="Official Aa-register count",
            )
        ],
        profile_updated_at=now_iso,
        last_checked_at=now_iso,
    )

    with Session(engine) as session:
        save_or_update_profile(profile_v1, session)

    # Re-run: Employees increased from 21,500 to 22,000
    profile_v2 = profile_v1.model_copy(deep=True)
    profile_v2.employees = 22000
    profile_v2.facts[0].value = 22000
    profile_v2.facts[0].evidence = "antallAnsatte: 22000"

    with Session(engine) as session:
        model_v2, history_v2 = save_or_update_profile(profile_v2, session)
        assert model_v2.employees == 22000

        # Diff must be recorded
        assert len(history_v2) == 1
        diff = history_v2[0]
        assert diff.field_name == "employees"
        assert diff.old_value == 21500
        assert diff.new_value == 22000
        assert "Updated value" in diff.change_reason

        # Check full history trail
        full_history = get_profile_history("923609016", session)
        assert len(full_history) == 2  # initial + update
