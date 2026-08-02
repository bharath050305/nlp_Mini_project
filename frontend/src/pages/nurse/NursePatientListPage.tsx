import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { patientsApi } from "@/api/patients";
import { FullPageSpinner } from "@/components/ui/Spinner";
import Card, { CardBody } from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/utils/format";

export default function NursePatientListPage() {
  const query = useQuery({ queryKey: ["patients"], queryFn: patientsApi.list });

  if (query.isLoading) return <FullPageSpinner />;
  const patients = query.data ?? [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-800">My Patients</h1>
        <p className="text-sm text-slate-500">Patients currently assigned to you.</p>
      </div>

      {patients.length === 0 ? (
        <EmptyState
          title="No patients assigned yet"
          description="Ask staff to assign a patient to you to see them here."
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {patients.map((p) => (
            <Link key={p.id} to={`/nurse/patients/${p.id}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardBody>
                  <p className="font-medium text-slate-800">{p.name}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    DOB: {p.date_of_birth ? formatDate(p.date_of_birth) : "unknown"}
                  </p>
                  {p.phone && <p className="text-xs text-slate-400">{p.phone}</p>}
                </CardBody>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
