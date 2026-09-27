"""ToR form services.

``get_tor_form`` reads the stored ToR form JSON from ``tor_submissions``.
``submit_tor_form`` validates a submitted ToR form and persists it to the graph
(group + members + relationships + reference links) inside one transaction,
alongside the ``tor_submissions`` row that records its place in the review
lifecycle.

``persist_to_graph`` holds the write itself and deliberately does not commit,
so the three flows that need it — a staff submission (group ``Proposed``), a
superuser submission (group ``Active``, review bypassed) and the approval of a
pending submission — can each write their submission row in the same
transaction.
"""

import re
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from app.db_schema import (
    REPORT_TO_TYPE_NAME,
    GovernanceGroup,
    GroupReferenceLink,
    GroupRelationship,
    GroupStatus,
    Membership,
    MembershipRole,
    Person,
    Role,
    TorSubmission,
    TorSubmissionStatus,
)
from app.extensions import db
from app.services import duplicate_verification_service, embedding_service, type_service

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ZID_RE = re.compile(r"^z\d{7}$")

# An explicit hierarchical scheme, e.g. "https://".
_URL_HIERARCHICAL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")

# An opaque scheme with no "//" authority — "javascript:alert(1)", "data:...",
# "mailto:...". These must be left untouched so the scheme allowlist can reject
# them; prepending "https://" would launder a javascript: payload into a URL
# that validates. The negative lookahead excludes "example.com:8080/x", where
# the colon introduces a port rather than a scheme.
_URL_OPAQUE_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:(?!\d)")

_REQUIRED_GROUP_FIELDS = ("group_name", "entity_type", "purpose", "responsibilities")

# The three mutually exclusive sources a member can be drawn from. Exactly one
# must be true; the analytics diversity tab buckets on these.
_REPRESENTATION_FLAGS = ("is_student", "is_faculty", "is_external")


def get_tor_form(uuid: str) -> dict | None:
    """Return the stored ``tor_form`` JSON for a group UUID or submission UUID.

    Callers hold a *group* uuid (this is the "edit the ToR behind this group"
    lookup), but the same value may also be a submission uuid, so both are
    tried. Group lookups take the most recent approved submission: a group may
    have several submissions against it over time and the approved one is the
    form that describes the group as it currently stands.
    """
    submission = (
        TorSubmission.query.filter_by(group_uuid=uuid, status=TorSubmissionStatus.APPROVED)
        .order_by(TorSubmission.reviewed_at.desc())
        .first()
    )
    if submission is None:
        submission = TorSubmission.query.filter_by(uuid=uuid).first()
    if submission is None:
        return None

    return submission.form_json_data


def _is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _title_case(value: str) -> str:
    """Capitalise each word's first letter, leaving the rest untouched.

    Plain ``str.title()`` lower-cases the remainder of every word, which
    mangles acronyms (``"UNSW"`` -> ``"Unsw"``). This only upper-cases the
    first character, so existing internal capitalisation survives.
    """
    return " ".join(word[:1].upper() + word[1:] for word in value.split())


def _has_role(members: list[dict], role_name: str) -> bool:
    return any(
        role_name.lower() in (str(r).lower() for r in member.get("roles", []))
        for member in members
        if isinstance(member.get("roles"), list)
    )


def _resolve_existing_person(member: dict) -> Person | None:
    """The person this entry already refers to, or None for a new person.

    Only ``uuid`` counts here. zID and email also match at write time, but those
    are values the submitter typed, so they still have to be validated; a uuid
    comes from the picker and identifies a record that already exists.
    """
    person_uuid = member.get("uuid")
    if not person_uuid:
        return None
    return Person.query.filter_by(uuid=str(person_uuid).strip()).first()


