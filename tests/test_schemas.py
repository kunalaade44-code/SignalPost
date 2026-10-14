import pytest
from pydantic import ValidationError
from signalpost.schemas.profile import (
    CompanyProfile,
    ContactInfo,
    Fact,
    FinancialYear,
    Role,
    RunMetadata,
)


class TestSchemas:
    def test_company_profile_valid(self):
        profile = CompanyProfile(
            org_number="923609016",
            legal_name="EQUINOR ASA",
            status="ACTIVE",
            org_form="Allment aksjeselskap (ASA)",
            registered_date="1995-08-09",
            nace_codes=["06.100 - Utvinning av råolje"],
            address="Forusbeen 50, 4035 STAVANGER",
            municipality="STAVANGER",
            municipality_number="1103",
            employees=21500,
            vat_registered=True,
            website="https://www.equinor.com",
            contact=ContactInfo(visiting_address="Forusbeen 50"),
            roles=[
                Role(role="Daglig leder", name="Anders Opedal")
            ],
            financials=[
                FinancialYear(
                    year=2023,
                    revenue=1150000000000.0,
                    profit=380000000000.0,
                    currency="NOK",
                    source_url="https://data.brreg.no/regnskapsregisteret/regnskap/923609016",
                )
            ],
            facts=[
                Fact(
                    field="legal_name",
                    value="EQUINOR ASA",
                    source_url="https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
                    source_type="registry_enheter",
                    retrieved_at="2026-10-14T10:00:00Z",
                    evidence="enhet.navn: EQUINOR ASA",
                    match_signals=["exact_orgnr_in_official_registry"],
                    confidence=1.0,
                    explanation="Official registered legal company name from Brønnøysundregistrene.",
                )
            ],
            profile_updated_at="2026-10-14T10:00:00Z",
            last_checked_at="2026-10-14T10:00:00Z",
            run_metadata=RunMetadata(requests=3, cost_usd=0.0),
        )

        assert profile.org_number == "923609016"
        assert profile.financials[0].revenue == 1150000000000.0
        assert profile.financials[0].currency == "NOK"
        assert len(profile.facts) == 1

    def test_invalid_org_number_fails_pydantic_validation(self):
        with pytest.raises(ValidationError):
            CompanyProfile(
                org_number="12345",  # Too short
                legal_name="Test AS",
                status="ACTIVE",
                org_form="AS",
                profile_updated_at="2026-10-14T10:00:00Z",
                last_checked_at="2026-10-14T10:00:00Z",
            )
