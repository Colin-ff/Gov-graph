interface Props {
  // Optional micro-label header, matching GroupPanel's section labels.
  label?: string;
  right?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

// Borders-only card (no shadow) — the app's card convention.
export function SectionCard({ label, right, className, children }: Props) {
  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-6 ${className ?? ""}`}>
      {(label || right) && (
        <div className="flex items-center justify-between mb-4">
          {label && (
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest">
              {label}
            </p>
          )}
          {right}
        </div>
      )}
      {children}
    </div>
  );
}