def _validate_member(member: dict, index: int, errors: dict) -> None:
    prefix = f"members[{index}]"

    roles = member.get("roles")
    if not isinstance(roles, list) or not roles or any(_is_blank(r) for r in roles):
        errors[f"{prefix}.roles"] = "Must be a non-empty list of role names."

    # A member who resolves to an existing person contributes only their roles.
    # ``_match_or_create_person`` keeps the stored record and discards every
    # other field, so requiring them would make the submitter retype details
    # that are then thrown away — and would let contradictory values through
    # unchallenged.
    if _resolve_existing_person(member) is not None:
        return

    if _is_blank(member.get("first_name")):
        errors[f"{prefix}.first_name"] = "Required."
    if _is_blank(member.get("last_name")):
        errors[f"{prefix}.last_name"] = "Required."

    email = member.get("email")
    if _is_blank(email):
        errors[f"{prefix}.email"] = "Required."
    elif not _EMAIL_RE.match(email.strip()):
        errors[f"{prefix}.email"] = "Must be a valid email address."

    if _is_blank(member.get("gender")):
        errors[f"{prefix}.gender"] = "Required."

    # Exactly one representation flag — the buckets are mutually exclusive and
    # collectively exhaustive, so neither zero nor two is a meaningful answer.
    selected = [flag for flag in _REPRESENTATION_FLAGS if member.get(flag)]
    if len(selected) != 1:
        errors[f"{prefix}.member_representation"] = (
            "Exactly one of is_student, is_faculty, or is_external must be true."
        )

    if not member.get("is_external"):
        zid = member.get("zID")
        if _is_blank(zid):
            errors[f"{prefix}.zID"] = "Required for internal (non-external) members."
        elif not _ZID_RE.match(str(zid).strip()):
            errors[f"{prefix}.zID"] = "Must match the format z followed by 7 digits."


def _validate_relation(relation: dict, index: int, errors: dict) -> None:
    """Validate one reporting line.

    ``relation_type`` is no longer read from the payload: every relation the ToR
    form creates is a ``Report to``. A relation either points at an existing
    group by uuid, or names a group that is not registered yet — in which case
    only the name is needed. Earlier sprints also demanded chair and secretariat
    contact details for a proposed target, which is a lot of friction for a group
    you are merely naming as your reporting line.
    """
    prefix = f"relations[{index}]"

    if relation.get("existing_group"):
        group_uuid = relation.get("group_uuid")
        if _is_blank(group_uuid):
            errors[f"{prefix}.group_uuid"] = "Required when existing_group is true."
        elif _find_group_by_uuid(group_uuid) is None:
            errors[f"{prefix}.group_uuid"] = "No governance group exists with this uuid."
    elif _is_blank(relation.get("group_name")):
        errors[f"{prefix}.group_name"] = "Required when naming an unregistered group."


def normalise_url(url: str) -> str:
    """Return ``url`` with an explicit scheme, defaulting to ``https://``.

    Non-technical submitters type "www.unsw.edu.au/tor", not
    "https://www.unsw.edu.au/tor". Rejecting that is needless friction, so a
    missing scheme is filled in rather than refused. An explicit scheme is left
    alone so ``_validate_reference_link`` can still reject ``javascript:`` and
    friends.
    """
    cleaned = url.strip()
    if not cleaned:
        return cleaned
    if _URL_HIERARCHICAL_SCHEME_RE.match(cleaned) or _URL_OPAQUE_SCHEME_RE.match(cleaned):
        return cleaned
    return f"https://{cleaned}"


def _validate_reference_link(link: dict, index: int, errors: dict) -> None:
    prefix = f"reference_links[{index}]"

    if _is_blank(link.get("title")):
        errors[f"{prefix}.title"] = "Required."

    url = link.get("url")
    if _is_blank(url):
        errors[f"{prefix}.url"] = "Required."
    elif urlparse(normalise_url(url)).scheme.lower() not in ("http", "https"):
        errors[f"{prefix}.url"] = "Must be an http:// or https:// URL."


def _parse_date(payload: dict, field: str, errors: dict) -> date | None:
    """Require ``field`` and return it parsed, recording an error if unusable."""
    value = payload.get(field)
    if _is_blank(value):
        errors[field] = "Required."
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        errors[field] = "Must be a date in YYYY-MM-DD format."
        return None


def _validate_validity_period(payload: dict, errors: dict) -> None:
    """The group's validity window must be a real, non-empty span.

    A past start date is fine — groups that have been running for years still
    need registering. What is not fine is an end date that lands on or before
    the start.
    """
    start = _parse_date(payload, "start_date", errors)
    end = _parse_date(payload, "review_date", errors)

    if start is not None and end is not None and start >= end:
        errors["review_date"] = "Must be later than the start date."


def _find_group_by_name(group_name: str) -> GovernanceGroup | None:
    """Resolve a group by name, case-insensitively.

    Names are the only handle a submitter has on a group they did not create,
    so matching has to survive "audit committee" vs "Audit Committee".
    """
    cleaned = group_name.strip()
    if not cleaned:
        return None
    return GovernanceGroup.query.filter(
        db.func.lower(GovernanceGroup.group_name) == cleaned.lower()
    ).first()


