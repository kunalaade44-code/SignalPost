from pathlib import Path

import pytest
import respx
from signalpost.cli.batch_runner import BatchRunner
from signalpost.config import settings


@pytest.mark.asyncio
async def test_batch_runner_execution(tmp_path, sample_brreg_entity_json, sample_brreg_roles_json, sample_brreg_regnskap_json):
    input_file = tmp_path / "test_orgnrs.txt"
    out_dir = tmp_path / "out"

    # Write 2 valid org numbers
    input_file.write_text("923609016\n984851006\n", encoding="utf-8")

    runner = BatchRunner(
        input_path=input_file,
        out_dir=out_dir,
        concurrency=2,
        force_refresh=True,
    )

    with respx.mock(assert_all_called=False) as respx_mock:
        # Mock responses for both companies
        for nr in ["923609016", "984851006"]:
            entity_data = dict(sample_brreg_entity_json)
            entity_data["organisasjonsnummer"] = nr
            respx_mock.get(f"{settings.brreg_enheter_base_url}/enheter/{nr}").respond(
                status_code=200, json=entity_data
            )
            respx_mock.get(f"{settings.brreg_enheter_base_url}/enheter/{nr}/roller").respond(
                status_code=200, json=sample_brreg_roles_json
            )
            respx_mock.get(f"{settings.brreg_regnskap_base_url}/{nr}").respond(
                status_code=200, json=sample_brreg_regnskap_json
            )
            respx_mock.get("https://www.equinor.com").respond(
                status_code=200, text="<html><body>Equinor ASA 923 609 016</body></html>"
            )

        res = await runner.run()

        assert res["completed_count"] == 2
        assert Path(res["summary_csv"]).exists()
        assert Path(res["quality_report"]).exists()

        # Check individual JSONs created
        assert (out_dir / "profiles" / "923609016.json").exists()
        assert (out_dir / "profiles" / "984851006.json").exists()

        # Check summary CSV contents
        csv_text = Path(res["summary_csv"]).read_text(encoding="utf-8")
        assert "923609016" in csv_text
        assert "984851006" in csv_text
        assert "EQUINOR ASA" in csv_text
