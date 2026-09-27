import { useEffect, useRef } from "react";

interface Props {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

// Minimal dialog: a scrim plus a centred panel, layered above the ToR form.
// Closes on Escape and on scrim click, and moves focus into the panel so
// keyboard users are not left behind on the page underneath.
export function Modal({ open, title, onClose, children, footer }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Callers pass an inline arrow, so `onClose` is a new function on every
  // render. Holding it in a ref keeps it out of the effect dependencies below.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onCloseRef.current();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  // Focus the panel when it opens — and only then. Re-running this on every
  // render pulled focus out of whichever field was being typed into, so only
  // the first keystroke of a description ever landed.
  useEffect(() => {
    if (open) panelRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onMouseDown={(e) => {
        // Only a click that both starts and ends on the scrim dismisses, so a
        // drag that ends outside the panel does not close it.
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-md rounded-lg bg-white shadow-xl outline-none"
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
          <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="text-lg leading-none text-gray-400 hover:text-gray-600"
          >
            ×
          </button>
        </div>

        <div className="px-5 py-4">{children}</div>

        {footer && (
          <div className="flex justify-end gap-2 border-t border-gray-200 px-5 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
