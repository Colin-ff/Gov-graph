import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { UserRole } from "../auth/role";
import { useWizardExitGuard } from "../wizard/WizardExitGuardContext";

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { runAndClear } = useWizardExitGuard();
  const [leaving, setLeaving] = useState(false);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  // If a ToR wizard is mounted with unsaved work, this flushes it as a draft
  // before leaving — so clicking the logo never silently loses progress.
  async function handleLogoClick() {
    if (leaving) return;
    setLeaving(true);
    try {
      const canNavigate = await runAndClear();
      if (canNavigate) navigate("/registry");
    } finally {
      setLeaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center gap-8">
          <button
            type="button"
            onClick={handleLogoClick}
            disabled={leaving}
            className="flex items-center gap-2.5 disabled:opacity-60"
          >
            <div className="w-7 h-7 rounded-full bg-blue-600" />
            <span className="font-semibold text-gray-900 tracking-tight">GovGraph</span>
          </button>
          <NavLink
            to="/registry"
            className={({ isActive }) =>
              `text-sm ${isActive ? "text-blue-600 font-medium" : "text-gray-600 hover:text-gray-900"}`
            }
          >
            ToR Registry
          </NavLink>
          <NavLink
            to="/visualisation"
            className={({ isActive }) =>
              `text-sm ${isActive ? "text-blue-600 font-medium" : "text-gray-600 hover:text-gray-900"}`
            }
          >
            Visualisation
          </NavLink>
          {user?.userRole === UserRole.SuperUser && (
            <>
              <NavLink
                to="/analytics"
                className={({ isActive }) =>
                  `text-sm ${isActive ? "text-blue-600 font-medium" : "text-gray-600 hover:text-gray-900"}`
                }
              >
                Analytics
              </NavLink>
              <NavLink
                to="/admin-registry"
                className={({ isActive }) =>
                  `text-sm ${isActive ? "text-blue-600 font-medium" : "text-gray-600 hover:text-gray-900"}`
                }
              >
                Admin Registry
              </NavLink>
            </>
          )}
          {user ? (
            <div className="ml-auto flex items-center gap-3">
              <span className="text-sm text-gray-600">{user.displayName}</span>
              <button
                onClick={handleLogout}
                className="text-sm font-semibold border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-1.5 rounded-lg"
              >
                Logout
              </button>
            </div>
          ) : (
            <button
              onClick={() => navigate("/login")}
              className="ml-auto text-sm font-semibold bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg"
            >
              Login
            </button>
          )}
        </div>
      </nav>
      <main className={location.pathname === "/visualisation" ? "" : "max-w-7xl mx-auto px-6 py-8"}>
        <Outlet />
      </main>
    </div>
  );
}
