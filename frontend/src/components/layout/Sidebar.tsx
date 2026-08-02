import { NavLink } from "react-router-dom";
import clsx from "clsx";
import { useAuth } from "@/context/AuthContext";
import { navByRole } from "./navConfig";

function LogoMark() {
  return (
    <div className="flex items-center gap-2 px-2">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white font-bold text-sm">
        M
      </div>
      <span className="text-lg font-semibold text-slate-800">MediAgent</span>
    </div>
  );
}

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  if (!user) return null;
  const items = navByRole[user.role];

  return (
    <div className="flex h-full flex-col gap-6 py-6">
      <LogoMark />
      <nav className="flex flex-1 flex-col gap-1 px-2">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-800",
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="mx-2 rounded-lg bg-slate-50 px-3 py-3 text-xs text-slate-400">
        Signed in as <span className="font-medium text-slate-600">{user.role}</span>
      </div>
    </div>
  );
}
