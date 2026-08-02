import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "@/api/notifications";
import Spinner from "@/components/ui/Spinner";
import Badge from "@/components/ui/Badge";
import { Link } from "react-router-dom";
import { formatDateTime } from "@/utils/format";

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const unreadQuery = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: () => notificationsApi.list({ unread_only: true, limit: 20 }),
    refetchInterval: 30000,
  });

  const markAllRead = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markOneRead = useMutation({
    mutationFn: (id: number) => notificationsApi.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const unread = unreadQuery.data ?? [];
  const count = unread.length;

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative flex h-9 w-9 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100"
        aria-label="Notifications"
      >
        <BellIcon />
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold text-white">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 rounded-xl border border-slate-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <span className="text-sm font-semibold text-slate-700">Notifications</span>
            {count > 0 && (
              <button
                onClick={() => markAllRead.mutate()}
                className="text-xs font-medium text-brand-600 hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {unreadQuery.isLoading ? (
              <div className="flex justify-center py-6">
                <Spinner />
              </div>
            ) : unread.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-slate-400">
                You're all caught up.
              </p>
            ) : (
              unread.map((n) => (
                <button
                  key={n.id}
                  onClick={() => markOneRead.mutate(n.id)}
                  className="block w-full border-b border-slate-50 px-4 py-3 text-left hover:bg-slate-50"
                >
                  <div className="flex items-center gap-2">
                    <Badge tone="info">{n.type.replace(/_/g, " ")}</Badge>
                    <span className="text-xs text-slate-400">{formatDateTime(n.created_at)}</span>
                  </div>
                  <p className="mt-1 text-sm font-medium text-slate-700">{n.title}</p>
                  <p className="line-clamp-2 text-xs text-slate-500">{n.body}</p>
                </button>
              ))
            )}
          </div>
          <div className="border-t border-slate-100 px-4 py-2 text-center">
            <Link
              to="/notifications"
              onClick={() => setOpen(false)}
              className="text-xs font-medium text-brand-600 hover:underline"
            >
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function BellIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
