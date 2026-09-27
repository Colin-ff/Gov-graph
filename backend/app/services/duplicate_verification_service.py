"""LLM verification pass for cosine-similarity duplicate candidates.

Cosine similarity over the distilled purpose/responsibilities/reporting-line
text (see ``app/services/embedding_service.py``) can be fooled by shared
boilerplate governance-committee phrasing even when two groups' actual
remits have nothing to do with each other. This module hands the
score-qualifying candidates to Gemini -- the same provider already used for
ToR autofill -- and asks it to judge, from the text itself, which ones
genuinely describe an overlapping governance body. Candidates it rejects are
dropped before the caller ever sees them.
"""

from __future__ import annotations

import json

from flask import current_app
from google import genai
from google.genai import errors, types

# Same default as tor_autofill_service: Google's maintained alias for its
# current recommended flash model. Overridable via GEMINI_MODEL.
_DEFAULT_MODEL = "gemini-flash-latest"


class VerificationUnavailable(Exception):
    """Gemini isn't configured, or the call failed.

    Callers should catch this and fall back to the unverified candidate
    list -- a missing API key or a flaky provider must never hide a possible
    duplicate the cosine search already found.
    """


def _response_schema() -> types.Schema:
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "duplicate_uuids": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
                description=(
                    "uuids of candidates that genuinely describe the same or "
                    "substantially overlapping governance body as the new group."
                ),
            ),
        },
    )


def _build_prompt(new_text: str, candidates: list[dict]) -> str:
    listed = "\n\n".join(
        f"uuid: {candidate['uuid']}\n"
        f"group_name: {candidate['group_name']}\n"
        f"text: {candidate['embedding_text']}"
        for candidate in candidates
    )
    return (
        "A new governance group's Terms of Reference is being checked against "
        "existing groups that a text-similarity search flagged as possible "
        "duplicates. That similarity score can be inflated by shared "
        "boilerplate committee phrasing (e.g. generic language about "
        "oversight, advice, and accountability) even when the groups cover "
        "unrelated subject matter. Decide which candidates, if any, actually "
        "describe the same or substantially overlapping governance body as "
        "the new group -- judge by their specific subject matter and remit, "
        "not by how similar the generic wording sounds.\n\n"
        f"New group's text:\n{new_text}\n\n"
        f"Candidates:\n{listed}\n\n"
        "Return the uuids of only the candidates that are genuine duplicates. "
        "If none are, return an empty list."
    )


def verify_candidates(new_text: str, candidates: list[dict]) -> list[dict]:
    """Filter ``candidates`` down to the ones Gemini agrees are genuine duplicates.

    Each candidate dict must carry ``uuid``, ``group_name``, and
    ``embedding_text``. Returns the subset of the original candidate dicts
    Gemini confirmed, preserving their original shape and order.

    Raises ``VerificationUnavailable`` if Gemini isn't configured or the call
    fails; it never raises for "no genuine duplicates" -- that's a normal
    empty result.
    """
    if not candidates:
        return []

    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise VerificationUnavailable("Gemini is not configured on this server.")

    model = current_app.config.get("GEMINI_MODEL") or _DEFAULT_MODEL
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=_build_prompt(new_text, candidates),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_response_schema(),
            ),
        )
    except errors.APIError as exc:
        raise VerificationUnavailable(
            "The verification service is temporarily unavailable."
        ) from exc

    if not response.text:
        raise VerificationUnavailable(
            "The verification service returned an unexpected response."
        )

    try:
        raw = json.loads(response.text)
    except ValueError as exc:
        raise VerificationUnavailable(
            "The verification service returned an unexpected response."
        ) from exc

    if not isinstance(raw, dict):
        raise VerificationUnavailable(
            "The verification service returned an unexpected response."
        )

    duplicate_uuids = set(raw.get("duplicate_uuids") or [])
    return [candidate for candidate in candidates if candidate["uuid"] in duplicate_uuids]
