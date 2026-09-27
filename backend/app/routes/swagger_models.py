"""flask-restx Swagger model definitions.

Every model mirrors a DTO under ``data_transfer_object_examples/`` — the
``dto_manual.md`` there is the declared source of truth. Keys are snake_case to
match the manual (note the deliberate ``zID`` casing on person fields).

``register_models(api)`` registers all models against the shared ``Api`` and
returns them as a dict so the namespace modules can reference each by key in
``@ns.expect(...)`` / ``@ns.response(...)``.
"""

from flask_restx import fields


def register_models(api) -> dict:
    M: dict = {}

    # ----- shared --------------------------------------------------------
    M["reference_link"] = api.model(
        "ReferenceLink",
        {
            "title": fields.String(required=True, example="ToR"),
            "url": fields.String(
                required=True,
                description="http/https only — re-validated server-side",
                example="https://www.unsw.edu.au/.../terms-of-reference",
            ),
        },
    )

    # ----- ToR form (tor/tor_form.json) ----------------------------------
    M["tor_member"] = api.model(
        "TorMember",
        {
            "uuid": fields.String(
                description="Canonical person id; null when adding a new person",
                example="1f6b9d2c-4a7e-4b3f-9c8d-2e5a1f7b3c6d",
            ),
            "first_name": fields.String(required=True),
            "last_name": fields.String(required=True),
            "gender": fields.String,
            "email": fields.String(required=True, description="Required for everyone"),
            "phone": fields.String,
            "zID": fields.String(description="z+7 digits; null for external members"),
            "roles": fields.List(fields.String, description="One member, many roles"),
            "is_student": fields.Boolean,
            "is_external": fields.Boolean,
        },
    )
    M["tor_relation"] = api.model(
        "TorRelation",
        {
            "relation_type": fields.String(required=True, example="Subgroup"),
            "existing_group": fields.Boolean(
                description="True -> resolve by group_uuid; False -> proposed new group"
            ),
            "group_uuid": fields.String(description="Set when existing_group is true"),
            "group_name": fields.String(description="Set when proposing a new group"),
            "note": fields.String,
            "chair_first_name": fields.String,
            "chair_last_name": fields.String,
            "chair_email": fields.String,
            "secretariat_first_name": fields.String,
            "secretariat_last_name": fields.String,
            "secretariat_email": fields.String,
        },
    )
    M["tor_form"] = api.model(
        "TorForm",
        {
            "group_name": fields.String(required=True),
            "entity_type": fields.String(
                required=True,
                description="Exact value from entity_types (Title Case)",
                example="Working Group",
            ),
            "purpose": fields.String,
            "responsibilities": fields.String,
            "members": fields.List(fields.Nested(M["tor_member"])),
            "relations": fields.List(fields.Nested(M["tor_relation"])),
            "meeting_frequency_per_year": fields.Integer(example=6),
            "meeting_duration_hour": fields.Float(example=2),
            "reference_links": fields.List(fields.Nested(M["reference_link"])),
            "start_date": fields.String(example="2024-06-01"),
            "review_date": fields.String(example="2026-06-01"),
        },
    )

    # ----- ToR submission lifecycle -------------------------------------
    M["tor_submission_summary"] = api.model(
        "TorSubmissionSummary",
        {
            "uuid": fields.String(description="Submission UUID — not the group UUID"),
            "group_uuid": fields.String(
                description="The group this submission produced; null while a draft"
            ),
            "group_name": fields.String,
            "status": fields.String(
                description="draft | pending_review | approved | rejected",
                example="pending_review",
            ),
            "submitted_by_email": fields.String,
            "admin_comment": fields.String(description="Reviewer's note; required on reject"),
            "reviewed_by": fields.String,
            "reviewed_at": fields.String,
            "created_at": fields.String(description="When the draft was first saved"),
            "updated_at": fields.String,
            "submitted_at": fields.String(description="Null while still a draft"),
        },
    )
    M["tor_submission"] = api.inherit(
        "TorSubmission",
        M["tor_submission_summary"],
        {"form_json_data": fields.Nested(M["tor_form"])},
    )
    M["tor_submission_list"] = api.model(
        "TorSubmissionList",
        {"submissions": fields.List(fields.Nested(M["tor_submission_summary"]))},
    )
    M["tor_draft_request"] = api.model(
        "TorDraftRequest",
        {
            "form_json_data": fields.Nested(
                M["tor_form"],
                description="Partially-completed ToR form; not validated until submit",
            )
        },
    )
    M["tor_review_request"] = api.model(
        "TorReviewRequest",
        {
            "admin_comment": fields.String(
                description="Optional on approve, required on reject",
                example="Overlaps the existing Audit Committee.",
            )
        },
    )

    # ----- ToR duplicate pre-check (embedding similarity) ----------------
    M["tor_duplicate_check_request"] = api.model(
        "TorDuplicateCheckRequest",
        {
            "entity_type": fields.String(required=True, example="Working Group"),
            "purpose": fields.String(required=True),
            "responsibilities": fields.String(required=True),
            "relations": fields.List(fields.Nested(M["tor_relation"])),
            "group_uuid": fields.String(
                required=False,
                description=(
                    "Uuid of the group this text belongs to, if it is already "
                    "registered. Excluded from the match scan so the group is "
                    "never flagged as a duplicate of itself."
                ),
            ),
        },
    )
    M["tor_duplicate_candidate"] = api.model(
        "TorDuplicateCandidate",
        {
            "uuid": fields.String,
            "group_name": fields.String,
            "score": fields.Float(description="Cosine similarity, 0-1"),
        },
    )
    M["tor_duplicate_check_response"] = api.model(
        "TorDuplicateCheckResponse",
        {"possible_duplicates": fields.List(fields.Nested(M["tor_duplicate_candidate"]))},
    )

    # ----- graph (visualisation/nodes_edges_visualisation.json) ----------
    M["graph_node"] = api.model(
        "GraphNode",
        {
            "uuid": fields.String,
            "group_name": fields.String,
            "status": fields.String(
                description="Lower-cased status; 'proposed' means named by another "
                "group's ToR but not formally registered yet"
            ),
            "entity_type": fields.String,
        },
    )
    M["graph_relation"] = api.model(
        "GraphRelation",
        {
            "source_uuid": fields.String(description="The subordinate group"),
            "target_uuid": fields.String(description="The governing group"),
            "relation_type": fields.String(description="Always 'Report to'"),
            "directed": fields.Boolean,
        },
    )
    M["graph"] = api.model(
        "Graph",
        {
            "nodes": fields.List(fields.Nested(M["graph_node"])),
            "relations": fields.List(fields.Nested(M["graph_relation"])),
        },
    )

    # ----- organisation (getting_info/organisation.json) -----------------
    M["org_member"] = api.model(
        "OrganisationMember",
        {
            "uuid": fields.String,
            "first_name": fields.String(description="Display snapshot, not identity"),
            "last_name": fields.String,
            "roles": fields.List(fields.String),
        },
    )
    M["org_relation"] = api.model(
        "OrganisationRelation",
        {
            "uuid": fields.String(description="Related group id — resolve by uuid"),
            "group_name": fields.String,
            "relation_type": fields.String(description="Always 'Report to'"),
            "direction": fields.String(
                description="'reports_to' when this group answers to the related "
                "one; 'reported_to_by' for the reverse"
            ),
        },
    )
    M["organisation"] = api.model(
        "Organisation",
        {
            "uuid": fields.String,
            "group_name": fields.String,
            "entity_type": fields.String,
            "status": fields.String(description="Server-controlled enum, e.g. active"),
            "purpose": fields.String,
            "responsibilities": fields.String,
            "can_view_meetings": fields.Boolean(
                description="True for a superuser or a member of this group. The "
                "meeting fields and reference_links are present only when true."
            ),
            "meeting_frequency_per_year": fields.Integer,
            "meeting_duration_hour": fields.Float,
            "membership": fields.List(fields.Nested(M["org_member"])),
            "relations": fields.List(fields.Nested(M["org_relation"])),
            "reference_links": fields.List(fields.Nested(M["reference_link"])),
            "start_date": fields.String,
            "review_date": fields.String,
            "created_timestamp": fields.String,
        },
    )

    # ----- organisation list (getting_info/organisation_list.json) -------
    M["organisation_list_item"] = api.model(
        "OrganisationListItem",
        {
            "uuid": fields.String,
            "group_name": fields.String,
            "status": fields.String(
                description="Lower-cased status; 'proposed' groups may be adopted "
                "by a ToR submission, registered ones may not"
            ),
            "chair": fields.String(description="Chair's full name, or null when unassigned"),
            "secretariat": fields.String(
                description="Secretariat's full name, or null when unassigned"
            ),
        },
    )
    M["organisation_list"] = api.model(
        "OrganisationList",
        {"organisations": fields.List(fields.Nested(M["organisation_list_item"]))},
    )

    # ----- person (getting_info/person_*.json) ---------------------------
    M["affiliated_group"] = api.model(
        "AffiliatedGroup",
        {
            "group_uuid": fields.String,
            "group_name": fields.String,
            "roles": fields.List(fields.String),
        },
    )
    M["person_public"] = api.model(
        "PersonPublicReference",
        {
            "uuid": fields.String,
            "first_name": fields.String,
            "last_name": fields.String,
            "affiliated_groups": fields.List(fields.Nested(M["affiliated_group"])),
        },
    )
    M["person_superuser"] = api.model(
        "PersonDetailsSuperuser",
        {
            "uuid": fields.String,
            "gender": fields.String,
            "is_student": fields.Boolean,
            "is_external": fields.Boolean,
            "is_faculty": fields.Boolean,
            "member_representation": fields.String(
                description="Derived bucket: student, faculty, or external"
            ),
            "first_name": fields.String,
            "last_name": fields.String,
            "email": fields.String,
            "phone": fields.String,
            "zID": fields.String,
            "affiliated_groups": fields.List(fields.Nested(M["affiliated_group"])),
        },
    )

    # ----- person list (getting_info/person_list.json) -------------------
    M["person_list_item"] = api.model(
        "PersonListItem",
        {
            "uuid": fields.String,
            "first_name": fields.String,
            "last_name": fields.String,
            "email": fields.String,
        },
    )
    M["person_list"] = api.model(
        "PersonList",
        {"people": fields.List(fields.Nested(M["person_list_item"]))},
    )

    # ----- type lists (tor/*.json) ---------------------------------------
    M["entity_types_list"] = api.model(
        "EntityTypes",
        {
            "entity_types": fields.List(fields.String),
            # Prescribed (seeded) types, in their curated order; a subset of
            # entity_types, which lists these first then user-added types.
            "prescribed_entity_types": fields.List(fields.String),
        },
    )
    M["member_roles_list"] = api.model("MemberRoles", {"member_types": fields.List(fields.String)})
    M["relation_types_list"] = api.model(
        "GroupRelationTypes", {"relation_types": fields.List(fields.String)}
    )

    # ----- auth (login) --------------------------------------------------
    M["login_request"] = api.model(
        "LoginRequest",
        {
            "email": fields.String(required=True, example="admin@unsw.edu.au"),
            "password": fields.String(required=True),
        },
    )
    M["login_response"] = api.model(
        "LoginResponse",
        {
            "email": fields.String,
            "displayName": fields.String,
            "userRole": fields.String(description="STAFF or SUPER_USER"),
            "token": fields.String(description="Sent back as X-Token on later calls"),
        },
    )
    M["register_request"] = api.model(
        "RegisterRequest",
        {
            "email": fields.String(required=True, example="new.user@unsw.edu.au"),
            "displayName": fields.String(required=True, example="New User"),
            "password": fields.String(required=True),
            "userRole": fields.String(required=True, description="STAFF or SUPER_USER"),
        },
    )
    M["admin_registration_request"] = api.model(
        "AdminRegistrationRequest",
        {
            "id": fields.Integer,
            "email": fields.String,
            "displayName": fields.String,
            "requestedRole": fields.String(description="SUPER_USER"),
            "status": fields.String(description="pending_review | approved | rejected"),
            "adminComment": fields.String,
            "reviewedBy": fields.String,
            "reviewedAt": fields.String,
            "createdAt": fields.String,
            "updatedAt": fields.String,
        },
    )
    M["admin_registration_pending"] = api.model(
        "AdminRegistrationPending",
        {
            "status": fields.String(example="pending_review"),
            "message": fields.String,
            "request": fields.Nested(M["admin_registration_request"]),
        },
    )
    M["admin_registration_list"] = api.model(
        "AdminRegistrationList",
        {"requests": fields.List(fields.Nested(M["admin_registration_request"]))},
    )
    M["admin_registration_review_request"] = api.model(
        "AdminRegistrationReviewRequest",
        {
            "adminComment": fields.String(
                description="Required when rejecting an admin registration",
                example="Please use your UNSW staff email.",
            )
        },
    )

    # ----- analytics -----------------------------------------------------
    M["analytics_person_load"] = api.model(
        "AnalyticsPersonLoad",
        {
            "uuid": fields.String,
            "meeting_hours": fields.Float(description="Yearly governance meeting hours"),
        },
    )
    M["analytics_ranked_person"] = api.model(
        "AnalyticsRankedPerson",
        {
            "uuid": fields.String,
            "name": fields.String,
            "count": fields.Float(description="Ranking metric (e.g. yearly meeting hours)"),
        },
    )
    M["analytics_top_people"] = api.model(
        "AnalyticsTopPeople",
        {"people": fields.List(fields.Nested(M["analytics_ranked_person"]))},
    )
    M["analytics_person_group_count"] = api.model(
        "AnalyticsPersonGroupCount",
        {
            "uuid": fields.String,
            "group_count": fields.Integer(description="Number of groups the person belongs to"),
        },
    )
    M["analytics_governed_count"] = api.model(
        "AnalyticsGovernedCount",
        {
            "uuid": fields.String,
            "governed_group_count": fields.Integer(
                description="Groups that report to / are subgroups of this group"
            ),
        },
    )
    M["analytics_group_hours"] = api.model(
        "AnalyticsGroupHours",
        {
            "uuid": fields.String,
            "governance_hours": fields.Float(description="Yearly meeting hours for this group"),
        },
    )
    M["analytics_group_ref"] = api.model(
        "AnalyticsGroupRef",
        {"uuid": fields.String, "name": fields.String},
    )
    M["analytics_orphan_groups"] = api.model(
        "AnalyticsOrphanGroups",
        {"groups": fields.List(fields.Nested(M["analytics_group_ref"]))},
    )
    M["analytics_ranked_group"] = api.model(
        "AnalyticsRankedGroup",
        {"uuid": fields.String, "name": fields.String, "count": fields.Integer},
    )
    M["analytics_multiple_reporting_groups"] = api.model(
        "AnalyticsMultipleReportingGroups",
        {"groups": fields.List(fields.Nested(M["analytics_ranked_group"]))},
    )
    M["analytics_shared_members"] = api.model(
        "AnalyticsSharedMembers",
        {
            "group_a_uuid": fields.String,
            "group_b_uuid": fields.String,
            "shared_member_count": fields.Integer,
        },
    )
    M["analytics_overlap_percentage"] = api.model(
        "AnalyticsOverlapPercentage",
        {
            "group_a_uuid": fields.String,
            "group_b_uuid": fields.String,
            "shared_member_count": fields.Integer,
            "overlap_percentage": fields.Float(
                description="Share of the latter group's (group_b) members also in group_a"
            ),
            "relative_to": fields.String(
                description="Which group is the denominator", example="group_b"
            ),
            "description": fields.String(description="Human-readable phrasing of the overlap"),
        },
    )
    M["analytics_gender_distribution"] = api.model(
        "AnalyticsGenderDistribution",
        {
            "uuid": fields.String,
            "distribution": fields.Raw(description="Map of gender label -> percentage"),
        },
    )
    M["analytics_member_representation_split"] = api.model(
        "AnalyticsMemberRepresentationSplit",
        {
            "student": fields.Float,
            "faculty": fields.Float,
            "external": fields.Float,
        },
    )
    M["analytics_member_representation"] = api.model(
        "AnalyticsMemberRepresentation",
        {
            "uuid": fields.String,
            "representation": fields.Nested(
                M["analytics_member_representation_split"],
                description="Percentage split; empty object for an empty group",
            ),
        },
    )
    M["analytics_chain_of_command"] = api.model(
        "AnalyticsChainOfCommand",
        {
            "from_uuid": fields.String,
            "to_uuid": fields.String,
            "connected": fields.Boolean(description="False when no reporting line links the two"),
            "chain": fields.List(
                fields.String,
                description="Group uuids ordered most-powerful first, or null when unconnected",
            ),
        },
    )
    M["analytics_top_groups"] = api.model(
        "AnalyticsTopGroups",
        {"groups": fields.List(fields.Nested(M["analytics_ranked_group"]))},
    )
    M["analytics_shared_member"] = api.model(
        "AnalyticsSharedMember",
        {
            "uuid": fields.String,
            "first_name": fields.String,
            "last_name": fields.String,
        },
    )
    M["analytics_shared_member_list"] = api.model(
        "AnalyticsSharedMemberList",
        {
            "group_a_uuid": fields.String,
            "group_b_uuid": fields.String,
            "shared_member_count": fields.Integer,
            "shared_members": fields.List(fields.Nested(M["analytics_shared_member"])),
        },
    )

    return M
