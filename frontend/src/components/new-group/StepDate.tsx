import { FormField } from "./FormField";

const inp =
  "w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";

export function StepDate({
  validFrom,
  setValidFrom,
  validTo,
  setValidTo,
}: {
  validFrom: string;
  setValidFrom: (v: string) => void;
  validTo: string;
  setValidTo: (v: string) => void;
}) {
  return (
    <div className="space-y-4">
      <FormField label="Validity starts from" required>
        <input
          className={inp}
          type="date"
          value={validFrom}
          onChange={(e) => setValidFrom(e.target.value)}
        />
        <p className="mt-1 text-xs text-gray-400">
          A past date is fine — groups that have been running for years still
          need registering.
        </p>
      </FormField>
      <FormField label="Validity ends on" required>
        <input
          className={inp}
          type="date"
          // A window cannot end before it starts, so the picker will not offer
          // those dates in the first place.
          min={validFrom || undefined}
          value={validTo}
          onChange={(e) => setValidTo(e.target.value)}
        />
      </FormField>
    </div>
  );
}
