interface Props {
  message: string;
  className?: string;
}

// Centred muted message, matching RegistryPage's "No groups registered yet."
// Analytics uses honest empty states rather than mock-data fallbacks.
export function EmptyState({ message, className }: Props) {
  return (
    <div className={`flex items-center justify-center py-10 ${className ?? ""}`}>
      <p className="text-sm text-gray-500 text-center">{message}</p>
    </div>
  );
}
