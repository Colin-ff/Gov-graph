import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { GroupPanel } from "../components/GroupPanel";
import { GovernanceGraph } from "../components/GovernanceGraph";
import { PersonPanel } from "../components/PersonPanel";
import { fetchGroup, fetchPerson } from "../api/client";
import { mockGroups } from "../api/mockData";
import type { GovernanceGroup, GraphNode, PersonPublic } from "../types/governance";

export default function VisualisationPage() {
  const [searchParams] = useSearchParams();
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [groupDetail, setGroupDetail] = useState<GovernanceGroup | null>(null);
  const [groupLoading, setGroupLoading] = useState(false);
  const [groupError, setGroupError] = useState("");

  const [personDetail, setPersonDetail] = useState<PersonPublic | null>(null);
  const [personLoading, setPersonLoading] = useState(false);

  function handleNodeClick(nodeId: string, node: GraphNode) {
    setSelectedNode(node);
    setGroupDetail(null);
    setGroupError("");
    setGroupLoading(true);
    setPersonDetail(null);

    fetchGroup(nodeId)
      .then(group => {
        setGroupDetail(group);
        // Deep links only know the uuid — backfill the name once fetched.
        setSelectedNode({ uuid: nodeId, group_name: group.group_name });
      })
      .catch(() => {
        setGroupDetail(mockGroups[nodeId] ?? {
          uuid: node.uuid,
          group_name: node.group_name,
          entity_type: "",
          status: "active",
          purpose: null,
          responsibilities: null,
          meeting_frequency_per_year: null,
          meeting_duration_hour: null,
        });
      })
      .finally(() => setGroupLoading(false));
  }

  function handlePersonClick(personUuid: string, firstName: string, lastName: string) {
    setPersonDetail(null);
    setPersonLoading(true);

    fetchPerson(personUuid)
      .then(person => setPersonDetail(person))
      .catch(() => setPersonDetail({
        uuid: personUuid,
        first_name: firstName,
        last_name: lastName,
        affiliated_groups: [],
      }))
      .finally(() => setPersonLoading(false));
  }

  // Deep links from Analytics: /visualisation?group=<uuid> opens (and auto-centres
  // on) that group's panel; ?person=<uuid> opens that person's detail panel.
  useEffect(() => {
    const groupUuid = searchParams.get("group");
    const personUuid = searchParams.get("person");
    if (personUuid) {
      handlePersonClick(personUuid, "", "");
    } else if (groupUuid) {
      handleNodeClick(groupUuid, { uuid: groupUuid, group_name: "" });
    }
    // Run once on mount — afterwards selection is driven by graph clicks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleClose() {
    setSelectedNode(null);
    setGroupDetail(null);
    setGroupError("");
    setPersonDetail(null);
  }

  const showPerson = personDetail !== null || personLoading;

  return (
    <div className="flex h-[calc(100vh-3.5rem)] border-t border-gray-200 overflow-hidden">
      <GovernanceGraph
        onNodeClick={handleNodeClick}
        selectedNodeId={selectedNode?.uuid ?? null}
      />

      {showPerson && (
        <PersonPanel
          person={personDetail ?? { uuid: "", first_name: "", last_name: "", affiliated_groups: [] }}
          loading={personLoading}
          onClose={handleClose}
          onBack={() => setPersonDetail(null)}
          onGroupSelect={(uuid, groupName) => {
            setPersonDetail(null);
            handleNodeClick(uuid, { uuid, group_name: groupName });
          }}
        />
      )}

      {!showPerson && selectedNode && (
        <GroupPanel
          graphNode={selectedNode}
          group={groupDetail}
          loading={groupLoading}
          error={groupError}
          onClose={handleClose}
          onNodeSelect={(uuid, groupName) => handleNodeClick(uuid, { uuid, group_name: groupName })}
          onPersonSelect={handlePersonClick}
        />
      )}
    </div>
  );
}
