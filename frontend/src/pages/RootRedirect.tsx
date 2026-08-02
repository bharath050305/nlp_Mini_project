import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { roleLandingPath } from "@/components/layout/navConfig";
import { FullPageSpinner } from "@/components/ui/Spinner";

export default function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={roleLandingPath[user.role]} replace />;
}
