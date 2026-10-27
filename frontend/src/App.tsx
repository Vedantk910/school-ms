import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { Role } from "./api";
import Layout from "./Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Students from "./pages/Students";
import StudentDetail from "./pages/StudentDetail";
import Attendance from "./pages/Attendance";
import Exams from "./pages/Exams";
import Fees from "./pages/Fees";
import Insights from "./pages/Insights";
import Compose from "./pages/Compose";

function Guard({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { role } = useAuth();
  if (!role) return <Navigate to="/login" replace />;
  if (!roles.includes(role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  const loc = useLocation();
  const { token } = useAuth();
  if (loc.pathname === "/login") return <Login />;
  if (!token) return <Navigate to="/login" replace />;

  const all: Role[] = ["admin", "teacher", "parent", "student"];
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route
          path="/students"
          element={<Guard roles={["admin", "teacher"]}><Students /></Guard>}
        />
        <Route
          path="/students/:id"
          element={<Guard roles={all}><StudentDetail id={loc.pathname.split("/")[2] || ""} /></Guard>}
        />
        <Route
          path="/attendance"
          element={<Guard roles={["admin", "teacher"]}><Attendance /></Guard>}
        />
        <Route
          path="/exams"
          element={<Guard roles={all}><Exams /></Guard>}
        />
        <Route
          path="/fees"
          element={<Guard roles={["admin", "teacher"]}><Fees /></Guard>}
        />
        <Route
          path="/insights"
          element={<Guard roles={["admin", "teacher"]}><Insights /></Guard>}
        />
        <Route
          path="/compose"
          element={<Guard roles={["admin", "teacher"]}><Compose /></Guard>}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
