// How the wizard is being used. The same form serves creating a ToR, resuming
// a draft, reviewing someone else's submission, and simply reading one back.
export type WizardMode = "create" | "draft" | "review" | "readonly";

const BTN = {
  neutral: "px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded hover:bg-gray-50",
  primary:
    "px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed",
  approve:
    "px-4 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-40",
  reject: "px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-40",
};

export function StepNav({
  step,
  totalSteps,
  mode = "create",
  submitting,
  savingDraft = false,
  onBack,
  onNext,
  onSaveDraft,
  onSubmit,
  onApprove,
  onReject,
}: {
  step: number;
  totalSteps: number;
  mode?: WizardMode;
  submitting: boolean;
  savingDraft?: boolean;
  onBack: () => void;
  onNext: () => void;
  onSaveDraft: () => void;
  onSubmit: () => void;
  onApprove?: () => void;
  onReject?: () => void;
}) {
  const isLast = step === totalSteps - 1;
  // A resolved submission, or someone else's form under review, is a record to
  // read — there is nothing to save and no action to take.
  const canSave = mode !== "readonly";
  const busy = submitting || savingDraft;

  return (
    <div className="mt-6 flex justify-between border-t border-gray-100 pt-4">
      <button onClick={onBack} className={BTN.neutral}>
        {step === 0 ? "Cancel" : "Back"}
      </button>

      <div className="flex gap-3">
        {/* Save is available on every step: partial progress is the whole point
            of a draft, so it must not be gated behind reaching the last one. */}
        {canSave && (
          <button onClick={onSaveDraft} disabled={busy} className={BTN.neutral}>
            {savingDraft ? "Saving…" : "Save"}
          </button>
        )}

        {!isLast && (
          <button onClick={onNext} className={BTN.primary}>
            Next
          </button>
        )}

        {isLast && mode === "review" && (
          <>
            <button onClick={onReject} disabled={busy} className={BTN.reject}>
              Reject
            </button>
            <button onClick={onApprove} disabled={busy} className={BTN.approve}>
              {submitting ? "Working…" : "Approve"}
            </button>
          </>
        )}

        {isLast && (mode === "create" || mode === "draft") && (
          <button onClick={onSubmit} disabled={busy} className={BTN.primary}>
            {submitting ? "Submitting…" : "Submit for review"}
          </button>
        )}
      </div>
    </div>
  );
}
