"""Extract the high-signal fields from ToR .docx files into a JSON dataset.

These ToRs are template-generated: every document shares a large amount of
boilerplate (Purpose preamble, Composition, Quorum, Resolutions, Reporting,
Review). Embedding the raw document text lets that boilerplate dominate the
vector and inflates cosine similarity across *every* pair. So instead of
dumping full text, we pull out only the fields that actually distinguish one
governance group from another and assemble a compact ``embedding_text`` from
them.

Fields captured (see README for the rationale / signal ranking):
  - purpose_distinguishing : the one clause of the Purpose that isn't boilerplate
  - scope                  : the "Scope of Responsibilities" bullets (section 8)
  - reporting_line         : who the group reports to (section 6)
  - group_type             : Committee / Working Group / Taskforce / ... (from name)

Usage:
    python extract_tors.py                 # extract every .docx in the default folder
    python extract_tors.py --only-ten      # just the 10 curated for the demo table
    python extract_tors.py --src "<path>"  # point at a different ToR folder
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

# ToR folder ships alongside the repo, not inside it.
DEFAULT_SRC = (
    Path(__file__).resolve().parents[2]
    / "ClientGovernanceDataSet"
    / "Sandbox Data Set"
    / "Terms of Reference"
)
OUT_PATH = Path(__file__).resolve().parent / "tors.json"

# The 10 groups curated for the demo table. Chosen to include deliberate
# near-duplicate pairs (Research Data vs Information Governance; Education vs
# Faculty Education; Audit & Risk vs Finance) so a threshold can be calibrated.
CURATED_TEN = [
    "Research Data Governance Committee",
    "Research Information Governance Committee",
    "Education Committee",
    "Faculty Education Committee",
    "Audit and Risk Committee",
    "Finance Committee",
    "Cyber Security Oversight Group",
    "AI Governance Taskforce",
    "Sustainability Advisory Group",
    "Research Integrity Panel",
]

# Ground-truth relationships in the curated set, for threshold calibration.
GROUND_TRUTH_DUPLICATES = [
    ["Research Data Governance Committee", "Research Information Governance Committee"],
]


def _read_docx_text(path: Path) -> str:
    """Flatten a .docx to plain text (paragraph breaks preserved)."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = xml.replace("</w:p>", "\n")
    text = re.sub(r"<[^>]+>", "", xml)
    # normalise the mojibake apostrophes / dashes the template emits
    return text.replace("’", "'").replace("–", "-").replace("�", "'")


def _section(text: str, num: int) -> str:
    """Return the body of numbered section ``num`` (up to the next heading)."""
    m = re.search(rf"\n{num}\.\s*(.*?)(?=\n\d+\.\s)", text, re.S)
    return m.group(1).strip() if m else ""


def _group_type(name: str) -> str:
    """Infer the structural type from the group's name."""
    for suffix in ("Committee", "Board", "Panel", "Taskforce", "Forum", "Council"):
        if name.endswith(suffix):
            return suffix
    if name.endswith("Working Group"):
        return "Working Group"
    if name.endswith("Advisory Group"):
        return "Advisory Group"
    if name.endswith("Oversight Group"):
        return "Oversight Group"
    if name.endswith("Steering Committee") or name.endswith("Steering Group"):
        return "Steering Group"
    if name.endswith("Group"):
        return "Group"
    return "Group"


def _distinguishing_purpose(purpose_section: str) -> str:
    """Strip the boilerplate wrapper, keeping only the 'In practical terms' clause."""
    m = re.search(
        r"In practical terms,\s*(.*?)\.\s*The group provides",
        purpose_section,
        re.S,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    # fall back to the whole purpose minus its heading if the template shifts
    body = re.sub(r"^Purpose\s*", "", purpose_section).strip()
    return re.sub(r"\s+", " ", body)


def _reporting_line(reporting_section: str) -> str:
    m = re.search(r"provide reports? to\s+(.*?),", reporting_section)
    return m.group(1).strip() if m else ""


def _bullets(section_body: str) -> list[str]:
    """Section body → list of non-empty, non-heading lines."""
    lines = [ln.strip() for ln in section_body.split("\n")]
    # drop the heading line (first) and any empties
    return [ln for ln in lines[1:] if ln]


def extract_one(path: Path) -> dict:
    text = _read_docx_text(path)
    name = path.stem
    purpose = _distinguishing_purpose(_section(text, 1))
    scope = _bullets(_section(text, 8))
    reporting = _reporting_line(_section(text, 6))
    gtype = _group_type(name)

    # The embedding text: only high-signal, distinguishing fields — never the
    # raw document (see README for why).
    embedding_text = (
        f"{gtype}. "
        f"Purpose: {purpose} "
        f"Responsibilities: {'; '.join(scope)}. "
        f"Reports to: {reporting}."
    )

    return {
        "group_name": name,
        "group_type": gtype,
        "purpose_distinguishing": purpose,
        "reporting_line": reporting,
        "scope": scope,
        "embedding_text": embedding_text,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC, help="ToR .docx folder")
    ap.add_argument("--only-ten", action="store_true", help="only the curated 10")
    ap.add_argument("--out", type=Path, default=OUT_PATH, help="output JSON path")
    args = ap.parse_args()

    if not args.src.exists():
        raise SystemExit(f"ToR folder not found: {args.src}")

    files = sorted(args.src.glob("*.docx"))
    if args.only_ten:
        wanted = {n.lower() for n in CURATED_TEN}
        files = [f for f in files if f.stem.lower() in wanted]

    records = [extract_one(f) for f in files]
    payload = {
        "count": len(records),
        "ground_truth_duplicates": GROUND_TRUTH_DUPLICATES,
        "tors": records,
    }
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(records)} ToRs -> {args.out}")


if __name__ == "__main__":
    main()
