"""ToR submission lifecycle: drafts, the review queue, and approve/reject.

Every function returns a ``(body, status_code)`` tuple so routes stay a thin
mapping layer. Ownership and visibility are enforced *here*, against the
authenticated user — never by the client filtering a broader list.

A draft deliberately writes nothing to the graph: no group, no persons, no
edges. Only ``submit`` and ``approve`` touch ``governance_groups``, and only
they run the full ToR validation, because a partially-filled draft cannot pass
it by definition.
"""

from datetime import datetime, timezone

from app.db_schema import (
    GovernanceGroup,
    GroupStatus,
    Role,
    TorSubmission,
    TorSubmissionStatus,
)
from app.extensions import db
from app.services import tor_service

# A draft is a form, not a blob store. Big enough for any realistic ToR.
_MAX_FORM_BYTES = 256 * 1024

_RESOLVED = (TorSubmissionStatus.APPROVED, TorSubmissionStatus.REJECTED)


def _is_superuser(user) -> bool:
    return user is not None and user.user_role == Role.SUPER_USER


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _owns(user, submission: TorSubmission) -> bool:
    return user is not None and submission.submitted_by_email == user.email


def _visible_to(user, submission: TorSubmission) -> bool:
    """Superusers see everything except other people's drafts."""
    if _owns(user, submission):
        return True
    if not _is_superuser(user):
        return False
    return submission.status != TorSubmissionStatus.DRAFT


def _validate_form_json(payload: dict) -> tuple[dict, int] | None:
    """Shape checks that apply even to a draft. None when acceptable."""
    form = payload.get("form_json_data")
    if not isinstance(form, dict):
        return {
            "error": "Validation failed",
            "details": {"form_json_data": "Must be a JSON object."},
        }, 400

    # Rough size guard — str() is cheap next to serialising properly and only
    # needs to catch the pathological case.
    if len(str(form)) > _MAX_FORM_BYTES:
        return {
            "error": "Validation failed",
            "details": {"form_json_data": "Form data is too large."},
        }, 400
    return None


def list_submissions(user, scope: str | None) -> tuple[dict, int]:
    """Role-scoped submission list. Summaries only — no form JSON."""
    scope = scope or ("pending" if _is_superuser(user) else "mine")

    if scope == "mine":
        query = TorSubmission.query.filter_by(submitted_by_email=user.email)
    elif scope in ("history", "pending"):
        if not _is_superuser(user):
            return {"error": "Insufficient privileges"}, 403
        if scope == "history":
            query = TorSubmission.query.filter(TorSubmission.status.in_(_RESOLVED))
        else:
            query = TorSubmission.query.filter_by(status=TorSubmissionStatus.PENDING_REVIEW)
    else:
        return {
            "error": "Validation failed",
            "details": {"scope": "Must be one of: mine, history, pending."},
        }, 400

    rows = query.order_by(TorSubmission.updated_at.desc()).all()
    return {"submissions": [row.to_summary_dict() for row in rows]}, 200


def create_draft(user, payload: dict) -> tuple[dict, int]:
    error = _validate_form_json(payload)
    if error:
        return error

    form = payload["form_json_data"]
    submission = TorSubmission(
        group_name=(form.get("group_name") or "").strip() or None,
        submitted_by_email=user.email,
        status=TorSubmissionStatus.DRAFT,
        form_json_data=form,
    )
    db.session.add(submission)
    db.session.commit()
    return submission.to_dict(), 201


def get_submission(user, uuid: str) -> tuple[dict, int]:
    submission = TorSubmission.query.filter_by(uuid=uuid).first()
    # 404 rather than 403 for a submission the caller may not see: a 403 would
    # confirm the row exists.
    if submission is None or not _visible_to(user, submission):
        return {"error": "ToR submission not found"}, 404
    return submission.to_dict(), 200


def update_submission(user, uuid: str, payload: dict) -> tuple[dict, int]:
    """Save a draft, or a superuser's edits to a form under review."""
    submission = TorSubmission.query.filter_by(uuid=uuid).first()
    if submission is None or not _visible_to(user, submission):
        return {"error": "ToR submission not found"}, 404

    if submission.status == TorSubmissionStatus.DRAFT:
        if not _owns(user, submission):
            return {"error": "ToR submission not found"}, 404
    elif submission.status == TorSubmissionStatus.PENDING_REVIEW:
        # The submitter cannot edit while it sits with a reviewer — otherwise
        # the form could change under the superuser mid-review.
        if not _is_superuser(user):
            return {"error": "This submission is awaiting review and cannot be edited."}, 409
    else:
        return {"error": "A resolved submission cannot be edited."}, 409

    error = _validate_form_json(payload)
    if error:
        return error

    form = payload["form_json_data"]
    submission.form_json_data = form
    submission.group_name = (form.get("group_name") or "").strip() or None
    db.session.commit()
    return submission.to_dict(), 200