def _pending_submission_for_group(group_uuid: str) -> TorSubmission | None:
    """The in-review submission for a group, if one exists.

    ``Proposed`` now has two very different meanings: an empty stub minted by
    ``_resolve_target_group`` when someone named an unregistered group as their
    reporting line, and a fully-populated group whose ToR is awaiting review.
    Only the second must block adoption, so this checks for a submission row
    rather than reading the group's status — a bare status check would break
    the legitimate stub-adoption path.
    """
    return TorSubmission.query.filter_by(
        group_uuid=group_uuid, status=TorSubmissionStatus.PENDING_REVIEW
    ).first()


def validate_tor_payload(payload: dict, *, allow_group_uuid: str | None = None) -> dict[str, str]:
    """Validate a ToR form submission.

    Returns a dict mapping field path -> error message; empty if valid.

    ``allow_group_uuid`` exempts one group from the name-collision rule: the
    group this payload already owns. Approving a pending submission re-runs this
    validation against a group the submission itself created, so without the
    exemption a form would block itself the moment its group stopped being
    ``Proposed``.
    """
    errors: dict[str, str] = {}

    for field in _REQUIRED_GROUP_FIELDS:
        if _is_blank(payload.get(field)):
            errors[field] = "Required."

    # A name already held by a *registered* group is a hard stop — two live
    # groups with one name make the registry unusable. A name held by a
    # ``Proposed`` group is the opposite: someone named this group as their
    # reporting line and it is now being registered for real, so the submission
    # adopts that row (see ``_resolve_target_group``).
    if not _is_blank(payload.get("group_name")):
        existing = _find_group_by_name(payload["group_name"])
        if existing is not None and existing.uuid != allow_group_uuid:
            if existing.status != GroupStatus.PROPOSED:
                errors["group_name"] = "A group with this name is already registered."
            elif _pending_submission_for_group(existing.uuid) is not None:
                # The group is Proposed because someone has a ToR for it under
                # review — not because it is an empty stub. Adopting it here
                # would overwrite their pending submission's members.
                errors["group_name"] = "A ToR for this group is already awaiting review."

    members = payload.get("members")
    if not isinstance(members, list) or not members:
        errors["members"] = "At least one member is required."
    else:
        for i, member in enumerate(members):
            _validate_member(member, i, errors)

        missing_roles = [role for role in ("Chair", "Secretariat") if not _has_role(members, role)]
        if missing_roles:
            errors["members"] = (
                f"At least one member must hold each of: {', '.join(missing_roles)}."
            )

    relations = payload.get("relations")
    if relations is not None:
        if not isinstance(relations, list):
            errors["relations"] = "Must be a list."
        else:
            for i, relation in enumerate(relations):
                _validate_relation(relation, i, errors)

    reference_links = payload.get("reference_links")
    if reference_links is not None:
        if not isinstance(reference_links, list):
            errors["reference_links"] = "Must be a list."
        else:
            for i, link in enumerate(reference_links):
                _validate_reference_link(link, i, errors)

    _validate_validity_period(payload, errors)

    freq = payload.get("meeting_frequency_per_year")
    if freq is not None and not isinstance(freq, int):
        errors["meeting_frequency_per_year"] = "Must be a whole number."

    return errors


def _find_group_by_uuid(group_uuid: str) -> GovernanceGroup | None:
    return GovernanceGroup.query.filter_by(uuid=group_uuid.strip()).first()


def _match_or_create_person(details: dict) -> Person:
    """Resolve a person by uuid -> zID -> email, creating a new record only
    if none of those match an existing person (per the DTO manual's identity rules).
    """
    person = None

    person_uuid = details.get("uuid")
    if person_uuid:
        person = Person.query.filter_by(uuid=person_uuid).first()

    zid = details.get("zID")
    if person is None and zid:
        person = Person.query.filter_by(z_id=zid.strip()).first()

    # Email is only guaranteed for a member the submitter typed in full; one
    # resolved from the picker returns above and may carry no contact fields.
    email = details.get("email")
    if person is None and email:
        person = Person.query.filter_by(email=email.strip().lower()).first()

    if person is None:
        person = Person(
            first_name=details["first_name"].strip(),
            last_name=details["last_name"].strip(),
            gender=details.get("gender") or None,
            email=details["email"].strip().lower(),
            phone=details.get("phone") or None,
            z_id=zid.strip() if zid else None,
            is_student=bool(details.get("is_student", False)),
            is_external=bool(details.get("is_external", False)),
            is_faculty=bool(details.get("is_faculty", False)),
        )
        db.session.add(person)
        db.session.flush()

    return person


