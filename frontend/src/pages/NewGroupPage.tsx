import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  apiErrorMessages,
  approveSubmission,
  createDraft,
  createGroup,
  fetchSubmission,
  rejectSubmission,
  submitDraft,
  updateDraft,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { UserRole } from "../auth/role";
import { StepProgress } from "../components/new-group/StepProgress";
import { StepNav } from "../components/new-group/StepNav";
import type { WizardMode } from "../components/new-group/StepNav";
import { Modal } from "../components/ui/Modal";
import { StepInfo } from "../components/new-group/StepInfo";
import { StepMembers } from "../components/new-group/StepMembers";
import { StepGovStructure } from "../components/new-group/StepGovStructure";
import { StepMeeting } from "../components/new-group/StepMeeting";
import { StepDate } from "../components/new-group/StepDate";
import { Toast } from "../components/ui/Toast";
import {
  applyForm,
  collectForm,
  defaultMembers,
  type WizardFormState,
} from "../components/new-group/formAdapters";
import {
  CHAIR_ROLE,
  dedupeDesignatedRoles,
  SECRETARIAT_ROLE,
  splitName,
} from "../components/new-group/types";
import type { Person, ReportEntry, ResourceEntry } from "../components/new-group/types";
import type { OrganisationListItem, TorFormPayload, TorSubmission } from "../types/governance";
import { useWizardExitGuard } from "../wizard/WizardExitGuardContext";

const STEPS = ["Info", "Members", "Reports To", "Meeting", "Date"];

