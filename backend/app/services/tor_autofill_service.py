"""ToR autofill: turn an uploaded document into a sparse ToR form draft.

POST /api/tor/autofill extracts text from an uploaded PDF/DOCX ToR document,
then asks Gemini to populate whichever ``tor_form`` fields the text clearly
supports. The result is a **sparse** ``Partial<TorFormPayload>`` -- any field
the document doesn't state is omitted or dropped by ``_postprocess``, never
guessed -- so the frontend can run it through the same ``applyForm()`` used
to resume a draft and get a prefilled-but-still-fully-editable wizard.
Nothing here is persisted or run through the full ToR validation; that only
happens on submit, same as manual entry.
"""

from __future__ import annotations

import io
import json
import re

from docx import Document
from flask import current_app
from google import genai
from google.genai import errors, types
from pypdf import PdfReader

from app.services import type_service

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

# Bounds the text sent to the model -- large documents cost more and add
# nothing past a certain point for a one-page ToR.
_MAX_EXTRACTED_CHARS = 40_000

# Google's maintained alias for its current recommended flash model, rather
# than a version-pinned name -- version-pinned Gemini models get deprecated
# for new API keys over time (e.g. gemini-2.5-flash already has been).
# Overridable via GEMINI_MODEL.
_DEFAULT_MODEL = "gemini-flash-latest"
_ZID_RE = re.compile(r"^\d{7}$")


class AutofillError(Exception):
    """A user-facing autofill failure: bad file, empty text, or an LLM failure.

    ``status`` is the HTTP status the route should return: 400 for a problem
    with the input (bad file, nothing extracted), 502 for a provider/config
    failure that isn't the caller's fault.
    """

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _extension(filename: str) -> str:
    idx = filename.rfind(".")
    return filename[idx:].lower() if idx != -1 else ""


def extract_text(file_storage) -> str:
    """Extract raw text from an uploaded ``.pdf`` or ``.docx`` file.

    Raises ``AutofillError`` with a user-facing message for anything else,
    including a legacy ``.doc`` -- there is no reliable pure-Python parser for
    the old binary Word format.
    """
    filename = file_storage.filename or ""
    ext = _extension(filename)
    data = file_storage.read()

    if ext == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise AutofillError("Could not read that PDF file.") from exc
    elif ext == ".docx":
        try:
            document = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in document.paragraphs)
        except Exception as exc:
            raise AutofillError("Could not read that .docx file.") from exc
    elif ext == ".doc":
        raise AutofillError(
            "Legacy .doc files aren't supported. Please upload a PDF or .docx file."
        )
    else:
        raise AutofillError("Unsupported file type. Please upload a PDF or .docx file.")

    text = text.strip()
    if not text:
        raise AutofillError("No text could be extracted from that file.")
    return text[:_MAX_EXTRACTED_CHARS]


def _response_schema() -> types.Schema:
    member_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "first_name": types.Schema(type=types.Type.STRING),
            "last_name": types.Schema(type=types.Type.STRING),
            "gender": types.Schema(type=types.Type.STRING),
            "email": types.Schema(type=types.Type.STRING),
            "phone": types.Schema(type=types.Type.STRING),
            "zID": types.Schema(type=types.Type.STRING, description="7 digits, no leading 'z'"),
            "roles": types.Schema(
                type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)
            ),
            "is_student": types.Schema(type=types.Type.BOOLEAN),
            "is_faculty": types.Schema(type=types.Type.BOOLEAN),
            "is_external": types.Schema(type=types.Type.BOOLEAN),
        },
    )
    relation_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "group_name": types.Schema(type=types.Type.STRING),
            "note": types.Schema(type=types.Type.STRING),
        },
    )
    reference_link_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title": types.Schema(type=types.Type.STRING),
            "url": types.Schema(type=types.Type.STRING),
        },
    )
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "group_name": types.Schema(type=types.Type.STRING),
            "entity_type": types.Schema(type=types.Type.STRING),
            "purpose": types.Schema(type=types.Type.STRING),
            "responsibilities": types.Schema(type=types.Type.STRING),
            "members": types.Schema(type=types.Type.ARRAY, items=member_schema),
            "relations": types.Schema(type=types.Type.ARRAY, items=relation_schema),
            "meeting_frequency_per_year": types.Schema(type=types.Type.INTEGER),
            "meeting_duration_hour": types.Schema(type=types.Type.NUMBER),
            "reference_links": types.Schema(type=types.Type.ARRAY, items=reference_link_schema),
            "start_date": types.Schema(type=types.Type.STRING, description="YYYY-MM-DD"),
            "review_date": types.Schema(type=types.Type.STRING, description="YYYY-MM-DD"),
        },
    )


