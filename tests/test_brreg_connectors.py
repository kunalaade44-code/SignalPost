import httpx
import pytest
import respx
from signalpost.config import settings
from signalpost.connectors.brreg_enheter import BrregEnheterConnector
from signalpost.connectors.brreg_regnskap import BrregRegnskapConnector


@pytest.mark.asyncio
async def test_brreg_enheter_connector_success(sample_brreg_entity_json, sample_brreg_roles_json):
    orgnr = "923609016"
    connector = BrregEnheterConnector()

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url=settings.brreg_enheter_base_url) as respx_mock:
            respx_mock.get(f"/enheter/{orgnr}").respond(
                status_code=200,
                json=sample_brreg_entity_json,
            )
            respx_mock.get(f"/enheter/{orgnr}/roller").respond(
                status_code=200,
                json=sample_brreg_roles_json,
            )

            result = await connector.fetch(client, orgnr)

            assert result["found"] is True
            assert result["legal_name"] == "EQUINOR ASA"
            assert result["status"] == "ACTIVE"
            assert result["employees"] == 21500
            assert result["vat_registered"] is True
            assert "06.100 - Utvinning av råolje" in result["nace_codes"]

            # Verify key roles
            assert len(result["roles"]) == 2
            daglig_leder = next((r for r in result["roles"] if "daglig" in r.role.lower()), None)
            assert daglig_leder is not None
            assert daglig_leder.name == "Anders Opedal"

            # Check facts generated
            facts = result["facts"]
            assert len(facts) >= 6
            name_fact = next((f for f in facts if f.field == "legal_name"), None)
            assert name_fact is not None
            assert name_fact.confidence == 1.0
            assert "exact_orgnr_in_official_registry" in name_fact.match_signals
            assert name_fact.source_url.startswith(settings.brreg_enheter_base_url)


@pytest.mark.asyncio
async def test_brreg_enheter_connector_not_found():
    orgnr = "999999999"
    connector = BrregEnheterConnector()

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url=settings.brreg_enheter_base_url) as respx_mock:
            respx_mock.get(f"/enheter/{orgnr}").respond(status_code=404)

            result = await connector.fetch(client, orgnr)
            assert result["found"] is False


@pytest.mark.asyncio
async def test_brreg_regnskap_connector_verbatim_extraction(sample_brreg_regnskap_json):
    orgnr = "923609016"
    connector = BrregRegnskapConnector()

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url=settings.brreg_regnskap_base_url) as respx_mock:
            respx_mock.get(f"/{orgnr}").respond(
                status_code=200,
                json=sample_brreg_regnskap_json,
            )

            result = await connector.fetch(client, orgnr)

            assert result["found"] is True
            assert len(result["financials"]) == 1
            fin = result["financials"][0]
            assert fin.year == 2023
            # Strict verbatim assertion
            assert fin.revenue == 1150000000000.0
            assert fin.profit == 380000000000.0
            assert fin.assets == 1750000000000.0
            assert fin.equity == 560000000000.0
            assert fin.currency == "NOK"

            # Strict assertion: facts generated from registry
            rev_fact = next((f for f in result["facts"] if f.field == "revenue_2023"), None)
            assert rev_fact is not None
            assert rev_fact.value == 1150000000000.0
            assert rev_fact.confidence == 1.0
            assert rev_fact.source_type == "registry_regnskap"


@pytest.mark.asyncio
async def test_brreg_regnskap_connector_no_accounts():
    orgnr = "999999999"
    connector = BrregRegnskapConnector()

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url=settings.brreg_regnskap_base_url) as respx_mock:
            respx_mock.get(f"/{orgnr}").respond(status_code=404)

            result = await connector.fetch(client, orgnr)
            assert result["found"] is False
            assert len(result["financials"]) == 0
            assert len(result["facts"]) == 0
