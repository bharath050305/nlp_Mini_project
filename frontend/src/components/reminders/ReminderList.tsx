import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import type { ReminderOut } from "@/api/types";
import { remindersApi } from "@/api/reminders";
import { getErrorMessage } from "@/api/client";
import Card, { CardBody } from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import DoseLogButton from "./DoseLogButton";
import { timeOfDayLabel } from "@/utils/format";

export default function ReminderList({
  patientId,
  reminders,
  onAddClick,
}: {
  patientId: number;
  reminders: ReminderOut[];
  onAddClick?: () => void;
}) {
  const queryClient = useQueryClient();

  const toggleActive = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      remindersApi.update(patientId, id, { active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminders", patientId] });
      toast.success("Reminder updated");
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const removeReminder = useMutation({
    mutationFn: (id: number) => remindersApi.remove(patientId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminders", patientId] });
      toast.success("Reminder deleted");
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  if (reminders.length === 0) {
    return (
      <EmptyState
        title="No reminders yet"
        description="Add one to get started tracking medicine schedules and refills."
        action={onAddClick && <Button onClick={onAddClick}>Add reminder</Button>}
      />
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {reminders.map((r) => {
        const lowStock =
          r.low_stock_threshold != null &&
          r.quantity_remaining != null &&
          r.quantity_remaining <= r.low_stock_threshold;

        return (
          <Card key={r.id} className={!r.active ? "opacity-60" : ""}>
            <CardBody>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-slate-800">{r.medicine_name}</p>
                  {r.dosage && <p className="text-xs text-slate-400">{r.dosage}</p>}
                </div>
                <div className="flex flex-wrap justify-end gap-1">
                  <Badge tone="brand">{r.schedule_type}</Badge>
                  {!r.active && <Badge tone="neutral">inactive</Badge>}
                  {lowStock && <Badge tone="danger">low stock</Badge>}
                  {r.refill_alert_sent && <Badge tone="warning">refill alert sent</Badge>}
                </div>
              </div>

              {r.slots.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {r.slots.map((s) => (
                    <span
                      key={s.id}
                      className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600"
                    >
                      {s.day_of_month ? `Day ${s.day_of_month} · ` : ""}
                      {timeOfDayLabel(s.time_of_day)}
                    </span>
                  ))}
                </div>
              )}

              {r.quantity_total != null && (
                <p className="mt-3 text-xs text-slate-500">
                  {r.quantity_remaining ?? 0} / {r.quantity_total} pills remaining
                  {r.quantity_per_dose != null ? ` · ${r.quantity_per_dose} per dose` : ""}
                </p>
              )}

              <div className="mt-4 flex items-center justify-between">
                <DoseLogButton patientId={patientId} reminderId={r.id} slot={r.slots[0]} />
                <div className="flex gap-2">
                  <button
                    onClick={() => toggleActive.mutate({ id: r.id, active: !r.active })}
                    className="text-xs font-medium text-slate-500 hover:underline"
                  >
                    {r.active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete reminder for ${r.medicine_name}?`)) {
                        removeReminder.mutate(r.id);
                      }
                    }}
                    className="text-xs font-medium text-rose-500 hover:underline"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </CardBody>
          </Card>
        );
      })}
    </div>
  );
}