def _build_prompt(text: str) -> str:
    entity_types = type_service.list_entity_types().get("entity_types", [])
    member_roles = type_service.list_member_roles().get("member_types", [])

    return (
        "Extract Terms of Reference (ToR) details from the document text below "
        "into the JSON schema you were given. Only fill a field when the text "
        "clearly states it -- omit anything the text does not mention rather "
        "than guessing or inventing a value. Do not include a members, "
        "relations, or reference_links entry that has nothing but empty or "
        "unknown values -- leave the array out (or shorter) instead.\n\n"
        f"Known entity types (prefer one of these for entity_type when it fits): "
        f"{entity_types}\n"
        f"Known member roles (prefer these for each member's roles when they "
        f"fit): {member_roles}\n\n"
        "For each member, set exactly one of is_student / is_faculty / "
        "is_external true when the document indicates it, and leave all three "
        "unset otherwise.\n\n"
        "Document text:\n"
        f"{text}"
    )


def autofill_from_text(text: str) -> dict:
    """Call Gemini with a JSON-mode schema and return a sparse partial ToR dict."""
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise AutofillError("Autofill is not configured on this server.", status=502)

    model = current_app.config.get("GEMINI_MODEL") or _DEFAULT_MODEL
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=_build_prompt(text),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_response_schema(),
            ),
        )
    except errors.APIError as exc:
        raise AutofillError("The autofill service is temporarily unavailable.", status=502) from exc

    if not response.text:
        raise AutofillError("The autofill service returned an unexpected response.", status=502)

    try:
        raw = json.loads(response.text)
    except ValueError as exc:
        raise AutofillError(
            "The autofill service returned an unexpected response.", status=502
        ) from exc

    if not isinstance(raw, dict):
        raise AutofillError("The autofill service returned an unexpected response.", status=502)

    return _postprocess(raw)


def _has_any_value(d: dict) -> bool:
    return any(v not in (None, "", [], False) for v in d.values())


def _postprocess(raw: dict) -> dict:
    """Coerce a couple of fields the LLM can plausibly get wrong shape-wise.

    Not full ToR validation -- this is still a draft the user reviews. Just
    enough to keep obviously-malformed values (a bad zID, an ambiguous
    representation, an all-empty placeholder row) from reaching the wizard as
    if they were confirmed data.
    """
    result = dict(raw)

    members = result.get("members")
    if isinstance(members, list):
        cleaned_members = [
            _postprocess_member(m) for m in members if isinstance(m, dict) and _has_any_value(m)
        ]
        if cleaned_members:
            result["members"] = cleaned_members
        else:
            result.pop("members", None)

    for list_key in ("relations", "reference_links"):
        items = result.get(list_key)
        if isinstance(items, list):
            cleaned = [i for i in items if isinstance(i, dict) and _has_any_value(i)]
            if cleaned:
                result[list_key] = cleaned
            else:
                result.pop(list_key, None)

    return result


def _postprocess_member(member: dict) -> dict:
    cleaned = dict(member)

    zid = cleaned.get("zID")
    if not isinstance(zid, str) or not _ZID_RE.match(zid):
        cleaned.pop("zID", None)

    flags = (cleaned.get("is_student"), cleaned.get("is_faculty"), cleaned.get("is_external"))
    if sum(bool(f) for f in flags) != 1:
        cleaned.pop("is_student", None)
        cleaned.pop("is_faculty", None)
        cleaned.pop("is_external", None)

    return cleaned