def _add_membership(group: GovernanceGroup, person: Person, role_names: list[str]) -> None:
    """Attach one person to one group with all of their roles.

    Exactly one ``Membership`` row per person per group — a person who is both
    Chair and Secretariat holds two roles on a single membership, not two
    memberships, which would double-count them in every analytics query.
    """
    membership = Membership(group_id=group.id, person_id=person.id)
    db.session.add(membership)
    db.session.flush()

    seen: set[int] = set()
    for role_name in role_names:
        role_type_id = type_service.get_or_create_member_role_type(_title_case(str(role_name)))
        if role_type_id in seen:
            continue
        seen.add(role_type_id)
        db.session.add(MembershipRole(membership_id=membership.id, role_type_id=role_type_id))


def _clear_memberships(group: GovernanceGroup) -> None:
    """Remove every membership on a group, roles first (no cascade is declared)."""
    memberships = Membership.query.filter_by(group_id=group.id).all()
    for membership in memberships:
        MembershipRole.query.filter_by(membership_id=membership.id).delete()
        db.session.delete(membership)
    db.session.flush()


def _add_members(group: GovernanceGroup, members: list[dict]) -> None:
    """Persist every submitted member, collapsing repeats of the same person.

    The form may send one person several times — once per position they hold.
    Resolving each to a ``Person`` first and unioning their roles means the
    "chair and secretariat are the same person" case produces one membership
    carrying both roles.
    """
    roles_by_person: dict[int, list[str]] = {}
    people: dict[int, Person] = {}

    for member in members:
        person = _match_or_create_person(member)
        people.setdefault(person.id, person)
        existing = roles_by_person.setdefault(person.id, [])
        for role in member["roles"]:
            if role not in existing:
                existing.append(role)

    for person_id, roles in roles_by_person.items():
        _add_membership(group, people[person_id], roles)


def _resolve_target_group(group: GovernanceGroup, relation: dict) -> GovernanceGroup:
    """Return the group this reporting line points at, creating it if needed.

    A target named by free text is matched against existing groups by name
    before anything is created. Without that, two ToR forms naming the same
    parent would mint two ``Proposed`` rows and the graph would show the same
    body twice with one reporting line each.
    """
    if relation.get("existing_group"):
        return _find_group_by_uuid(relation["group_uuid"])

    name = relation["group_name"].strip()
    existing = _find_group_by_name(name)
    if existing is not None:
        return existing

    # Not registered anywhere yet: record it as Proposed so it appears in the
    # graph as a known-but-unregistered body. It inherits the submitting group's
    # type because the form collects nothing else about it.
    target = GovernanceGroup(
        group_name=_title_case(name),
        group_type_id=group.group_type_id,
        status=GroupStatus.PROPOSED,
    )
    db.session.add(target)
    db.session.flush()
    return target


def _add_relation(group: GovernanceGroup, relation: dict) -> None:
    """Record ``group`` reporting to the relation's target.

    The edge always reads source-reports-to-target, so ``group`` is the
    subordinate. A group may declare several of these.
    """
    target = _resolve_target_group(group, relation)
    if target is None or target.id == group.id:
        # A group reporting to itself is meaningless and would render as a
        # self-loop in the graph.
        return

    already_linked = GroupRelationship.query.filter_by(
        source_group_id=group.id,
        target_group_id=target.id,
    ).first()
    if already_linked is not None:
        return

    db.session.add(
        GroupRelationship(
            source_group_id=group.id,
            target_group_id=target.id,
            relationship_type_id=type_service.get_or_create_relation_type(REPORT_TO_TYPE_NAME),
            description=relation.get("note") or None,
        )
    )


def _add_reference_link(group: GovernanceGroup, link: dict) -> None:
    db.session.add(
        GroupReferenceLink(
            group_id=group.id,
            title=link["title"].strip(),
            url=normalise_url(link["url"]),
        )
    )


def _embed_payload(payload: dict) -> tuple[str, list[float]]:
    """Distill a ToR payload into its embedding text and vector.

    Shared by every path that needs a group's embedding — persisting it,
    checking a draft against existing groups, or checking a submission
    against existing groups before it becomes one of them.
    """
    entity_type_name = _title_case(payload["entity_type"].strip())
    reporting_line = embedding_service.derive_reporting_line(payload.get("relations"))
    embedding_text = embedding_service.build_embedding_text(
        entity_type_name,
        payload["purpose"].strip(),
        payload["responsibilities"].strip(),
        reporting_line,
    )
    return embedding_text, embedding_service.embed_text(embedding_text)


