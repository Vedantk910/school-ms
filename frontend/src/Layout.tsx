import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "./auth";
import { Role } from "./api";

const NAV: { to: string; label: string; roles: Role[] }[] = [
  { to: "/", label: "Dashboard", roles: ["admin", "teacher", "parent", "student"] },
  { to: "/students", label: "Students", roles: ["admin", "teacher"] },
  { to: "/attendance", label: "Attendance", roles: ["admin", "teacher"] },
  { to: "/exams", label: "Exams", roles: ["admin", "teacher", "parent", "student"] },
  { to: "/fees", label: "Fees", roles: ["admin", "teacher"] },
  { to: "/insights", label: "AI Insights", roles: ["admin", "teacher"] },
  { to: "/compose", label: "Compose Notice", roles: ["admin", "teacher"] },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { role, username, logout, switchRole } = useAuth();
  const nav = useNavigate();
  const items = NAV.filter((n) => role && n.roles.includes(role));

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">MS</span>
          <div>
            <div className="brand-name">School-MS</div>
            <div className="brand-sub">MSBSHSE · demo</div>
          </div>
        </div>
        <nav>
          {items.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} className="nav-link">
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="muted small">
            {username} · <b>{role}</b>
          </div>
          <label className="small">
            <span className="muted">Switch role</span>
            <select
              defaultValue=""
              onChange={(e) => {
                if (!e.target.value) return;
                switchRole(e.target.value);
                nav("/");
              }}
            >
              <option value="" disabled>
                demo…
              </option>
              <option value="admin">Admin</option>
              <option value="teach01">Teacher</option>
              <option value="parent01">Parent</option>
              <option value="stud0001">Student</option>
            </select>
          </label>
          <button className="btn ghost" onClick={() => { logout(); nav("/login"); }}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
