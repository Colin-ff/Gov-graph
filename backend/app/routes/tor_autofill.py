"""ToR autofill endpoint (T18BBANANA-46).

POST /api/tor/autofill -> extract a partial ToR form from an uploaded document
"""

from flask import request
from flask_restx import Namespace, Resource

from app.auth import require_role
from app.db_schema import Role
from app.services import tor_autofill_service
from app.services.tor_autofill_service import AutofillError

# Generous enough for any realistic ToR document; guards against an
# accidental (or malicious) huge upload reaching the extraction step.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def register(api, M) -> None:
    ns = Namespace(
        "tor-autofill", path="/tor", description="ToR autofill from an uploaded document"
    )

    @ns.route("/autofill")
    class TorAutofill(Resource):
        @ns.doc("autofill_tor")
        @ns.response(200, "Partial ToR form extracted from the document")
        @ns.response(400, "Missing file, unsupported type, or file too large")
        @ns.response(401, "Authentication required")
        @ns.response(502, "The autofill service failed")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def post(self):
            """Extract a sparse, partial ToR form from an uploaded PDF/DOCX.

            The file is parsed in memory and discarded -- nothing is persisted.
            Any field the document doesn't clearly state is omitted, so the
            caller should treat the result exactly like a partial draft (run
            it through the same rehydration used to resume one) rather than a
            validated submission.
            """
            file_storage = request.files.get("file")
            if file_storage is None or not file_storage.filename:
                return {
                    "error": "Validation failed",
                    "details": {"file": "A file is required."},
                }, 400

            ext = file_storage.filename.lower()
            if not ext.endswith((".pdf", ".docx", ".doc")):
                return {
                    "error": "Validation failed",
                    "details": {
                        "file": "Unsupported file type. Please upload a PDF or .docx file."
                    },
                }, 400

            file_storage.stream.seek(0, 2)
            size = file_storage.stream.tell()
            file_storage.stream.seek(0)
            if size > _MAX_UPLOAD_BYTES:
                return {
                    "error": "Validation failed",
                    "details": {"file": "File is too large."},
                }, 400

            try:
                text = tor_autofill_service.extract_text(file_storage)
                form = tor_autofill_service.autofill_from_text(text)
            except AutofillError as exc:
                return {"error": str(exc)}, exc.status

            return {"form_json_data": form}, 200

    api.add_namespace(ns)
