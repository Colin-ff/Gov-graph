import { createContext, useCallback, useContext, useMemo, useRef } from "react";

// Resolves false to block navigation (e.g. the flush failed and the caller
// should stay put so the wizard's own error UI stays visible).
type ExitGuard = () => Promise<boolean>;

interface WizardExitGuardContextValue {
  register: (guard: ExitGuard) => () => void;
  runAndClear: () => Promise<boolean>;
}

const WizardExitGuardContext = createContext<WizardExitGuardContextValue | null>(null);

// Lets a mounted wizard register a "flush my unsaved work" function that an
// unrelated component (the nav logo) can invoke without knowing whether a
// wizard is even mounted. A ref, not state: nothing here should re-render
// anyone — it's read once, at click time.
export function WizardExitGuardProvider({ children }: { children: React.ReactNode }) {
  const guardRef = useRef<ExitGuard | null>(null);

  const register = useCallback((guard: ExitGuard) => {
    guardRef.current = guard;
    return () => {
      // Only clear if this is still the registration being cleaned up, so a
      // stale unmount can't wipe out a newer registration.
      if (guardRef.current === guard) guardRef.current = null;
    };
  }, []);

  const runAndClear = useCallback(async () => {
    const guard = guardRef.current;
    if (!guard) return true;
    return guard();
  }, []);

  const value = useMemo(() => ({ register, runAndClear }), [register, runAndClear]);

  return (
    <WizardExitGuardContext.Provider value={value}>{children}</WizardExitGuardContext.Provider>
  );
}

export function useWizardExitGuard(): WizardExitGuardContextValue {
  const ctx = useContext(WizardExitGuardContext);
  if (ctx === null) {
    throw new Error("useWizardExitGuard must be used within a WizardExitGuardProvider");
  }
  return ctx;
}
