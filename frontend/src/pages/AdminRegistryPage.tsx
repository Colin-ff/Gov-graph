import { useCallback, useEffect, useState } from "react";
import {
  apiErrorMessages,
  approveAdminRegistration,
  fetchAdminRegistrations,
  rejectAdminRegistration,
} from "../api/client";
import type {
  AdminRegistrationRequest,
  AdminRegistrationScope,
} from "../types/governance";

const TABS: { scope: AdminRegistrationScope; label: string; empty: string }[] = [
  { scope: "pending", label: "Pending Review", empty: "No admin registrations awaiting review." },
  { scope: "history", label: "History", empty: "No reviewed admin registrations yet." },
];

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function AdminRegistryPage() {
  const [tab, setTab] = useState<AdminRegistrationScope>("pending");
  const [requests, setRequests] = useState<AdminRegistrationRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);
  const [commentById, setCommentById] = useState<Record<number, string>>({});
  const [actingId, setActingId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErrors([]);
    try {
      setRequests(await fetchAdminRegistrations(tab));
    } catch (err) {
      setErrors(apiErrorMessages(err));
      setRequests([]);
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    void load();
  }, [load]);

  async function approve(id: number) {
    setActingId(id);
    setErrors([]);
    try {
      await approveAdminRegistration(id);
      await load();
    } catch (err) {
      setErrors(apiErrorMessages(err));
    } finally {
      setActingId(null);
    }
  }

  async function reject(id: number) {
    setActingId(id);
    setErrors([]);
    try {
      await rejectAdminRegistration(id, commentById[id] ?? "");
      setCommentById((prev) => ({ ...prev, [id]: "" }));
      await load();
    } catch (err) {
      setErrors(apiErrorMessages(err));
    } finally {
      setActingId(null);
    }
  }

  const empty = TABS.find((item) => item.scope === tab)?.empty ?? "Nothing to show.";

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-gray-900">Admin Registry</h1>

      <div className="mb-6 flex gap-6 border-b border-gray-200">
        {TABS.map(({ scope, label }) => (
          <button
            key={scope}
            onClick={() => setTab(scope)}
            className={`-mb-px border-b-2 px-1 pb-3 text-sm ${
              tab === scope
                ? "border-blue-600 font-medium text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading && <p className="text-sm text-gray-500">Loading…</p>}

      {errors.length > 0 && (
        <ul className="mb-4 list-inside list-disc space-y-1">
          {errors.map((error, index) => (
            <li key={index} className="text-sm text-red-600">
              {error}
            </li>
          ))}
        </ul>
      )}

      {!loading && requests.length === 0 && errors.length === 0 && (
        <p className="text-sm text-gray-500">{empty}</p>
      )}

      {!loading && requests.length > 0 && (
        <div className="space-y-3">
          {requests.map((request) => (
            <div
              key={request.id}
              className="rounded-lg border border-gray-200 bg-white p-6"
            >
              <div className="flex items-start justify-between gap-6">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-900">
                    {request.displayName}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {request.email} · Admin · Requested {formatDate(request.createdAt)}
                  </p>
                  {request.status !== "pending_review" && (
                    <p className="mt-1.5 text-xs text-gray-500">
                      {request.status === "approved" ? "Approved" : "Rejected"}{" "}
                      {formatDate(request.reviewedAt)}
                      {request.reviewedBy && <span> by {request.reviewedBy}</span>}
                    </p>
                  )}
                  {request.adminComment && (
                    <p className="mt-1.5 text-xs text-red-700">{request.adminComment}</p>
                  )}
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
                    request.status === "approved"
                      ? "bg-green-50 text-green-700"
                      : request.status === "rejected"
                        ? "bg-red-50 text-red-700"
                        : "bg-blue-50 text-blue-700"
                  }`}
                >
                  {request.status.replace("_", " ")}
                </span>
              </div>

              {request.status === "pending_review" && (
                <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
                  <input
                    className="min-w-0 flex-1 rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    placeholder="Rejection reason"
                    value={commentById[request.id] ?? ""}
                    onChange={(e) =>
                      setCommentById((prev) => ({ ...prev, [request.id]: e.target.value }))
                    }
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => void approve(request.id)}
                      disabled={actingId === request.id}
                      className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-40"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => void reject(request.id)}
                      disabled={actingId === request.id}
                      className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
