import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/api/analytics";
import { FullPageSpinner } from "@/components/ui/Spinner";
import StatTile from "./StatTile";
import LabTrendChart from "./LabTrendChart";
import AdherenceChart from "./AdherenceChart";

const trendLabel: Record<string, string> = {
  up: "Rising",
  down: "Falling",
  flat: "Stable",
  unknown: "Not enough data",
};

export default function AnalyticsPanel({ patientId }: { patientId: number }) {
  const summaryQuery = useQuery({
    queryKey: ["analytics", "summary", patientId],
    queryFn: () => analyticsApi.summary(patientId),
  });
  const labTrendsQuery = useQuery({
    queryKey: ["analytics", "lab-trends", patientId],
    queryFn: () => analyticsApi.labTrends(patientId),
  });
  const adherenceQuery = useQuery({
    queryKey: ["analytics", "adherence", patientId],
    queryFn: () => analyticsApi.adherence(patientId),
  });

  if (summaryQuery.isLoading) return <FullPageSpinner />;
  const summary = summaryQuery.data;

  return (
    <div className="flex flex-col gap-5">
      {summary && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatTile label="Reports on file" value={summary.total_reports} />
          <StatTile
            label="Abnormal readings"
            value={summary.total_abnormal_readings}
            hint={trendLabel[summary.abnormal_trend]}
            tone={summary.total_abnormal_readings > 0 ? "warning" : "default"}
          />
          <StatTile label="Active reminders" value={summary.active_reminders} />
          <StatTile
            label="Doses missed this week"
            value={summary.doses_missed_this_week}
            tone={summary.doses_missed_this_week > 0 ? "danger" : "default"}
          />
        </div>
      )}

      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Lab value trends</h3>
        {labTrendsQuery.isLoading ? <FullPageSpinner /> : <LabTrendChart points={labTrendsQuery.data ?? []} />}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Reminder adherence</h3>
        {adherenceQuery.isLoading ? <FullPageSpinner /> : <AdherenceChart data={adherenceQuery.data ?? []} />}
      </div>
    </div>
  );
}