const HEADINGS: Record<WizardMode, string> = {
  create: "New Governance Group",
  draft: "Continue Draft ToR",
  review: "Review ToR Submission",
  readonly: "ToR Submission",
};

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export default function NewGroupPage() {
  const navigate = useNavigate();
  // Present only on /registry/tor/:uuid — an existing submission being resumed,
  // reviewed or read back. Absent means a brand-new ToR.
  const { uuid: routeUuid } = useParams<{ uuid: string }>();
  const { user } = useAuth();
  const isSuperUser = user?.userRole === UserRole.SuperUser;

  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const [toastVariant, setToastVariant] = useState<"error" | "success">("error");

  // The submission this form is bound to. Set from the route, or minted by the
  // first Save on a new ToR so later saves update rather than duplicate.
  const [submissionUuid, setSubmissionUuid] = useState<string | null>(routeUuid ?? null);
  const [loading, setLoading] = useState(Boolean(routeUuid));
  const [mode, setMode] = useState<WizardMode>("create");
  const [adminComment, setAdminComment] = useState("");
  const [reviewAction, setReviewAction] = useState<"approve" | "reject" | null>(null);
  // The superuser's decision on a resolved submission, shown to the submitter
  // near the status bar. Captured for approvals as well as rejections.
  const [decision, setDecision] = useState<{
    status: "approved" | "rejected";
    note: string | null;
  } | null>(null);

  const [groupName, setGroupName] = useState("");
  const [entityType, setEntityType] = useState("");
  const [purpose, setPurpose] = useState("");
  const [responsibility, setResponsibility] = useState("");
  const [duplicateGroup, setDuplicateGroup] = useState<OrganisationListItem | null>(null);

  const [members, setMembers] = useState<Person[]>(defaultMembers);

  const [reportsTo, setReportsTo] = useState<ReportEntry[]>([]);

  const [meetingFreq, setMeetingFreq] = useState("");
  const [meetingDur, setMeetingDur] = useState("");
  const [resources, setResources] = useState<ResourceEntry[]>([]);

  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");

  // Load an existing submission and decide how the form should behave. Mode
  // depends on the row's status *and* the viewer's role, so it can only be
  // resolved once the fetch lands — not from the URL alone.
  useEffect(() => {
    if (!routeUuid) return;

    let cancelled = false;
    (async () => {
      try {
        const submission: TorSubmission = await fetchSubmission(routeUuid);
        if (cancelled) return;

        hydrateForm(applyForm(submission.form_json_data ?? {}));

        if (submission.status === "draft") {
          setMode("draft");
        } else if (submission.status === "pending_review") {
          // A superuser reviews it; the submitter can only look. Editing while
          // it sits with a reviewer would change the form under them.
          setMode(isSuperUser ? "review" : "readonly");
        } else {
          setMode("readonly");
          if (submission.status === "approved" || submission.status === "rejected") {
            setDecision({ status: submission.status, note: submission.admin_comment });
          } else {
            setDecision(null);
          }
        }
      } catch (err) {
        if (!cancelled) setErrors(apiErrorMessages(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [routeUuid, isSuperUser]);

  function notify(message: string, variant: "error" | "success" = "error") {
    setToastVariant(variant);
    setToast(message);
  }

  // Spreads an applyForm() result into the wizard's individual pieces of
  // state. Shared by the draft-load effect and autofill, so the two can never
  // drift on which fields get hydrated.
  function hydrateForm(loaded: WizardFormState) {
    setGroupName(loaded.groupName);
    setEntityType(loaded.entityType);
    setPurpose(loaded.purpose);
    setResponsibility(loaded.responsibility);
    // Heal any ingested data (an old draft, an autofilled form) that carries a
    // duplicate Chair/Secretariat onto a second member — those are single-holder.
    setMembers(dedupeDesignatedRoles(loaded.members));
    setReportsTo(loaded.reportsTo);
    setMeetingFreq(loaded.meetingFreq);
    setMeetingDur(loaded.meetingDur);
    setResources(loaded.resources);
    setValidFrom(loaded.validFrom);
    setValidTo(loaded.validTo);
  }

  // The LLM omits any field it couldn't find in the document, and applyForm()
  // already defaults every missing field to blank (it was built for partial
  // drafts) — so this needs nothing beyond running the result through the
  // same rehydration a resumed draft uses.
  function handleAutofill(form: Partial<TorFormPayload>) {
    hydrateForm(applyForm(form));
    notify("Fields populated from your document — please review each step.", "success");
  }

  // The wizard's fields as one serialisable object. `collectForm` turns this
  // into the ToR JSON that is both saved as a draft and submitted, so a draft
  // and a submission can never drift apart in shape.
  function currentForm() {
    return collectForm({
      groupName,
      entityType,
      purpose,
      responsibility,
      members,
      reportsTo,
      meetingFreq,
      meetingDur,
      resources,
      validFrom,
      validTo,
    });
  }

  // Validation is per-step so "Next" can report just the step in front of the
  // user, but submit runs every step. Checking only the last step (as this used
  // to) let a user skip forward past required fields and submit regardless.
  function validateStep(index: number): string[] {
    const errs: string[] = [];

    if (index === 0) {
      if (!groupName.trim()) errs.push("Group name is required.");
      if (duplicateGroup) {
        errs.push(`"${duplicateGroup.group_name}" is already registered.`);
      }
      if (!entityType.trim()) errs.push("Entity type is required.");
      if (!purpose.trim()) errs.push("Purpose is required.");
      if (!responsibility.trim()) errs.push("Responsibilities are required.");
    } else if (index === 1) {
      members.forEach((p, i) => {
        const label = p.roles.length > 0 ? p.roles.join(" · ") : `Member ${i + 1}`;
        if (p.roles.length === 0) errs.push(`${label}: at least one role is required.`);

        // Someone matched from the registry contributes only their roles — the
        // backend keeps their stored record and ignores the rest, so there is
        // nothing else here to check.
        if (p.uuid !== null) return;

        const { first_name, last_name } = splitName(p.name);
        if (!first_name) {
          errs.push(`${label}: a name is required.`);
        } else if (!last_name) {
          // The API stores a first and last name separately, so a single word
          // leaves the surname empty and would be rejected server-side.
          errs.push(`${label}: enter a full name, e.g. "Ashley Clay".`);
        }
        if (!EMAIL_RE.test(p.email.trim())) {
          errs.push(`${label}: a valid email is required.`);
        }
        if (!p.gender.trim()) errs.push(`${label}: gender is required.`);
        if (!p.representation) {
          errs.push(`${label}: select student, staff, or external.`);
        }
        if (p.representation !== "external" && !/^\d{7}$/.test(p.zId.trim())) {
          errs.push(`${label}: zID must be 7 digits for internal members.`);
        }
      });

      const hasRole = (role: string) =>
        members.some((m) => m.roles.some((r) => r.toLowerCase() === role.toLowerCase()));
      if (!hasRole(CHAIR_ROLE)) errs.push(`A ${CHAIR_ROLE} is required.`);
      if (!hasRole(SECRETARIAT_ROLE)) errs.push(`A ${SECRETARIAT_ROLE} is required.`);
    } else if (index === 2) {
      reportsTo.forEach((r, i) => {
        if (!r.groupName.trim()) {
          errs.push(`Reporting line ${i + 1}: a group name is required.`);
        }
      });
    } else if (index === 3) {
      resources.forEach((r, i) => {
        if (r.title.trim() && !r.url.trim()) {
          errs.push(`Resource ${i + 1}: a source link is required.`);
        }
        if (r.url.trim() && !r.title.trim()) {
          errs.push(`Resource ${i + 1}: a title is required.`);
        }
      });
    } else if (index === 4) {
      if (!validFrom) errs.push("Validity start date is required.");
      if (!validTo) errs.push("Validity end date is required.");
      if (validFrom && validTo && validTo <= validFrom) {
        errs.push("The end date must be later than the start date.");
      }
    }

    return errs;
  }

  function flagMissingInfo(stepsToCheck: number[]): boolean {
    const validationErrors = stepsToCheck.flatMap(validateStep);
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return true;
    }
    setErrors([]);
    return false;
  }

  function handleNext() {
    if (flagMissingInfo([step])) return;
    setStep(step + 1);
  }

  /**
   * Persist whatever is on screen, without validating it — that is the point
   * of a draft. Returns the submission uuid so callers can chain onto it.
   *
   * Deliberately stays on the page: the user asked to save their progress, not
   * to leave. Only Cancel and a completed submit navigate away.
   */
  async function saveProgress(): Promise<string | null> {
    setSavingDraft(true);
    try {
      const form = currentForm();
      if (submissionUuid) {
        await updateDraft(submissionUuid, form);
        notify("Draft saved.", "success");
        return submissionUuid;
      }
      const created = await createDraft(form);
      // Returned rather than read back from state, which has not updated yet.
      setSubmissionUuid(created.uuid);
      setMode("draft");
      notify("Draft saved.", "success");
      return created.uuid;
    } catch (err) {
      setErrors(apiErrorMessages(err));
      return null;
    } finally {
      setSavingDraft(false);
    }
  }

  // Lets the nav logo flush unsaved work as a draft before leaving. Only
  // create/draft register a guard: review/readonly have nothing to save as a
  // draft, so the logo should navigate away immediately for those.
  const { register } = useWizardExitGuard();
  useEffect(() => {
    if (mode !== "create" && mode !== "draft") return undefined;
    return register(async () => (await saveProgress()) !== null);
  }, [mode, register, saveProgress]);

  async function handleSubmit() {
    if (flagMissingInfo(STEPS.map((_, i) => i))) return;

    setSubmitting(true);
    try {
      if (submissionUuid) {
        // Flush the latest edits into the draft first, otherwise the server
        // would submit whatever was last saved rather than what is on screen.
        await updateDraft(submissionUuid, currentForm());
        await submitDraft(submissionUuid);
      } else {
        await createGroup(currentForm());
      }
      navigate("/registry");
    } catch (err) {
      setErrors(apiErrorMessages(err));
    } finally {
      setSubmitting(false);
    }
  }

  // Approve/Reject both save the reviewer's edits first, so the decision is
  // recorded against the form as they left it.
  async function handleReviewDecision() {
    if (!submissionUuid || !reviewAction) return;
    if (reviewAction === "approve" && flagMissingInfo(STEPS.map((_, i) => i))) {
      setReviewAction(null);
      return;
    }

    setSubmitting(true);
    try {
      await updateDraft(submissionUuid, currentForm());
      if (reviewAction === "approve") {
        await approveSubmission(submissionUuid, adminComment);
      } else {
        await rejectSubmission(submissionUuid, adminComment);
      }
      setReviewAction(null);
      navigate("/registry");
    } catch (err) {
      setErrors(apiErrorMessages(err));
      setReviewAction(null);
    } finally {
      setSubmitting(false);
    }
  }

  const stepPanels = [
    <StepInfo
      groupName={groupName}
      setGroupName={setGroupName}
      entityType={entityType}
      setEntityType={setEntityType}
      purpose={purpose}
      setPurpose={setPurpose}
      responsibility={responsibility}
      setResponsibility={setResponsibility}
      duplicateGroup={duplicateGroup}
      setDuplicateGroup={setDuplicateGroup}
      onDuplicate={(message) => notify(message)}
      onAutofill={handleAutofill}
      onAutofillError={(message) => notify(message)}
    />,
    <StepMembers members={members} setMembers={setMembers} />,
    <StepGovStructure reportsTo={reportsTo} setReportsTo={setReportsTo} />,
    <StepMeeting
      meetingFreq={meetingFreq}
      setMeetingFreq={setMeetingFreq}
      meetingDur={meetingDur}
      setMeetingDur={setMeetingDur}
      resources={resources}
      setResources={setResources}
    />,
    <StepDate
      validFrom={validFrom}
      setValidFrom={setValidFrom}
      validTo={validTo}
      setValidTo={setValidTo}
    />,
  ];

  if (loading) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  const readOnly = mode === "readonly";

  return (
    <div className="max-w-2xl">
      <h1 className="mb-4 text-xl font-semibold text-gray-900">{HEADINGS[mode]}</h1>

      {mode === "review" && (
        <p className="mb-4 rounded border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          You are reviewing a submitted ToR. Every field is editable — your
          changes are saved with your decision.
        </p>
      )}

      {decision &&
        (decision.status === "approved" ? (
          <div className="mb-4 rounded border border-green-200 bg-green-50 px-4 py-3">
            <p className="text-sm font-medium text-green-800">This ToR was approved</p>
            {decision.note && (
              <p className="mt-1 text-sm text-green-700">{decision.note}</p>
            )}
          </div>
        ) : (
          <div className="mb-4 rounded border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-sm font-medium text-red-800">This ToR was rejected</p>
            {decision.note && <p className="mt-1 text-sm text-red-700">{decision.note}</p>}
          </div>
        ))}

      <StepProgress step={step} steps={STEPS} />

      <div className="rounded-lg border border-gray-200 bg-white p-6">
        {/* A native disabled fieldset switches off every control inside it, so
            read-only mode needs no changes to the step components. */}
        <fieldset disabled={readOnly} className={readOnly ? "opacity-75" : undefined}>
          {stepPanels[step]}
        </fieldset>

        {errors.length > 0 && (
          <ul className="mt-4 list-inside list-disc space-y-1">
            {errors.map((e, i) => (
              <li key={i} className="text-sm text-red-600">
                {e}
              </li>
            ))}
          </ul>
        )}

        <StepNav
          step={step}
          totalSteps={STEPS.length}
          mode={mode}
          submitting={submitting}
          savingDraft={savingDraft}
          onBack={() => (step === 0 ? navigate("/registry") : setStep(step - 1))}
          onNext={handleNext}
          onSaveDraft={() => void saveProgress()}
          onSubmit={handleSubmit}
          onApprove={() => {
            setAdminComment("");
            setReviewAction("approve");
          }}
          onReject={() => {
            setAdminComment("");
            setReviewAction("reject");
          }}
        />
      </div>

      <Modal
        open={reviewAction !== null}
        title={reviewAction === "approve" ? "Approve this ToR?" : "Reject this ToR?"}
        onClose={() => setReviewAction(null)}
        footer={
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setReviewAction(null)}
              className="rounded border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleReviewDecision}
              disabled={submitting || (reviewAction === "reject" && !adminComment.trim())}
              className={`rounded px-4 py-2 text-sm text-white disabled:opacity-40 ${
                reviewAction === "approve"
                  ? "bg-green-600 hover:bg-green-700"
                  : "bg-red-600 hover:bg-red-700"
              }`}
            >
              {reviewAction === "approve" ? "Approve" : "Reject"}
            </button>
          </div>
        }
      >
        <p className="mb-3 text-sm text-gray-600">
          {reviewAction === "approve"
            ? "The group becomes active in the registry and the visualisation."
            : "Rejection is final. The group is removed from the visualisation and the submitter is shown your reason."}
        </p>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Comment{reviewAction === "reject" && <span className="text-red-600"> *</span>}
        </label>
        <textarea
          value={adminComment}
          onChange={(e) => setAdminComment(e.target.value)}
          rows={3}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          placeholder={
            reviewAction === "approve" ? "Optional note" : "Why is this being rejected?"
          }
        />
      </Modal>

      <Toast message={toast} variant={toastVariant} onDismiss={() => setToast(null)} />
    </div>
  );
}