def persist_to_graph(
    payload: dict,
    *,
    group_status: GroupStatus,
    group_uuid: str | None = None,
) -> tuple[GovernanceGroup, bool]:
    """Write a validated ToR form to the graph. Returns ``(group, adopted)``.

    Deliberately does **not** commit. The caller owns the transaction because
    every flow that calls this also writes a ``tor_submissions`` row, and the
    two must land together or not at all.

    ``group_uuid`` pins the target group when the caller already knows it —
    approving a pending submission must update the exact row that submission
    created, not re-resolve by name and risk hitting a different one.
    """
    group_type_id = type_service.get_or_create_group_type(
        _title_case(payload["entity_type"].strip())
    )
    group_name = _title_case(payload["group_name"].strip())

    # If another group's ToR already named this one as its reporting line, or a
    # previous stage of this submission created it, a row already exists. Fill
    # it in rather than inserting a second row: that keeps its uuid and,
    # crucially, the reporting lines already pointing at it — a fresh row would
    # silently orphan them.
    group = _find_group_by_uuid(group_uuid) if group_uuid else None
    if group is None:
        group = _find_group_by_name(group_name)
    adopted = group is not None

    if group is None:
        group = GovernanceGroup(group_name=group_name)
        db.session.add(group)

    group.group_name = group_name
    group.group_type_id = group_type_id
    group.status = group_status
    group.purpose = payload["purpose"].strip()
    group.responsibilities = payload["responsibilities"].strip()
    group.meeting_frequency_per_year = payload.get("meeting_frequency_per_year")
    group.meeting_duration_hour = payload.get("meeting_duration_hour")
    group.start_date = date.fromisoformat(payload["start_date"])
    group.review_date = date.fromisoformat(payload["review_date"])
    group.embedding_text, group.embedding = _embed_payload(payload)
    db.session.flush()

    if adopted:
        # The ToR is now the authority on who sits on this group, so drop any
        # placeholder membership the existing row was carrying instead of
        # stacking the real members on top of it.
        _clear_memberships(group)

    _add_members(group, payload["members"])

    for relation in payload.get("relations") or []:
        _add_relation(group, relation)

    for link in payload.get("reference_links") or []:
        _add_reference_link(group, link)

    return group, adopted


def remove_group_from_graph(group: GovernanceGroup) -> bool:
    """Take a rejected submission's group out of the visualisation.

    Returns True if the row was deleted outright, False if it was stripped back
    to a stub. Like ``persist_to_graph``, this does not commit.

    A rejected ToR must leave nothing behind in the graph, and its name must be
    free for a fresh registration. Normally that means deleting the row. But if
    another group has drawn a reporting line *to* this one, that edge is their
    declaration and not this submission's to destroy — so the row is stripped
    back to the bare ``Proposed`` stub it would have been had this ToR never
    been submitted. Either way the name stays adoptable.
    """
    inbound = GroupRelationship.query.filter_by(target_group_id=group.id).count()

    _clear_memberships(group)
    GroupReferenceLink.query.filter_by(group_id=group.id).delete()
    # Outbound reporting lines were declared by *this* ToR, so they go with it.
    GroupRelationship.query.filter_by(source_group_id=group.id).delete()
    db.session.flush()

    if inbound == 0:
        db.session.delete(group)
        return True

    group.status = GroupStatus.PROPOSED
    group.purpose = None
    group.responsibilities = None
    group.meeting_frequency_per_year = None
    group.meeting_duration_hour = None
    group.start_date = None
    group.review_date = None
    return False


def _is_superuser(user) -> bool:
    """Whether this caller's submissions bypass review.

    Deliberately reads the role off the passed user rather than importing
    ``app.auth``: that module reaches into the Flask request, and the service
    layer stays callable without one.
    """
    return user is not None and user.user_role == Role.SUPER_USER


_CHECK_DUPLICATES_FIELDS = ("entity_type", "purpose", "responsibilities")


def _fetch_embedding_texts(uuids: list[str]) -> dict[str, str]:
    if not uuids:
        return {}
    rows = (
        db.session.query(GovernanceGroup.uuid, GovernanceGroup.embedding_text)
        .filter(GovernanceGroup.uuid.in_(uuids))
        .all()
    )
    return {row.uuid: row.embedding_text for row in rows}


