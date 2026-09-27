import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import type { UserRole } from "../auth/role";

interface Props {
  role: UserRole;
  children: React.ReactNode;
}

// Route guard mirroring RequireAuth in App.tsx, but role-aware: anonymous
// visitors are sent to /login; authenticated-but-wrong-role visitors are sent
// to /registry (so a bookmarked /analytics as STAFF never renders a broken page).
export default function RequireRole({ role, children }: Props) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (user.userRole !== role) {
    return <Navigate to="/registry" replace />;
  }
  return <>{children}</>;
}
