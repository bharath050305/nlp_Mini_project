import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { patientsApi } from "@/api/patients";
import type { CreatePatientPayload } from "@/api/patients";
import { usersApi } from "@/api/users";
import { assignmentsApi } from "@/api/assignments";
import type { AssignmentRole } from "@/api/types";
import { getErrorMessage } from "@/api/client";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import { TextInput, SelectInput } from "@/components/ui/FormField";
import Button from "@/components/ui/Button";
import Table from "@/components/ui/Table";
import Badge from "@/components/ui/Badge";
import { formatDateTime } from "@/utils/format";

interface AssignmentFormValues {
  patient_id: string;
  role_at_assignment: AssignmentRole;
  staff_user_id: string;
}

export default function AssignmentManagementPage() {
  const queryClient = useQueryClient();

  const patientsQuery = useQuery({ queryKey: ["patients"], queryFn: patientsApi.list });
  const doctorsQuery = useQuery({
    queryKey: ["users", "doctor"],
    queryFn: () => usersApi.list("doctor"),
  });
  const nursesQuery = useQuery({
    queryKey: ["users", "nurse"],
    queryFn: () => usersApi.list("nurse"),
  });

  // The backend only supports listing assignments for a single patient at a
  // time, so we fan out one query per patient and flatten the results.
  const patientIds = (patientsQuery.data ?? []).map((p) => p.id);
  const assignmentsQueries = useQueries({
    queries: patientIds.map((id) => ({
      queryKey: ["assignments", id],
      queryFn: () => assignmentsApi.listForPatient(id),
      enabled: patientIds.length > 0,
    })),
  });
  const assignmentsLoading = assignmentsQueries.some((q) => q.isLoading);
  const allAssignments = useMemo(
    () => assignmentsQueries.flatMap((q) => q.data ?? []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [assignmentsQueries.map((q) => q.dataUpdatedAt).join(",")],
  );

  const patients = patientsQuery.data ?? [];
  const patientNameById = useMemo(
    () => new Map(patients.map((p) => [p.id, p.name])),
    [patients],
  );

  // --- Walk-in patient form ---
  const patientForm = useForm<{ name: string; date_of_birth: string; phone: string }>();
  const createPatientMutation = useMutation({
    mutationFn: (payload: CreatePatientPayload) => patientsApi.create(payload),
    onSuccess: (p) => {
      toast.success(`Patient chart created for ${p.name}`);
      patientForm.reset();
      queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // --- Assignment form ---
  const assignForm = useForm<AssignmentFormValues>({
    defaultValues: { role_at_assignment: "doctor" },
  });
  const watchedRole = assignForm.watch("role_at_assignment");
  const staffOptions = watchedRole === "doctor" ? doctorsQuery.data ?? [] : nursesQuery.data ?? [];

  const createAssignmentMutation = useMutation({
    mutationFn: (values: AssignmentFormValues) =>
      assignmentsApi.create({
        patient_id: Number(values.patient_id),
        staff_user_id: Number(values.staff_user_id),
        role_at_assignment: values.role_at_assignment,
      }),
    onSuccess: () => {
      toast.success("Assignment created");
      assignForm.reset({ role_at_assignment: "doctor", patient_id: "", staff_user_id: "" });
      queryClient.invalidateQueries({ queryKey: ["assignments"] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const removeAssignmentMutation = useMutation({
    mutationFn: (id: number) => assignmentsApi.remove(id),
    onSuccess: () => {
      toast.success("Assignment removed");
      queryClient.invalidateQueries({ queryKey: ["assignments"] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-800">Care Assignments</h1>
        <p className="text-sm text-slate-500">
          Assign doctors and nurses to patients, and chart walk-in patients.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-1">
          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-slate-700">Chart a walk-in patient</h2>
            </CardHeader>
            <CardBody>
              <form
                onSubmit={patientForm.handleSubmit((values) =>
                  createPatientMutation.mutate({
                    name: values.name,
                    date_of_birth: values.date_of_birth || null,
                    phone: values.phone || null,
                  }),
                )}
                className="flex flex-col gap-4"
              >
                <TextInput
                  label="Name"
                  error={patientForm.formState.errors.name?.message}
                  {...patientForm.register("name", { required: "Required" })}
                />
                <TextInput
                  label="Date of birth"
                  type="date"
                  {...patientForm.register("date_of_birth")}
                />
                <TextInput label="Phone" {...patientForm.register("phone")} />
                <Button type="submit" loading={createPatientMutation.isPending} className="w-full">
                  Create patient chart
                </Button>
              </form>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-slate-700">New assignment</h2>
            </CardHeader>
            <CardBody>
              <form
                onSubmit={assignForm.handleSubmit((values) =>
                  createAssignmentMutation.mutate(values),
                )}
                className="flex flex-col gap-4"
              >
                <SelectInput
                  label="Patient"
                  error={assignForm.formState.errors.patient_id?.message}
                  {...assignForm.register("patient_id", { required: "Required" })}
                >
                  <option value="">Select a patient...</option>
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </SelectInput>
                <SelectInput label="Role" {...assignForm.register("role_at_assignment")}>
                  <option value="doctor">Doctor</option>
                  <option value="nurse">Nurse</option>
                </SelectInput>
                <SelectInput
                  label={watchedRole === "doctor" ? "Doctor" : "Nurse"}
                  error={assignForm.formState.errors.staff_user_id?.message}
                  {...assignForm.register("staff_user_id", { required: "Required" })}
                >
                  <option value="">Select...</option>
                  {staffOptions.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name}
                    </option>
                  ))}
                </SelectInput>
                <Button
                  type="submit"
                  loading={createAssignmentMutation.isPending}
                  className="w-full"
                >
                  Create assignment
                </Button>
              </form>
            </CardBody>
          </Card>
        </div>

        <Card className="lg:col-span-2">
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-700">All assignments</h2>
          </CardHeader>
          <CardBody>
            <Table
              rows={assignmentsQuery.data ?? []}
              rowKey={(a) => a.id}
              emptyMessage="No assignments yet."
              columns={[
                {
                  header: "Patient",
                  render: (a) => patientNameById.get(a.patient_id) ?? `#${a.patient_id}`,
                },
                {
                  header: "Role",
                  render: (a) => <Badge tone="brand">{a.role_at_assignment}</Badge>,
                },
                {
                  header: "Status",
                  render: (a) => (
                    <Badge tone={a.active ? "success" : "neutral"}>
                      {a.active ? "active" : "inactive"}
                    </Badge>
                  ),
                },
                { header: "Assigned", render: (a) => formatDateTime(a.assigned_at) },
                {
                  header: "",
                  render: (a) => (
                    <button
                      onClick={() => {
                        if (confirm("Remove this assignment?")) {
                          removeAssignmentMutation.mutate(a.id);
                        }
                      }}
                      className="text-xs font-medium text-rose-500 hover:underline"
                    >
                      Remove
                    </button>
                  ),
                },
              ]}
            />
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