def _verify_duplicates(embedding_text: str, candidates: list[dict]) -> list[dict]:
    """Ask Gemini to confirm which cosine-similarity candidates are genuine.

    Falls back to the unverified candidate list -- unchanged -- if Gemini
    isn't configured or the call fails, so a missing key or a provider outage
    never hides a possible duplicate the cosine search already found.
    """
    if not candidates:
        return candidates

    texts_by_uuid = _fetch_embedding_texts([candidate["uuid"] for candidate in candidates])
    enriched = [
        {**candidate, "embedding_text": texts_by_uuid.get(candidate["uuid"], "")}
        for candidate in candidates
    ]

    try:
        verified = duplicate_verification_service.verify_candidates(embedding_text, enriched)
    except duplicate_verification_service.VerificationUnavailable:
        return candidates

    verified_uuids = {candidate["uuid"] for candidate in verified}
    return [candidate for candidate in candidates if candidate["uuid"] in verified_uuids]


def check_duplicates(payload: dict) -> tuple[dict, int]:
    """Embed a ToR and return existing groups it resembles.

    Read-only: nothing is persisted. Lets the frontend warn the user before a
    real ``POST /api/tor`` submission creates the group, and also lets the
    registry re-check an already-registered group's own text. ``group_uuid``,
    when present, is that group's own uuid and is excluded from the match
    scan so a group is never flagged as a duplicate of itself.

    Candidates that clear the cosine-similarity threshold get one more pass:
    Gemini checks their actual text against the new group's and filters out
    matches that only share generic committee boilerplate (see
    ``duplicate_verification_service``).
    """
    errors = {
        field: "Required." for field in _CHECK_DUPLICATES_FIELDS if _is_blank(payload.get(field))
    }
    if errors:
        return {"error": "Validation failed", "details": errors}, 400

    embedding_text, embedding = _embed_payload(payload)
    exclude_uuid = payload.get("group_uuid") or None
    possible_duplicates = embedding_service.find_similar_groups(
        embedding, exclude_uuid=exclude_uuid
    )
    possible_duplicates = _verify_duplicates(embedding_text, possible_duplicates)
    return {"possible_duplicates": possible_duplicates}, 200


def submit_tor_form(payload: dict, user=None) -> tuple[dict, int]:
    """Validate and persist a ToR form submission.

    Returns a (response_body, status_code) tuple so the route layer can
    return it directly. Everything below the validation check happens in a
    single transaction: any failure rolls back the whole submission rather
    than leaving a half-created group behind — including the submission row,
    so the registry can never show a pending form whose group was never
    written.

    A superuser bypasses review: their group goes straight to ``Active`` and
    the submission is recorded as already approved, so it still appears in ToR
    History and its form JSON stays retrievable. Everyone else creates a
    ``Proposed`` group awaiting a superuser's approval.
    """
    errors = validate_tor_payload(payload)
    if errors:
        return {"error": "Validation failed", "details": errors}, 400

    bypasses_review = _is_superuser(user)
    now = datetime.now(timezone.utc)

    # Computed against the graph as it stands before this submission writes
    # anything, so a group never shows up as a duplicate of itself.
    embedding_text, embedding = _embed_payload(payload)
    possible_duplicates = embedding_service.find_similar_groups(embedding)
    possible_duplicates = _verify_duplicates(embedding_text, possible_duplicates)

    try:
        group, adopted = persist_to_graph(
            payload,
            group_status=GroupStatus.ACTIVE if bypasses_review else GroupStatus.PROPOSED,
        )

        submission = TorSubmission(
            group_uuid=group.uuid,
            group_name=group.group_name,
            submitted_by_email=getattr(user, "email", None),
            status=(
                TorSubmissionStatus.APPROVED
                if bypasses_review
                else TorSubmissionStatus.PENDING_REVIEW
            ),
            form_json_data=payload,
            submitted_at=now,
            reviewed_by=getattr(user, "email", None) if bypasses_review else None,
            reviewed_at=now if bypasses_review else None,
        )
        db.session.add(submission)
        # The submission uuid is a Python-side column default, so it is not
        # populated until the row is flushed.
        db.session.flush()

        group_uuid = group.uuid
        submission_uuid = submission.uuid
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    if bypasses_review:
        message = "Group registered successfully." if adopted else "Group created successfully."
    else:
        message = "ToR submitted for review."

    return {
        "message": message,
        "uuid": group_uuid,
        "submission_uuid": submission_uuid,
        "possible_duplicates": possible_duplicates,
    }, 201
