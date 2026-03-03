import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { type UserRole } from "../api/client";
import { useRole } from "../context/RoleContext";

const NAV: Array<{
  to: string;
  label: string | { broker: string; researcher: string };
  role?: "broker" | "researcher";
}> = [
  { to: "/", label: "Studies" },
  { to: "/new", label: "New Request", role: "researcher" },
  { to: "/keys", label: "Key Management", role: "broker" },
];

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { role, setRole } = useRole();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <Link to="/" className="text-xl font-bold text-gray-900">
              Airlock
            </Link>
            <div className="flex items-center gap-6">
              <nav className="flex gap-6">
                {NAV.filter((item) => !item.role || item.role === role).map(
                  (item) => {
                    const label =
                      typeof item.label === "string" ? item.label : item.label[role];
                    return (
                      <Link
                        key={item.to}
                        to={item.to}
                        className={`text-sm font-medium ${
                          location.pathname === item.to
                            ? "text-blue-600"
                            : "text-gray-500 hover:text-gray-700"
                        }`}
                      >
                        {label}
                      </Link>
                    );
                  },
                )}
              </nav>
              <select
                value={role}
                onChange={(e) => {
                  setRole(e.target.value as UserRole);
                  navigate("/");
                }}
                className="rounded-md border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700"
              >
                <option value="broker">Broker</option>
                <option value="researcher">Researcher</option>
              </select>
            </div>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
