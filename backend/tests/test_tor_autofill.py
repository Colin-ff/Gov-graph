import io
import json

import pytest
from docx import Document

from app.services import tor_autofill_service
from app.services.tor_autofill_service import AutofillError, extract_text


class _FakeFile:
    """Minimal stand-in for a Werkzeug FileStorage -- just filename + read()."""

    def __init__(self, filename: str, data: bytes):
        self.filename = filename
        self._data = data

    def read(self) -> bytes:
        return self._data


def _docx_bytes(paragraphs: list[str]) -> bytes:
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


# ----- extract_text ---------------------------------------------------------


def test_extract_text_docx_returns_joined_paragraphs():
    data = _docx_bytes(["Academic Board", "Reviews academic policy."])
    text = extract_text(_FakeFile("tor.docx", data))
    assert "Academic Board" in text
    assert "Reviews academic policy." in text


def test_extract_text_rejects_legacy_doc():
    with pytest.raises(AutofillError):
        extract_text(_FakeFile("tor.doc", b"not a real doc"))


def test_extract_text_rejects_unsupported_extension():
    with pytest.raises(AutofillError):
        extract_text(_FakeFile("tor.txt", b"hello"))


def test_extract_text_rejects_empty_docx():
    data = _docx_bytes([])
    with pytest.raises(AutofillError):
        extract_text(_FakeFile("tor.docx", data))


def test_extract_text_wraps_corrupt_pdf():
    with pytest.raises(AutofillError):
        extract_text(_FakeFile("tor.pdf", b"this is not a pdf"))


# ----- autofill_from_text (mocked Gemini client) ----------------------------


class _FakeResponse:
    def __init__(self, payload: dict):
        self.text = json.dumps(payload)


class _FakeModels:
    def __init__(self, payload: dict):
        self._payload = payload

    def generate_content(self, **kwargs):
        return _FakeResponse(self._payload)


class _FakeGenaiClient:
    def __init__(self, payload: dict, **kwargs):
        self.models = _FakeModels(payload)


def _patch_genai(monkeypatch, payload: dict):
    monkeypatch.setattr(
        tor_autofill_service.genai,
        "Client",
        lambda **kwargs: _FakeGenaiClient(payload),
    )


def test_autofill_from_text_returns_only_llm_provided_keys(app, monkeypatch):
    app.config["GEMINI_API_KEY"] = "test-key"
    _patch_genai(monkeypatch, {"group_name": "Academic Board", "purpose": "Set policy."})

    with app.app_context():
        result = tor_autofill_service.autofill_from_text("some document text")

    assert result == {"group_name": "Academic Board", "purpose": "Set policy."}
    # Fields the LLM didn't mention are absent entirely, not blanked -- the
    # frontend's applyForm() supplies the blank defaults for anything missing.
    assert "entity_type" not in result
    assert "members" not in result


def test_autofill_from_text_coerces_bad_zid(app, monkeypatch):
    app.config["GEMINI_API_KEY"] = "test-key"
    _patch_genai(
        monkeypatch,
        {"members": [{"first_name": "Ashley", "zID": "not-7-digits"}]},
    )

    with app.app_context():
        result = tor_autofill_service.autofill_from_text("text")

    assert "zID" not in result["members"][0]
    assert result["members"][0]["first_name"] == "Ashley"


def test_autofill_from_text_drops_ambiguous_representation_flags(app, monkeypatch):
    app.config["GEMINI_API_KEY"] = "test-key"
    _patch_genai(
        monkeypatch,
        {"members": [{"first_name": "Ashley", "is_student": True, "is_faculty": True}]},
    )

    with app.app_context():
        result = tor_autofill_service.autofill_from_text("text")

    member = result["members"][0]
    assert "is_student" not in member
    assert "is_faculty" not in member
    assert "is_external" not in member


def test_autofill_from_text_drops_all_empty_members(app, monkeypatch):
    app.config["GEMINI_API_KEY"] = "test-key"
    _patch_genai(
        monkeypatch,
        {
            "group_name": "Academic Board",
            "members": [{"first_name": "", "last_name": "", "roles": []}],
        },
    )

    with app.app_context():
        result = tor_autofill_service.autofill_from_text("text")

    # A placeholder row Gemini's JSON mode filled with empties shouldn't reach
    # the wizard as if a member was actually found in the document.
    assert "members" not in result
    assert result["group_name"] == "Academic Board"


def test_autofill_from_text_raises_when_no_api_key(app):
    app.config["GEMINI_API_KEY"] = None
    with app.app_context(), pytest.raises(AutofillError):
        tor_autofill_service.autofill_from_text("text")


# ----- POST /api/tor/autofill route -----------------------------------------


def test_autofill_route_requires_auth(client):
    data = {"file": (io.BytesIO(_docx_bytes(["hello"])), "tor.docx")}
    resp = client.post("/api/tor/autofill", data=data, content_type="multipart/form-data")
    assert resp.status_code == 401


def test_autofill_route_requires_file(client, admin_headers):
    resp = client.post("/api/tor/autofill", data={}, headers=admin_headers)
    assert resp.status_code == 400


def test_autofill_route_rejects_legacy_doc(client, admin_headers):
    data = {"file": (io.BytesIO(b"not a real doc"), "tor.doc")}
    resp = client.post(
        "/api/tor/autofill", data=data, headers=admin_headers, content_type="multipart/form-data"
    )
    assert resp.status_code == 400


def test_autofill_route_rejects_oversized_file(client, admin_headers):
    big = io.BytesIO(b"a" * (10 * 1024 * 1024 + 1))
    data = {"file": (big, "tor.docx")}
    resp = client.post(
        "/api/tor/autofill", data=data, headers=admin_headers, content_type="multipart/form-data"
    )
    assert resp.status_code == 400


def test_autofill_route_success(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        tor_autofill_service,
        "autofill_from_text",
        lambda text: {"group_name": "Academic Board"},
    )
    data = {"file": (io.BytesIO(_docx_bytes(["Academic Board ToR"])), "tor.docx")}
    resp = client.post(
        "/api/tor/autofill", data=data, headers=admin_headers, content_type="multipart/form-data"
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json() == {"form_json_data": {"group_name": "Academic Board"}}


def test_autofill_route_returns_502_on_llm_failure(client, admin_headers, monkeypatch):
    def _raise(text):
        raise AutofillError("The autofill service is temporarily unavailable.", status=502)

    monkeypatch.setattr(tor_autofill_service, "autofill_from_text", _raise)
    data = {"file": (io.BytesIO(_docx_bytes(["Academic Board ToR"])), "tor.docx")}
    resp = client.post(
        "/api/tor/autofill", data=data, headers=admin_headers, content_type="multipart/form-data"
    )

    assert resp.status_code == 502
