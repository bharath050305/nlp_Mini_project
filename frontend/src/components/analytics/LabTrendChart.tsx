import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { LabTrendPoint } from "@/api/types";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/utils/format";

interface ChartDatum {
  date: string;
  rawDate: string;
  value: number;
  isAbnormal: boolean;
  rawValue: string;
  filename: string;
}

function AbnormalDot(props: any) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null) return null;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={payload.isAbnormal ? 5 : 3.5}
      fill={payload.isAbnormal ? "#e11d48" : "#2f93ab"}
      stroke="white"
      strokeWidth={1.5}
    />
  );
}

function LabTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const point: ChartDatum = payload[0].payload;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-slate-700">{point.rawValue}</p>
      <p className="text-slate-400">{point.filename}</p>
      {point.isAbnormal && <p className="mt-1 font-medium text-rose-600">Outside reference range</p>}
    </div>
  );
}

/** One small line chart per distinct lab label — a wide pivot would
 * collide when a single report yields multiple readings under the same
 * label (the regex-based matcher isn't test-name-aware), so small
 * multiples keep every point visible and honest. */
export default function LabTrendChart({ points }: { points: LabTrendPoint[] }) {
  if (points.length === 0) {
    return (
      <EmptyState
        title="No lab trend data yet"
        description="Upload at least one report with recognizable lab values to see trends here."
      />
    );
  }

  const byLabel = new Map<string, LabTrendPoint[]>();
  for (const point of points) {
    const list = byLabel.get(point.label) ?? [];
    list.push(point);
    byLabel.set(point.label, list);
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {Array.from(byLabel.entries()).map(([label, series]) => {
        const data: ChartDatum[] = series
          .slice()
          .sort((a, b) => a.report_date.localeCompare(b.report_date))
          .map((p) => ({
            date: formatDate(p.report_date),
            rawDate: p.report_date,
            value: p.numeric_value,
            isAbnormal: p.is_abnormal,
            rawValue: p.raw_value,
            filename: p.report_filename,
          }));
        const referenceRange = series[0].reference_range;
        const [low, high] = referenceRange.split("-").map(Number);

        return (
          <Card key={label}>
            <CardHeader className="flex items-center justify-between">
              <span className="text-sm font-semibold text-slate-700">{label}</span>
              <span className="text-xs text-slate-400">Reference: {referenceRange}</span>
            </CardHeader>
            <CardBody>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                    <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} width={40} />
                    <Tooltip content={<LabTooltip />} />
                    {!Number.isNaN(low) && (
                      <ReferenceLine y={low} stroke="#cbd5e1" strokeDasharray="4 4" />
                    )}
                    {!Number.isNaN(high) && (
                      <ReferenceLine y={high} stroke="#cbd5e1" strokeDasharray="4 4" />
                    )}
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#2f93ab"
                      strokeWidth={2}
                      dot={<AbnormalDot />}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardBody>
          </Card>
        );
      })}
    </div>
  );
}
