import json
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from signalpost.schemas.profile import CompanyProfile


def export_json_schema(output_path: Path) -> None:
    schema = CompanyProfile.model_json_schema()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"Exported JSON Schema to {output_path}")


if __name__ == "__main__":
    out_file = Path(__file__).resolve().parent / "company_profile.schema.json"
    export_json_schema(out_file)
