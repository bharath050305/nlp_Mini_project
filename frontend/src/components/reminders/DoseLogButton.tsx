import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { remindersApi } from "@/api/reminders";
import { getErrorMessage } from "@/api/client";
import Button from "@/components/ui/Button";
import type { ReminderSlot } from "@/api/types";

export default function DoseLogButton({
  patientId,
  reminderId,
  slot,
}: {
  patientId: number;
  reminderId: number;
  slot?: ReminderSlot;
}) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (status: "taken" | "skipped") =>
      remindersApi.markDose(patientId, reminderId, { slot_id: slot?.id, status }),
    onSuccess: (result, status) => {
      queryClient.invalidateQueries({ queryKey: ["reminders", patientId] });
      if (result.refill_alert_sent) {
        toast("Low stock — a refill alert was sent.", { icon: "⚠️" });
      } else {
        toast.success(status === "taken" ? "Dose logged as taken" : "Dose logged as skipped");
      }
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <div className="flex gap-1.5">
      <Button
        size="sm"
        variant="primary"
        loading={mutation.isPending && mutation.variables === "taken"}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate("taken")}
      >
        Mark taken
      </Button>
      <Button
        size="sm"
        variant="secondary"
        loading={mutation.isPending && mutation.variables === "skipped"}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate("skipped")}
      >
        Skip
      </Button>
    </div>
  );
}