def delete_draft(user, uuid: str) -> tuple[dict, int]:
    submission = TorSubmission.query.filter_by(uuid=uuid).first()
    if submission is None or not _owns(user, submission):
        return {"error": "ToR submission not found"}, 404
    if submission.status != TorSubmissionStatus.DRAFT:
        return {"error": "Only a draft can be deleted."}, 409

    db.session.delete(submission)
    db.session.commit()
    return {"message": "Draft deleted."}, 200


def submit_submission(user, uuid: str) -> tuple[dict, int]:
    """Draft -> live. Staff produce a Proposed group; superusers bypass review."""
    submission = TorSubmission.query.filter_by(uuid=uuid).first()
    if submission is None or not _owns(user, submission):
        return {"error": "ToR submission not found"}, 404
    if submission.status != TorSubmissionStatus.DRAFT:
        return {"error": "Only a draft can be submitted."}, 409

    form = submission.form_json_data or {}
    errors = tor_service.validate_tor_payload(form, allow_group_uuid=submission.group_uuid)
    if errors:
        return {"error": "Validation failed", "details": errors}, 400

    bypasses_review = _is_superuser(user)
    now = _now()

    try:
        group, _ = tor_service.persist_to_graph(
            form,
            group_status=GroupStatus.ACTIVE if bypasses_review else GroupStatus.PROPOSED,
            group_uuid=submission.group_uuid,
        )
        submission.group_uuid = group.uuid
        submission.group_name = group.group_name
        submission.submitted_at = now
        submission.status = (
            TorSubmissionStatus.APPROVED if bypasses_review else TorSubmissionStatus.PENDING_REVIEW
        )
        if bypasses_review:
            submission.reviewed_by = user.email
            submission.reviewed_at = now
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return submission.to_dict(), 200


def approve_submission(user, uuid: str, admin_comment: str | None) -> tuple[dict, int]:
    submission = TorSubmission.query.filter_by(uuid=uuid).first()
    if submission is None:
        return {"error": "ToR submission not found"}, 404
    if submission.status != TorSubmissionStatus.PENDING_REVIEW:
        return {"error": "Only a submission awaiting review can be approved."}, 409

    form = submission.form_json_data or {}
    # The reviewer may have edited the form, so re-validate — exempting the
    # group this submission already owns, which would otherwise fail its own
    # duplicate-name check.
    errors = tor_service.validate_tor_payload(form, allow_group_uuid=submission.group_uuid)
    if errors:
        return {"error": "Validation failed", "details": errors}, 400

    try:
        group, _ = tor_service.persist_to_graph(
            form,
            group_status=GroupStatus.ACTIVE,
            group_uuid=submission.group_uuid,
        )
        submission.group_uuid = group.uuid
        submission.group_name = group.group_name
        submission.status = TorSubmissionStatus.APPROVED
        submission.admin_comment = (admin_comment or "").strip() or None
        submission.reviewed_by = user.email
        submission.reviewed_at = _now()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return submission.to_dict(), 200


def reject_submission(user, uuid: str, admin_comment: str | None) -> tuple[dict, int]:
    """Reject terminally and take the group back out of the graph."""
    submission = TorSubmission.query.filter_by(uuid=uuid).first()
    if submission is None:
        return {"error": "ToR submission not found"}, 404
    if submission.status != TorSubmissionStatus.PENDING_REVIEW:
        return {"error": "Only a submission awaiting review can be rejected."}, 409

    # Required so the submitter is never left without a reason — rejection is
    # terminal, so there is no later opportunity to explain.
    comment = (admin_comment or "").strip()
    if not comment:
        return {
            "error": "Validation failed",
            "details": {"admin_comment": "A reason is required when rejecting."},
        }, 400

    try:
        if submission.group_uuid:
            group = GovernanceGroup.query.filter_by(uuid=submission.group_uuid).first()
            if group is not None and tor_service.remove_group_from_graph(group):
                # The row is gone, so the reference would dangle. The ToR itself
                # survives in form_json_data, which is the record that matters.
                submission.group_uuid = None

        submission.status = TorSubmissionStatus.REJECTED
        submission.admin_comment = comment
        submission.reviewed_by = user.email
        submission.reviewed_at = _now()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return submission.to_dict(), 200
