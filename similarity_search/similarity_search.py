"""ToR duplicate-detection spike: embed -> cosine -> LLM verify.

Pipeline
--------
1. Embed each ToR's distilled ``embedding_text`` with all-mpnet-base-v2
   (L2-normalised, so cosine == dot product).
2. Compute the pairwise cosine-similarity matrix; save a heatmap; list every
   pair at or above ``--threshold`` as a *candidate* duplicate.
3. Send each candidate pair to Gemini, which returns a structured verdict
   (duplicate / not, with reasoning). The embedding stage favours recall; the
   LLM stage supplies precision.

Run:
    python extract_tors.py --only-ten          # produces tors.json
    python similarity_search.py                # uses default threshold 0.55
    python similarity_search.py --threshold 0.6
    # The LLM stage REQUIRES GEMINI_API_KEY — set it in the repo-root .env or
    # your shell. Without it, the script exits with an error unless you pass
    # --no-llm.
    python similarity_search.py --no-llm       # embedding + cosine only, no key needed
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google.genai import types

HERE = Path(__file__).resolve().parent
DEFAULT_TORS = HERE / "tors.json"
DEFAULT_HEATMAP = HERE / "similarity_heatmap.png"
MODEL_NAME = "all-mpnet-base-v2"
# Google's maintained alias for its current flash-lite model, rather than a
# version-pinned name -- version-pinned Gemini models get deprecated for new
# API keys over time (e.g. gemini-2.5-flash-lite already has been).
LLM_MODEL = "gemini-flash-lite-latest"

# Same repo-root .env the Flask backend loads (see backend/wsgi.py).
load_dotenv(HERE.parent / ".env")

# Verdict schema the LLM is constrained to (structured outputs).
VERDICT_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "is_duplicate": types.Schema(type=types.Type.BOOLEAN),
        "confidence": types.Schema(type=types.Type.STRING, enum=["low", "medium", "high"]),
        "reasoning": types.Schema(type=types.Type.STRING),
    },
    required=["is_duplicate", "confidence", "reasoning"],
)


def load_tors(path: Path) -> tuple[list[dict], list[list[str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["tors"], data.get("ground_truth_duplicates", [])


def embed(texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    # normalize_embeddings=True => cosine similarity is a plain dot product.
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def cosine_matrix(emb: np.ndarray) -> np.ndarray:
    return emb @ emb.T


def candidate_pairs(sims: np.ndarray, names: list[str], threshold: float):
    """Every i<j pair with cosine >= threshold, highest first."""
    pairs = []
    for i, j in itertools.combinations(range(len(names)), 2):
        score = float(sims[i, j])
        if score >= threshold:
            pairs.append((names[i], names[j], score, i, j))
    pairs.sort(key=lambda p: p[2], reverse=True)
    return pairs


def save_heatmap(sims: np.ndarray, names: list[str], out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(names)
    fig, ax = plt.subplots(figsize=(max(8, n * 0.7), max(7, n * 0.6)))
    im = ax.imshow(sims, cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(names, rotation=60, ha="right", fontsize=7)
    ax.set_yticklabels(names, fontsize=7)
    for i in range(n):
        for j in range(n):
            ax.text(
                j, i, f"{sims[i, j]:.2f}",
                ha="center", va="center",
                color="white" if sims[i, j] < 0.6 else "black", fontsize=6,
            )
    fig.colorbar(im, ax=ax, label="cosine similarity")
    ax.set_title(f"ToR cosine similarity ({MODEL_NAME}, distilled fields)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved heatmap -> {out}")


def verify_pair(client, a: dict, b: dict) -> dict:
    """Ask Gemini whether two ToRs describe duplicate governance groups."""
    prompt = (
        "You are auditing a university governance register for duplicate groups. "
        "Two groups are DUPLICATES if they have substantially the same purpose, "
        "scope and reporting line so that one is redundant. Groups that merely "
        "share a domain, or have the same purpose but a different jurisdiction or "
        "reporting line, are NOT duplicates.\n\n"
        f"GROUP A — {a['group_name']} ({a['group_type']})\n"
        f"  Purpose: {a['purpose_distinguishing']}\n"
        f"  Reports to: {a['reporting_line']}\n"
        f"  Scope: {'; '.join(a['scope'])}\n\n"
        f"GROUP B — {b['group_name']} ({b['group_type']})\n"
        f"  Purpose: {b['purpose_distinguishing']}\n"
        f"  Reports to: {b['reporting_line']}\n"
        f"  Scope: {'; '.join(b['scope'])}\n\n"
        "Decide whether A and B are duplicates."
    )
    resp = client.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VERDICT_SCHEMA,
        ),
    )
    return json.loads(resp.text)


def make_llm_client():
    """Return a Gemini client. Raises SystemExit if the SDK or credentials are missing.

    The LLM stage is the precision half of the pipeline (see module docstring) —
    running the recall stage alone without saying so would understate the
    duplicate risk, so a missing key is a hard error here rather than a silent
    skip. Pass --no-llm to opt out of the stage entirely.
    """
    try:
        from google import genai
    except ImportError as exc:
        raise SystemExit(
            "google-genai SDK not installed. Run `pip install -r requirements.txt`, "
            "or pass --no-llm to run embedding + cosine only."
        ) from exc

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit(
            "GEMINI_API_KEY is required for the LLM verification stage. Set it "
            "in the repo-root .env or export it in your shell. Pass --no-llm to "
            "skip this stage."
        )

    return genai.Client(api_key=api_key)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tors", type=Path, default=DEFAULT_TORS)
    ap.add_argument("--threshold", type=float, default=0.55,
                    help="cosine cutoff for candidate pairs (default 0.55)")
    ap.add_argument("--heatmap", type=Path, default=DEFAULT_HEATMAP)
    ap.add_argument("--no-llm", action="store_true", help="skip the LLM stage")
    args = ap.parse_args()

    tors, ground_truth = load_tors(args.tors)
    by_name = {t["group_name"]: t for t in tors}
    names = [t["group_name"] for t in tors]

    print(f"Embedding {len(tors)} ToRs with {MODEL_NAME} ...")
    emb = embed([t["embedding_text"] for t in tors])
    sims = cosine_matrix(emb)

    save_heatmap(sims, names, args.heatmap)

    pairs = candidate_pairs(sims, names, args.threshold)
    print(f"\nCandidate pairs at cosine >= {args.threshold}: {len(pairs)}")
    for a, b, score, *_ in pairs:
        print(f"  {score:.3f}  {a}  <->  {b}")

    # Report how the known duplicate pair(s) scored — quick calibration signal.
    if ground_truth:
        print("\nGround-truth duplicate pairs (should sit above the threshold):")
        for ga, gb in ground_truth:
            i, j = names.index(ga), names.index(gb)
            print(f"  {sims[i, j]:.3f}  {ga}  <->  {gb}")

    if args.no_llm or not pairs:
        return

    client = make_llm_client()

    print(f"\nLLM verification ({LLM_MODEL}):")
    for a, b, score, *_ in pairs:
        verdict = verify_pair(client, by_name[a], by_name[b])
        mark = "DUPLICATE" if verdict["is_duplicate"] else "not a duplicate"
        print(f"\n  [{score:.3f}] {a}  <->  {b}")
        print(f"    -> {mark} (confidence: {verdict['confidence']})")
        print(f"    {verdict['reasoning']}")


if __name__ == "__main__":
    main()
