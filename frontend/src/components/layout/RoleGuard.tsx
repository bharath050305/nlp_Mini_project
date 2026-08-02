import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import type { Role } from "@/api/types";
import { roleLandingPath } from "./navConfig";
import { FullPageSpinner } from "@/components/ui/Spinner";

export default function RoleGuard({ allow }: { allow: Role[] }) {
  const { user, loading } = useAuth();

  if (loading) return <FullPageSpinner />;
  if (!user) return <Navigate to="/login" replace />;
  if (!allow.includes(user.role)) {
    return <Navigate to={roleLandingPath[user.role]} replace />;
  }
  return <Outlet />;
}

export function RequireAuth() {
  const { user, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}
