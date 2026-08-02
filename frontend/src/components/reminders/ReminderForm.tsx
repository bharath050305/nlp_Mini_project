import { useState } from "react";
import type { ScheduleType } from "@/api/types";
import type { CreateReminderPayload } from "@/api/reminders";
import { TextInput } from "@/components/ui/FormField";
import Button from "@/components/ui/Button";
import ScheduleBuilder from "./ScheduleBuilder";
import type { SlotFormValue } from "./ScheduleBuilder";

export default function ReminderForm({
  onSubmit,
  onCancel,
  submitting,
}: {
  onSubmit: (payload: CreateReminderPayload) => void;
  onCancel: () => void;
  submitting: boolean;
}) {
  const [medicineName, setMedicineName] = useState("");
  const [dosage, setDosage] = useState("");
  const [scheduleType, setScheduleType] = useState<ScheduleType>("daily");
  const [slots, setSlots] = useState<SlotFormValue[]>([{ time_of_day: "08:00", day_of_month: "1" }]);
  const [quantityTotal, setQuantityTotal] = useState("");
  const [quantityPerDose, setQuantityPerDose] = useState("");
  const [lowStockThreshold, setLowStockThreshold] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!medicineName.trim()) {
      setError("Medicine name is required.");
      return;
    }
    if (scheduleType !== "unscheduled" && slots.length === 0) {
      setError("Add at least one schedule slot, or choose Unscheduled.");
      return;
    }
    if (scheduleType === "monthly") {
      const invalid = slots.some((s) => {
        const d = Number(s.day_of_month);
        return !d || d < 1 || d > 28;
      });
      if (invalid) {
        setError("Day of month must be between 1 and 28 for every slot.");
        return;
      }
    }

    const payload: CreateReminderPayload = {
      medicine_name: medicineName.trim(),
      dosage: dosage.trim() || null,
      schedule_type: scheduleType,
      quantity_total: quantityTotal ? Number(quantityTotal) : null,
      quantity_per_dose: quantityPerDose ? Number(quantityPerDose) : null,
      low_stock_threshold: lowStockThreshold ? Number(lowStockThreshold) : null,
      slots:
        scheduleType === "unscheduled"
          ? []
          : slots.map((s) => ({
              time_of_day: `${s.time_of_day}:00`,
              day_of_month: scheduleType === "monthly" ? Number(s.day_of_month) : undefined,
            })),
    };

    onSubmit(payload);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <TextInput
        label="Medicine name"
        required
        value={medicineName}
        onChange={(e) => setMedicineName(e.target.value)}
        placeholder="e.g. Metformin"
      />
      <TextInput
        label="Dosage"
        value={dosage}
        onChange={(e) => setDosage(e.target.value)}
        placeholder="e.g. 500mg"
        hint="Optional"
      />

      <ScheduleBuilder
        scheduleType={scheduleType}
        onScheduleTypeChange={setScheduleType}
        slots={slots}
        onSlotsChange={setSlots}
      />

      <div>
        <p className="mb-2 text-sm font-medium text-slate-700">Refill tracking</p>
        <p className="mb-2 text-xs text-slate-400">
          Leave blank to skip refill tracking for this medicine.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <TextInput
            label="Total pills"
            type="number"
            min={0}
            value={quantityTotal}
            onChange={(e) => setQuantityTotal(e.target.value)}
          />
          <TextInput
            label="Pills per dose"
            type="number"
            min={0}
            value={quantityPerDose}
            onChange={(e) => setQuantityPerDose(e.target.value)}
          />
          <TextInput
            label="Low-stock alert at"
            type="number"
            min={0}
            value={lowStockThreshold}
            onChange={(e) => setLowStockThreshold(e.target.value)}
          />
        </div>
      </div>

      {error && <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</div>}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={submitting}>
          Create reminder
        </Button>
      </div>
    </form>
  );
}
