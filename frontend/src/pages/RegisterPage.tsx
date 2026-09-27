import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiErrorMessages } from "../api/client";
import { UserRole } from "../auth/role";
import { useAuth } from "../auth/AuthContext";

const inp =
  "w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [userRole, setUserRole] = useState<UserRole>(UserRole.Staff);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await register({
        displayName,
        email,
        password,
        userRole,
      });
      if (result.kind === "authenticated") {
        navigate("/registry", { replace: true });
      } else {
        setMessage(result.message);
      }
    } catch (err) {
      setError(apiErrorMessages(err)[0]);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm bg-white border border-gray-200 rounded-lg p-6 space-y-4"
      >
        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-7 h-7 rounded-full bg-blue-600" />
          <span className="font-semibold text-gray-900 tracking-tight">GovGraph</span>
        </div>
        <h1 className="text-lg font-semibold text-gray-900">Register</h1>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Display name</label>
          <input
            className={inp}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            autoComplete="name"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            className={inp}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <input
            className={inp}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Confirm password</label>
          <input
            className={inp}
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Account type</label>
          <select
            className={inp}
            value={userRole}
            onChange={(e) => setUserRole(e.target.value as UserRole)}
          >
            <option value={UserRole.Staff}>Staff</option>
            <option value={UserRole.SuperUser}>Admin</option>
          </select>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {message && <p className="text-sm text-green-700">{message}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-40"
        >
          {submitting ? "Registering…" : "Register"}
        </button>

        <p className="text-center text-sm text-gray-500">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-blue-600 hover:text-blue-700">
            Log in
          </Link>
        </p>
      </form>
    </div>
  );
}
