import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "@/api/notifications";
import Card, { CardBody } from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { formatDateTime } from "@/utils/format";

const PAGE_SIZE = 20;

export default function NotificationsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["notifications", "all", unreadOnly, offset],
    queryFn: () =>
      notificationsApi.list({ unread_only: unreadOnly, limit: PAGE_SIZE, offset }),
  });

  const markAllRead = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const markOneRead = useMutation({
    mutationFn: (id: number) => notificationsApi.markRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const notifications = query.data ?? [];

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Notifications</h1>
          <p className="text-sm text-slate-500">Your full notification history.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(e) => {
                setUnreadOnly(e.target.checked);
                setOffset(0);
              }}
            />
            Unread only
          </label>
          <Button variant="secondary" size="sm" onClick={() => markAllRead.mutate()}>
            Mark all read
          </Button>
        </div>
      </div>

      {query.isLoading ? (
        <FullPageSpinner />
      ) : notifications.length === 0 ? (
        <EmptyState title="No notifications" description="You're all caught up." />
      ) : (
        <div className="flex flex-col gap-2">
          {notifications.map((n) => (
            <Card key={n.id} className={n.status !== "read" ? "border-brand-200" : ""}>
              <CardBody className="flex flex-col gap-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="info">{n.type.replace(/_/g, " ")}</Badge>
                  {n.status !== "read" && <Badge tone="brand">unread</Badge>}
                  <span className="ml-auto text-xs text-slate-400">
                    {formatDateTime(n.created_at)}
                  </span>
                </div>
                <p className="text-sm font-medium text-slate-700">{n.title}</p>
                <p className="text-sm text-slate-500">{n.body}</p>
                {n.status !== "read" && (
                  <button
                    onClick={() => markOneRead.mutate(n.id)}
                    className="mt-1 self-start text-xs font-medium text-brand-600 hover:underline"
                  >
                    Mark as read
                  </button>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      <div className="mt-4 flex justify-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={offset === 0}
          onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
        >
          Previous
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={notifications.length < PAGE_SIZE}
          onClick={() => setOffset((o) => o + PAGE_SIZE)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
