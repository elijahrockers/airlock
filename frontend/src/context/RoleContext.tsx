import { createContext, useContext, useState } from "react";
import { type UserRole, setApiRole } from "../api/client";

function loadRole(): UserRole {
  const stored = localStorage.getItem("airlock-role");
  const role = stored === "researcher" ? "researcher" : "broker";
  setApiRole(role);
  return role;
}

interface RoleContextValue {
  role: UserRole;
  setRole: (role: UserRole) => void;
}

const RoleContext = createContext<RoleContextValue>({
  role: "broker",
  setRole: () => {},
});

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<UserRole>(loadRole);

  const setRole = (r: UserRole) => {
    localStorage.setItem("airlock-role", r);
    setApiRole(r);
    setRoleState(r);
  };

  return (
    <RoleContext.Provider value={{ role, setRole }}>
      {children}
    </RoleContext.Provider>
  );
}

export function useRole() {
  return useContext(RoleContext);
}
