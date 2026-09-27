import json

import pytest

from app.services import duplicate_verification_service
from app.services.duplicate_verification_service import (
    VerificationUnavailable,
    verify_candidates,
)

_CANDIDATES = [
    {"uuid": "uuid-1", "group_name": "Cyber Security Oversight Group", "score": 0.59},
    {"uuid": "uuid-2", "group_name": "Cultural Inclusion Working Group", "score": 0.6},
]


def _with_embedding_text(candidates):
    return [{**c, "embedding_text": f"text for {c['group_name']}"} for c in candidates]


class _FakeResponse:
    def __init__(self, payload):
        self.text = json.dumps(payload) if payload is not None else None


class _FakeModels:
    def __init__(self, payload):
        self._payload = payload

    def generate_content(self, **kwargs):
        return _FakeResponse(self._payload)


class _FakeGenaiClient:
    def __init__(self, payload, **kwargs):
        self.models = _FakeModels(payload)


def _patch_genai(monkeypatch, payload):
    monkeypatch.setattr(
        duplicate_verification_service.genai,
        "Client",
        lambda **kwargs: _FakeGenaiClient(payload),
    )


def test_verify_candidates_returns_empty_list_when_no_candidates(app):
    with app.app_context():
        assert verify_candidates("some text", []) == []


def test_verify_candidates_raises_when_no_api_key(app):
    app.config["GEMINI_API_KEY"] = None
    with app.app_context(), pytest.raises(VerificationUnavailable):
        verify_candidates("some text", _with_embedding_text(_CANDIDATES))


def test_verify_candidates_filters_to_confirmed_uuids(app, monkeypatch):
    app.config["GEMINI_API_KEY"] = "test-key"
    _patch_genai(monkeypatch, {"duplicate_uuids": ["uuid-1"]})

    with app.app_context():
        result = verify_candidates("some text", _with_embedding_text(_CANDIDATES))

    assert [c["uuid"] for c in result] == ["uuid-1"]


def test_verify_candidates_returns_empty_when_none_confirmed(app, monkeypatch):
    app.config["GEMINI_API_KEY"] = "test-key"
    _patch_genai(monkeypatch, {"duplicate_uuids": []})

    with app.app_context():
        result = verify_candidates("some text", _with_embedding_text(_CANDIDATES))

    assert result == []


def test_verify_candidates_raises_on_malformed_response(app, monkeypatch):
    app.config["GEMINI_API_KEY"] = "test-key"
    _patch_genai(monkeypatch, None)

    with app.app_context(), pytest.raises(VerificationUnavailable):
        verify_candidates("some text", _with_embedding_text(_CANDIDATES))
