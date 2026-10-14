import pytest
import respx
from signalpost.agent.budget import BudgetManager
from signalpost.agent.graph import SignalpostAgent
from signalpost.config import settings


@pytest.mark.asyncio
async def test_agent_full_workflow_success(sample_brreg_entity_json, sample_brreg_roles_json, sample_brreg_regnskap_json):
    orgnr = "923609016"
    budget = BudgetManager(max_requests=100)
    agent = SignalpostAgent(budget_manager=budget)

    homepage_html = """
    <html>
      <head>
        <title>Equinor - Fornybar Energi og Olje</title>
        <meta name="description" content="Equinor er et bredt energiselskap med virksomhet i mer enn 30 land.">
      </head>
      <body>
        <h1>Equinor ASA</h1>
        <p>Vi er registrert i Norge med org.nr 923 609 016 MVA.</p>
        <p>Hovedkontor: Forusbeen 50, 4035 Stavanger.</p>
        <a href="mailto:kontakt@equinor.com">kontakt@equinor.com</a>
        <a href="https://www.linkedin.com/company/equinor">LinkedIn</a>
      </body>
    </html>
    """

    with respx.mock(assert_all_called=False) as respx_mock:
        # Mock Enhetsregisteret
        respx_mock.get(f"{settings.brreg_enheter_base_url}/enheter/{orgnr}").respond(
            status_code=200, json=sample_brreg_entity_json
        )
        respx_mock.get(f"{settings.brreg_enheter_base_url}/enheter/{orgnr}/roller").respond(
            status_code=200, json=sample_brreg_roles_json
        )
        # Mock Regnskapsregisteret
        respx_mock.get(f"{settings.brreg_regnskap_base_url}/{orgnr}").respond(
            status_code=200, json=sample_brreg_regnskap_json
        )
        # Mock company website
        respx_mock.get("https://www.equinor.com").respond(
            status_code=200, text=homepage_html
        )

        profile = await agent.run(orgnr)

        assert profile.org_number == "923609016"
        assert profile.legal_name == "EQUINOR ASA"
        assert profile.status == "ACTIVE"
        assert profile.employees == 21500
        assert profile.vat_registered is True
        assert len(profile.financials) >= 1
        assert profile.financials[0].revenue == 1150000000000.0

        # Facts check
        assert len(profile.facts) > 5
        # Verify provenance
        for fact in profile.facts:
            assert fact.source_url is not None
            assert fact.retrieved_at is not None
            assert fact.evidence is not None
            assert fact.confidence > 0.0
            assert fact.explanation is not None

        # STRICT ASSERTION: All financial facts must have registry source
        for fact in profile.facts:
            if any(k in fact.field for k in ["revenue", "profit", "assets", "equity"]):
                assert fact.source_type == "registry_regnskap"
                assert "regnskapsregisteret" in fact.source_url


@pytest.mark.asyncio
async def test_agent_bankrupt_company_stops_early(sample_brreg_entity_json):
    orgnr = "923609016"
    bankrupt_entity = dict(sample_brreg_entity_json)
    bankrupt_entity["konkurs"] = True

    budget = BudgetManager(max_requests=100)
    agent = SignalpostAgent(budget_manager=budget)

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(f"{settings.brreg_enheter_base_url}/enheter/{orgnr}").respond(
            status_code=200, json=bankrupt_entity
        )
        respx_mock.get(f"{settings.brreg_enheter_base_url}/enheter/{orgnr}/roller").respond(
            status_code=200, json={"rollegrupper": []}
        )
        respx_mock.get(f"{settings.brreg_regnskap_base_url}/{orgnr}").respond(
            status_code=404
        )

        profile = await agent.run(orgnr)

        assert profile.status == "BANKRUPT"
        # Bankrupt entity stops early; no website should be crawled
        status_fact = next((f for f in profile.facts if f.field == "status"), None)
        assert status_fact is not None
        assert status_fact.value == "BANKRUPT"


@pytest.mark.asyncio
async def test_agent_invalid_checksum_stops_at_input():
    # Corrupted 9-digit orgnr
    invalid_orgnr = "923609019"
    agent = SignalpostAgent()

    profile = await agent.run(invalid_orgnr)

    assert profile.status == "INVALID_CHECKSUM"
    assert profile.run_metadata.requests == 0
