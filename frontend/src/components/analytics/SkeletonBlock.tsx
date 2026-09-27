interface Props {
  className?: string;
}

// Loading placeholder. Plain pulse — no shimmer (per the "purposeful only"
// animation decision).
export function SkeletonBlock({ className }: Props) {
  return <div className={`bg-gray-100 rounded animate-pulse ${className ?? "h-4 w-full"}`} />;
}
