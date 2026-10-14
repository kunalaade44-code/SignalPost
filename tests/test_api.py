import json

import pytest
import respx
from fastapi.testclient import TestClient
from signalpost.api.app import app
from signalpost.config import settings
from signalpost.storage.database import init_db


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


def test_api_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["app"] == "Signalpost"


def test_api_stats(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "database" in data
    assert "limits" in data


def test_api_company_invalid_checksum(client):
    # Invalid 9-digit orgnr
    resp = client.get("/api/company/123456789")
    assert resp.status_code == 400
    assert "Invalid Norwegian organization number" in resp.json()["detail"]


def test_api_company_success(client, sample_brreg_entity_json, sample_brreg_roles_json, sample_brreg_regnskap_json):
    orgnr = "923609016"

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(f"{settings.brreg_enheter_base_url}/enheter/{orgnr}").respond(
            status_code=200, json=sample_brreg_entity_json
        )
        respx_mock.get(f"{settings.brreg_enheter_base_url}/enheter/{orgnr}/roller").respond(
            status_code=200, json=sample_brreg_roles_json
        )
        respx_mock.get(f"{settings.brreg_regnskap_base_url}/{orgnr}").respond(
            status_code=200, json=sample_brreg_regnskap_json
        )
        respx_mock.get("https://www.equinor.com").respond(
            status_code=200, text="<html><body>Equinor ASA 923 609 016</body></html>"
        )
        respx_mock.post("https://api.mistral.ai/v1/chat/completions").respond(
            status_code=200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "description": "Equinor ASA is a leading international energy company.",
                                "products_or_services": ["Oil", "Gas", "Wind"],
                                "evidence_quote": "Equinor ASA 923 609 016",
                                "explanation": "Extracted from official site."
                            })
                        }
                    }
                ]
            },
        )

        resp = client.get(f"/api/company/{orgnr}?force=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["org_number"] == "923609016"
        assert data["legal_name"] == "EQUINOR ASA"
        assert data["status"] == "ACTIVE"
        assert len(data["facts"]) > 5

        # Check history endpoint
        hist_resp = client.get(f"/api/company/{orgnr}/history")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert hist_data["org_number"] == "923609016"
        assert hist_data["revision_count"] >= 1


def test_api_batch_run_initiation(client):
    payload = {
        "org_numbers": ["923609016", "984851006"],
        "concurrency": 2,
    }
    resp = client.post("/api/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "QUEUED"
    assert data["total_companies"] == 2


def test_api_list_companies(client):
    resp = client.get("/api/companies?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1


def test_api_search_companies_by_name(client):
    mock_brreg_search_resp = {
        "_embedded": {
            "enheter": [
                {
                    "organisasjonsnummer": "923609016",
                    "navn": "EQUINOR ASA",
                    "organisasjonsform": {"kode": "ASA"},
                    "forretningsadresse": {"kommune": "STAVANGER", "adresse": ["Forusbeen 50"]},
                    "konkurs": False,
                }
            ]
        }
    }
    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(f"{settings.brreg_enheter_base_url}/enheter").respond(
            status_code=200, json=mock_brreg_search_resp
        )
        resp = client.get("/api/companies/search?q=Equinor")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["org_number"] == "923609016"


def test_api_preview_company(client, sample_brreg_entity_json):
    orgnr = "923609016"
    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(f"{settings.brreg_enheter_base_url}/enheter/{orgnr}").respond(
            status_code=200, json=sample_brreg_entity_json
        )
        resp = client.get(f"/api/companies/{orgnr}/preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["org_number"] == orgnr
        assert data["legal_name"] == "EQUINOR ASA"
        assert data["status"] == "ACTIVE"


def test_api_preview_company_invalid(client):
    resp = client.get("/api/companies/123456789/preview")
    assert resp.status_code == 400


def test_api_add_company_invalid(client):
    resp = client.post("/api/companies", json={"org_number": "123456789", "track": True})
    assert resp.status_code == 400


def test_api_bulk_add_companies(client):
    payload = {
        "org_numbers": ["923609016", "984851006"],
        "track": True,
        "concurrency": 2,
    }
    resp = client.post("/api/companies/bulk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_batch_worker_accurate_counting_cached_and_new():
    from signalpost.api.app import ACTIVE_RUNS, _run_batch_worker

    run_id = "test_run_counting"
    ACTIVE_RUNS[run_id] = {
        "run_id": run_id,
        "status": "QUEUED",
        "total_companies": 2,
        "processed_count": 0,
        "successful_count": 0,
        "cached_count": 0,
        "failed_count": 0,
        "progress_pct": 0.0,
        "results": [],
    }

    # 923609016 and 984851006 are pre-seeded in the database
    await _run_batch_worker(run_id, ["923609016", "984851006"], concurrency=2, force=False)

    state = ACTIVE_RUNS[run_id]
    assert state["status"] == "COMPLETED"
    assert state["total_companies"] == 2
    assert state["processed_count"] == 2  # Must be exactly 2, never double counted!
    assert state["cached_count"] == 2
    assert state["progress_pct"] == 100.0  # Must be 100.0%, never 200%!
    assert len(state["results"]) == 2


