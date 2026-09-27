import { useEffect, useState } from "react";
import { apiErrorMessages } from "../../api/client";

export interface AnalyticsResource<T> {
  data: T | null;
  loading: boolean;
  error: string;
}

// Small {data, loading, error} fetch hook shared by the analytics tabs. There
// are 16 endpoints, so a hand-rolled useState triad per call would be extremely
// repetitive. A `cancelled` flag guards against setting state after unmount or
// after the deps change mid-flight (which the app's existing fetches lack).
//
// `fetcher` is re-run whenever `deps` change; pass `null` as the fetcher to
// represent "nothing selected yet" (stays in the idle, non-loading state).
export function useAnalyticsResource<T>(
  fetcher: (() => Promise<T>) | null,
  deps: React.DependencyList,
): AnalyticsResource<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!fetcher) {
      setData(null);
      setLoading(false);
      setError("");
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setData(null);
          setError(apiErrorMessages(err)[0]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error };
}
