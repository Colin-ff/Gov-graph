import { useEffect } from "react";

type ToastVariant = "error" | "success";

interface Props {
  message: string | null;
  onDismiss: () => void;
  // Auto-hide delay in ms. Pass 0 to keep it up until dismissed.
  duration?: number;
  // Defaults to "error" so existing call sites keep the styling they had.
  variant?: ToastVariant;
}

const VARIANTS: Record<ToastVariant, { box: string; text: string; close: string }> = {
  error: {
    box: "border-red-200 bg-red-50",
    text: "text-red-700",
    close: "text-red-400 hover:text-red-600",
  },
  success: {
    box: "border-green-200 bg-green-50",
    text: "text-green-700",
    close: "text-green-500 hover:text-green-700",
  },
};

// Transient notice pinned to the bottom-left corner. Used where a message
// belongs to the page rather than to one field — e.g. "that group is already
// registered", which is about the submission, not the text in the box.
export function Toast({ message, onDismiss, duration = 6000, variant = "error" }: Props) {
  useEffect(() => {
    if (!message || duration <= 0) return;
    const timer = setTimeout(onDismiss, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onDismiss]);

  if (!message) return null;

  const styles = VARIANTS[variant];

  return (
    <div
      role="alert"
      className={`fixed bottom-4 left-4 z-50 flex max-w-sm items-start gap-3 rounded-lg border px-4 py-3 shadow-lg ${styles.box}`}
    >
      <p className={`text-sm ${styles.text}`}>{message}</p>
      <button
        type="button"
        aria-label="Dismiss"
        onClick={onDismiss}
        className={`text-lg leading-none ${styles.close}`}
      >
        ×
      </button>
    </div>
  );
}
