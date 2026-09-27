import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import NewGroupPage from "./pages/NewGroupPage";
import RegistryPage from "./pages/RegistryPage";
import VisualisationPage from "./pages/VisualisationPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import AdminRegistryPage from "./pages/AdminRegistryPage";
import RequireRole from "./components/RequireRole";
import { UserRole } from "./auth/role";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { WizardExitGuardProvider } from "./wizard/WizardExitGuardContext";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <WizardExitGuardProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          {/* Every view is behind a login: the registry names real people and the
              groups they sit on, so none of it is public. */}
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/registry" replace />} />
            <Route
              path="registry"
              element={
                <RequireAuth>
                  <RegistryPage />
                </RequireAuth>
              }
            />
            <Route
              path="registry/new"
              element={
                <RequireAuth>
                  <NewGroupPage />
                </RequireAuth>
              }
            />
            {/* One existing submission: resumed as a draft, opened for review, or
                read back. Deliberately not role-gated here — the server decides
                what the caller may see (404 for someone else's draft, 403 to
                approve without privileges), and a second guard in the router
                would be a duplicate source of truth that drifts. */}
            <Route
              path="registry/tor/:uuid"
              element={
                <RequireAuth>
                  <NewGroupPage />
                </RequireAuth>
              }
            />
            <Route
              path="visualisation"
              element={
                <RequireAuth>
                  <VisualisationPage />
                </RequireAuth>
              }
            />
            <Route
              path="analytics"
              element={
                <RequireRole role={UserRole.SuperUser}>
                  <AnalyticsPage />
                </RequireRole>
              }
            />
            <Route
              path="admin-registry"
              element={
                <RequireRole role={UserRole.SuperUser}>
                  <AdminRegistryPage />
                </RequireRole>
              }
            />
            {/* A link to a deleted draft would otherwise render a blank page. */}
            <Route path="*" element={<Navigate to="/registry" replace />} />
          </Route>
        </Routes>
      </WizardExitGuardProvider>
    </AuthProvider>
  );
}
