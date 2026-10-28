import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./auth";
import { Role } from "./api";
import {
  IconBanknote,
  IconBook,
  IconCalendar,
  IconGradCap,
  IconGrid,
  IconLogout,
  IconPen,
  IconSparkles,
  IconUsers,
} from "./icons";
import { ReactNode } from "react";

const NAV: { to: string; label: string; roles: Role[]; icon: (p: { size?: number }) => ReactNode }[] = [
  { to: "/", label: "Dashboard", roles: ["admin", "teacher", "parent", "student"], icon: IconGrid },
  { to: "/students", label: "Students", roles: ["admin", "teacher"], icon: IconUsers },
  { to: "/attendance", label: "Attendance", roles: ["admin", "teacher"], icon: IconCalendar },
  { to: "/exams", label: "Exams", roles: ["admin", "teacher", "parent", "student"], icon: IconBook },
  { to: "/fees", label: "Fees", roles: ["admin", "teacher"], icon: IconBanknote },
  { to: "/insights", label: "AI Insights", roles: ["admin", "teacher"], icon: IconSparkles },
  { to: "/compose", label: "Compose Notice", roles: ["admin", "teacher"], icon: IconPen },
];

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  teacher: "Teacher",
  parent: "Parent",
  student: "Student",
};

const ROLE_TONE: Record<string, string> = {
  admin: "",
  teacher: "teal",
  parent: "amber",
  student: "slate",
};

function initials(name: string | null): string {
  if (!name) return "MS";
  return name
    .replace(/[0-9]/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("") || name.slice(0, 2).toUpperCase();
}

function topbarFor(path: string, items: typeof NAV): { section: string; title: string } {
  const exact = items.find((n) => n.to === path);
  if (exact) return { section: "Overview", title: exact.label };
  if (path.startsWith("/students/")) {
    const id = path.split("/")[2];
    return { section: "Students", title: id ? `Student profile · #${id}` : "Student profile" };
  }
  return { section: "Overview", title: "School-MS" };
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { role, username, logout, switchRole } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const items = NAV.filter((n) => role && n.roles.includes(role));
  const { section, title } = topbarFor(loc.pathname, NAV);
  const avatarTone =
    role === "teacher" ? "avatar teal" : role === "parent" ? "avatar amber" : role === "student" ? "avatar slate" : "avatar";

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">
            <IconGradCap size={22} />
          </span>
          <div>
            <div className="brand-name">School-MS</div>
            <div className="brand-sub">MSBSHSE · demo</div>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="Primary">
          {items.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} className="nav-link">
              {n.icon({ size: 20 })}
              <span className="nav-label">{n.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="foot-text muted small">
            {username} · <b>{ROLE_LABEL[role ?? ""] ?? role}</b>
          </div>
          <label className="foot-select-wrap">
            <span className="foot-text muted small">Switch role (demo)</span>
            <select
              className="foot-select"
              defaultValue=""
              aria-label="Switch demo role"
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
            <IconLogout size={17} />
            <span className="foot-text">Sign out</span>
          </button>
        </div>
      </aside>

      <div className="shell-col">
        <header className="topbar">
          <div className="topbar-title">
            <span className="topbar-crumb">{section}</span>
            <h1>{title}</h1>
          </div>
          <div className="topbar-user">
            <span className={`role-badge ${ROLE_TONE[role ?? ""] ?? ""}`}>
              <span className="dot" />
              {ROLE_LABEL[role ?? ""] ?? role}
            </span>
            <div className="user-chip">
              <span className={avatarTone} aria-hidden="true">
                {initials(username)}
              </span>
              <span className="who">
                <b>{username}</b>
                <span>{ROLE_LABEL[role ?? ""] ?? "Member"}</span>
              </span>
            </div>
          </div>
        </header>
        <main className="content">
          <div className="content-inner">{children}</div>
        </main>
      </div>
    </div>
  );
}
