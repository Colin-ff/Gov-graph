export function StepProgress({ step, steps }: { step: number; steps: string[] }) {
  return (
    <>
      <div className="flex gap-1 mb-1">
        {steps.map((_, i) => (
          <div key={i} className={`h-1 flex-1 rounded-full ${i <= step ? "bg-blue-600" : "bg-gray-200"}`} />
        ))}
      </div>
      <p className="text-xs text-gray-400 mb-6">
        Step {step + 1} of {steps.length} — {steps[step]}
      </p>
    </>
  );
}
