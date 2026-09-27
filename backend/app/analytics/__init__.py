"""Governance analytics computations (burden, concentration, overlap, etc.).

Re-exports the analytics functions consumed by ``app.routes.analytics`` so
callers can ``from app.analytics import <function>`` without reaching into the
``main`` module. Internal helpers (``_find_group_by_uuid`` and friends) stay
private to ``main``.
"""

from app.analytics.main import (
    get_all_multiple_reporting_line_groups,
    get_all_orphan_groups,
    get_chain_of_command,
    get_gender_distribution_of_a_group,
    get_member_representation_of_a_group,
    get_number_of_governance_groups_under_control,
    get_number_of_governance_hours_of_a_group,
    get_number_of_groups_a_person_belongs,
    get_number_of_shared_members_between_two_groups,
    get_percentage_of_membership_overlapping_relevant_to_group_a,
    get_shared_members_between_two_groups,
    get_top_groups_by_governance_hours,
    get_top_groups_by_under_control_count,
    get_top_people_by_group_count,
    get_top_people_by_meeting_hours,
    get_total_meeting_hours_for_a_person,
    group_exists,
    person_exists,
)

__all__ = [
    # general helpers
    "group_exists",
    "person_exists",
    # 1. member's governance burden
    "get_total_meeting_hours_for_a_person",
    "get_top_people_by_meeting_hours",
    "get_top_people_by_group_count",
    "get_number_of_groups_a_person_belongs",
    # 2. group governance concentration
    "get_number_of_governance_groups_under_control",
    "get_number_of_governance_hours_of_a_group",
    "get_top_groups_by_under_control_count",
    "get_top_groups_by_governance_hours",
    # 3. governance structural pitfalls
    "get_all_orphan_groups",
    "get_all_multiple_reporting_line_groups",
    # 4. overlapped duties
    "get_number_of_shared_members_between_two_groups",
    "get_shared_members_between_two_groups",
    "get_percentage_of_membership_overlapping_relevant_to_group_a",
    # 5. diversity analytics
    "get_gender_distribution_of_a_group",
    "get_member_representation_of_a_group",
    # 6. chain of command intelligence
    "get_chain_of_command",
]
