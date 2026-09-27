"""Embedding-based duplicate detection for governance groups.

A governance group is distilled down to the fields that actually distinguish
it from another one - purpose, responsibilities, reporting line, group type -
and only that distilled text is embedded, never the raw form/document text.
Raw-text embedding lets shared boilerplate dominate the vector so every pair
looks similar; see ``similarity_search/README.md`` at the repo root for the
full rationale and how the 0.55 cosine threshold was calibrated.

There is no pgvector/vector index here: at this dataset's scale (tens to a
few hundred groups), a brute-force NumPy cosine scan against every stored
embedding is microseconds, so the comparison happens in plain Python instead
of a database vector type. ``GovernanceGroup.embedding`` is a plain JSON
column of floats for that reason.
"""

from __future__ import annotations

import numpy as np

from app.db_schema import GovernanceGroup
from app.extensions import db

MODEL_NAME = "all-mpnet-base-v2"
DEFAULT_THRESHOLD = 0.55

_model = None


def _get_model():
    """Lazily load and cache the sentence-transformers model.

    The import is deferred so merely importing this module (e.g. at Flask
    app boot) never pulls in torch; the model itself loads once, on first
    actual use, and is reused for the life of the process.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_text(text: str) -> list[float]:
    """Embed one string, L2-normalised so cosine similarity == dot product."""
    vector = _get_model().encode([text], normalize_embeddings=True)[0]
    return vector.tolist()


def build_embedding_text(
    group_type: str, purpose: str, responsibilities: str, reporting_line: str
) -> str:
    """Assemble the distilled text that gets embedded for a group."""
    return (
        f"{group_type}. "
        f"Purpose: {purpose.strip()} "
        f"Responsibilities: {responsibilities.strip()}. "
        f"Reports to: {reporting_line.strip()}."
    )


def derive_reporting_line(relations: list[dict] | None) -> str:
    """Return the name of the group a "Report to" relation points at, if any."""
    for relation in relations or []:
        if str(relation.get("relation_type", "")).strip().lower() != "report to":
            continue
        if relation.get("existing_group"):
            target = GovernanceGroup.query.filter_by(
                uuid=(relation.get("group_uuid") or "").strip()
            ).first()
            return target.group_name if target else ""
        return (relation.get("group_name") or "").strip()
    return ""


def find_similar_groups(
    embedding: list[float],
    threshold: float = DEFAULT_THRESHOLD,
    top_k: int = 5,
    exclude_uuid: str | None = None,
) -> list[dict]:
    """Existing groups whose stored embedding scores >= threshold, highest first.

    ``exclude_uuid`` omits one group from the scan. Callers checking an
    already-registered group's own text against the database (e.g. re-showing
    a duplicate warning for a group that was already saved) must pass that
    group's uuid here, otherwise its stored embedding matches itself with a
    cosine score of ~1.0 every time.
    """
    query = db.session.query(
        GovernanceGroup.uuid, GovernanceGroup.group_name, GovernanceGroup.embedding
    ).filter(GovernanceGroup.embedding.isnot(None))
    if exclude_uuid:
        query = query.filter(GovernanceGroup.uuid != exclude_uuid)
    rows = query.all()
    if not rows:
        return []

    matrix = np.array([row.embedding for row in rows])
    scores = matrix @ np.array(embedding)

    candidates = [
        {"uuid": row.uuid, "group_name": row.group_name, "score": float(score)}
        for row, score in zip(rows, scores, strict=True)
        if score >= threshold
    ]
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:top_k]
