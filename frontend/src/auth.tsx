import { createContext, useContext, useState } from "react";
import { api, LoginResult, Role } from "./api";

interface AuthState {
  token: string | null;
  role: Role | null;
  username: string | null;
  login: (u: string, p: string) => Promise<LoginResult>;
  logout: () => void;
  switchRole: (u: string) => Promise<void>; // dev-only convenience
}

const Ctx = createContext<AuthState>(null!);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<{ token: string | null; role: Role | null; username: string | null }>(
    { token: null, role: null, username: null }
  );

  async function login(u: string, p: string) {
    const r = await api<LoginResult>("/auth/login", { method: "POST", body: { username: u, password: p } });
    setState({ token: r.access_token, role: r.role, username: r.username });
    return r;
  }

  async function switchRole(u: string) {
    // demo credentials: password === role name
    const pw = u === "admin" ? "admin" : u === "teach01" ? "teacher" : u === "parent01" ? "parent" : "student";
    await login(u, pw);
  }

  return (
    <Ctx.Provider
      value={{ ...state, login, logout: () => setState({ token: null, role: null, username: null }), switchRole }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  return useContext(Ctx);
}
