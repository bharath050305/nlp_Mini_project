import type { ScheduleType } from "@/api/types";
import Button from "@/components/ui/Button";
import clsx from "clsx";

export interface SlotFormValue {
  time_of_day: string;
  day_of_month: string;
}

const scheduleOptions: { value: ScheduleType; label: string; description: string }[] = [
  { value: "daily", label: "Daily", description: "Repeats every day at chosen times" },
  { value: "monthly", label: "Monthly", description: "Repeats on chosen day(s) of month" },
  { value: "unscheduled", label: "Unscheduled", description: "As-needed, no fixed times" },
];

export default function ScheduleBuilder({
  scheduleType,
  onScheduleTypeChange,
  slots,
  onSlotsChange,
}: {
  scheduleType: ScheduleType;
  onScheduleTypeChange: (t: ScheduleType) => void;
  slots: SlotFormValue[];
  onSlotsChange: (slots: SlotFormValue[]) => void;
}) {
  function addSlot() {
    onSlotsChange([...slots, { time_of_day: "08:00", day_of_month: "1" }]);
  }

  function updateSlot(index: number, patch: Partial<SlotFormValue>) {
    onSlotsChange(slots.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  }

  function removeSlot(index: number) {
    onSlotsChange(slots.filter((_, i) => i !== index));
  }

  return (
    <div className="flex flex-col gap-3">
      <span className="block text-sm font-medium text-slate-700">Schedule</span>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {scheduleOptions.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onScheduleTypeChange(opt.value)}
            className={clsx(
              "rounded-lg border px-3 py-2 text-left transition-colors",
              scheduleType === opt.value
                ? "border-brand-400 bg-brand-50 ring-1 ring-brand-300"
                : "border-slate-200 bg-white hover:bg-slate-50",
            )}
          >
            <span className="block text-sm font-medium text-slate-700">{opt.label}</span>
            <span className="block text-xs text-slate-400">{opt.description}</span>
          </button>
        ))}
      </div>

      {scheduleType !== "unscheduled" && (
        <div className="flex flex-col gap-2 rounded-lg border border-slate-100 bg-slate-50/60 p-3">
          {slots.length === 0 && (
            <p className="text-xs text-slate-400">
              Add at least one {scheduleType === "monthly" ? "day + time" : "time"} below.
            </p>
          )}
          {slots.map((slot, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2">
              {scheduleType === "monthly" && (
                <label className="flex items-center gap-1 text-xs text-slate-500">
                  Day
                  <input
                    type="number"
                    min={1}
                    max={28}
                    value={slot.day_of_month}
                    onChange={(e) => updateSlot(i, { day_of_month: e.target.value })}
                    className="w-16 rounded-md border border-slate-200 px-2 py-1 text-sm"
                  />
                </label>
              )}
              <label className="flex items-center gap-1 text-xs text-slate-500">
                Time
                <input
                  type="time"
                  value={slot.time_of_day}
                  onChange={(e) => updateSlot(i, { time_of_day: e.target.value })}
                  className="rounded-md border border-slate-200 px-2 py-1 text-sm"
                />
              </label>
              <button
                type="button"
                onClick={() => removeSlot(i)}
                className="text-xs font-medium text-rose-500 hover:underline"
              >
                Remove
              </button>
            </div>
          ))}
          <Button type="button" variant="secondary" size="sm" onClick={addSlot} className="self-start">
            + Add {scheduleType === "monthly" ? "day & time" : "time"}
          </Button>
        </div>
      )}
    </div>
  );
}
