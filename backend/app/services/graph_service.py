"""Service functions for governance graph visualisation.

Builds the ``graph`` DTO (nodes + relations) consumed by ``GET /api/graph``.
"""

from app.db_schema import (
    REPORT_TO_TYPE_NAME,
    GovernanceGroup,
    GroupRelationship,
    GroupType,
    RelationshipType,
)
from app.extensions import db


def get_graph_data() -> dict:
    """Return graph nodes and relations for governance visualisation.

    Every group becomes a node. Nodes carry ``status`` and ``entity_type`` so
    the frontend can distinguish a formally registered group from one that only
    exists because another group's ToR named it as a reporting line (status
    ``Proposed``) — without those fields the two render identically.

    Only ``Report to`` relations are returned. The graph exists to show the flow
    of power, and an edge always reads ``source reports to target``, so the
    target is the governing group.

    Returns:
        A dict with ``nodes`` and ``relations`` lists.
    """
    groups = GovernanceGroup.query.all()
    type_names = {t.id: t.type_name for t in GroupType.query.all()}

    nodes = [
        {
            "uuid": g.uuid,
            "group_name": g.group_name,
            "status": g.status.value.lower(),
            "entity_type": type_names.get(g.group_type_id),
        }
        for g in groups
    ]
    uuid_by_id = {g.id: g.uuid for g in groups}

    relations = []
    rows = (
        db.session.query(GroupRelationship)
        .join(
            RelationshipType,
            RelationshipType.id == GroupRelationship.relationship_type_id,
        )
        .filter(RelationshipType.type_name == REPORT_TO_TYPE_NAME)
        .all()
    )
    for rel in rows:
        source_uuid = uuid_by_id.get(rel.source_group_id)
        target_uuid = uuid_by_id.get(rel.target_group_id)
        if source_uuid is None or target_uuid is None:
            continue
        relations.append(
            {
                "source_uuid": source_uuid,
                "target_uuid": target_uuid,
                "relation_type": REPORT_TO_TYPE_NAME,
                "directed": True,
            }
        )

    return {
        "nodes": nodes,
        "relations": relations,
    }
