import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiErrorMessages, fetchSubmissions } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { UserRole } from "../auth/role";
import { SubmissionList } from "../components/registry/SubmissionList";
import type { TorSubmissionScope, TorSubmissionSummary } from "../types/governance";

// Superusers split their view in two; a common user gets a single list covering
// every stage of their own ToRs.
const SUPERUSER_TABS: { scope: TorSubmissionScope; label: string; empty: string }[] = [
  { scope: "pending", label: "Pending Review", empty: "Nothing is awaiting review." },
  { scope: "history", label: "ToR History", empty: "No ToRs have been resolved yet." },
];

export default function RegistryPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSuperUser = user?.userRole === UserRole.SuperUser;

  const [tab, setTab] = useState<TorSubmissionScope>("pending");
  const [submissions, setSubmissions] = useState<TorSubmissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);

  // Scope is enforced server-side, so each tab is its own request rather than a
  // client-side filter over one list — a common user cannot fetch the others.
  const scope: TorSubmissionScope = isSuperUser ? tab : "mine";

  const load = useCallback(async () => {
    setLoading(true);
    setErrors([]);
    try {
      setSubmissions(await fetchSubmissions(scope));
    } catch (err) {
      setErrors(apiErrorMessages(err));
      setSubmissions([]);
    } finally {
      setLoading(false);
    }
  }, [scope]);

  useEffect(() => {
    void load();
  }, [load]);

  const emptyMessage = isSuperUser
    ? (SUPERUSER_TABS.find((t) => t.scope === tab)?.empty ?? "Nothing to show.")
    : "You have not started any ToR forms yet.";

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">ToR Registry</h1>
        <button
          onClick={() => navigate("/registry/new")}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
        >
          New Governance Group
        </button>
      </div>

      {isSuperUser && (
        <div className="mb-6 flex gap-6 border-b border-gray-200">
          {SUPERUSER_TABS.map(({ scope: tabScope, label }) => (
            <button
              key={tabScope}
              onClick={() => setTab(tabScope)}
              className={`-mb-px border-b-2 px-1 pb-3 text-sm ${
                tab === tabScope
                  ? "border-blue-600 font-medium text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      <SubmissionList
        submissions={submissions}
        loading={loading}
        errors={errors}
        emptyMessage={emptyMessage}
        // Only an org-wide list needs attribution.
        showSubmitter={isSuperUser}
      />
    </div>
  );
}
