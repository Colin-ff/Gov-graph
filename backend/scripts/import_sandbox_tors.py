"""One-off bulk import: load the sandbox ToRs into ``governance_groups`` with embeddings.

This writes ``GovernanceGroup`` rows directly rather than going through
``POST /api/tor`` - the sandbox ``.docx`` files (see
``similarity_search/extract_tors.py``) only carry purpose/scope/reporting-line
text, not the chair/secretariat membership the real submission endpoint
requires. Re-running is safe: groups are matched by name and updated in place.

Usage (from ``backend/``, with the backend venv active and Postgres running):
    python ../similarity_search/extract_tors.py    # (re)writes tors.json, all 40
    python scripts/import_sandbox_tors.py            # loads tors.json -> DB
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on sys.path

from dotenv import load_dotenv  # noqa: E402

# Same repo-root .env wsgi.py loads, so this talks to the same DB as `flask run`.
load_dotenv(str(Path(__file__).resolve().parents[2] / ".env"))

from app import create_app  # noqa: E402
from app.db_schema import GovernanceGroup, GroupStatus  # noqa: E402
from app.extensions import db  # noqa: E402
from app.services import embedding_service, type_service  # noqa: E402

TORS_JSON = Path(__file__).resolve().parents[2] / "similarity_search" / "tors.json"


def _title_case(value: str) -> str:
    return " ".join(word[:1].upper() + word[1:] for word in value.split())


def import_tors(tors_json: Path = TORS_JSON) -> None:
    data = json.loads(tors_json.read_text(encoding="utf-8"))
    records = data["tors"]
    print(f"Importing {len(records)} ToRs from {tors_json} ...")

    for record in records:
        group_name = _title_case(record["group_name"].strip())
        group_type_id = type_service.get_or_create_group_type(record["group_type"])

        group = GovernanceGroup.query.filter_by(group_name=group_name).first()
        is_new = group is None
        if is_new:
            group = GovernanceGroup(group_name=group_name, status=GroupStatus.ACTIVE)
            db.session.add(group)

        group.group_type_id = group_type_id
        group.purpose = record["purpose_distinguishing"]
        group.responsibilities = "; ".join(record["scope"])
        group.embedding_text = record["embedding_text"]
        group.embedding = embedding_service.embed_text(record["embedding_text"])

        print(f"  {'created' if is_new else 'updated'} {group_name}")

    db.session.commit()
    print("Done.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        import_tors()
