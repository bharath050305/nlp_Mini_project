import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { usersApi } from "@/api/users";
import type { CreateUserPayload } from "@/api/users";
import type { Role } from "@/api/types";
import { getErrorMessage } from "@/api/client";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import { TextInput, SelectInput } from "@/components/ui/FormField";
import Button from "@/components/ui/Button";
import Table from "@/components/ui/Table";
import Badge from "@/components/ui/Badge";
import { formatDateTime } from "@/utils/format";

const roles: Role[] = ["doctor", "nurse", "staff", "patient"];

export default function StaffUserManagementPage() {
  const [roleFilter, setRoleFilter] = useState<Role | "">("");
  const queryClient = useQueryClient();

  const usersQuery = useQuery({
    queryKey: ["users", roleFilter],
    queryFn: () => usersApi.list(roleFilter || undefined),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateUserPayload>({ defaultValues: { role: "doctor" } });

  const createMutation = useMutation({
    mutationFn: (payload: CreateUserPayload) => usersApi.create(payload),
    onSuccess: (user) => {
      toast.success(`${user.role} account created for ${user.full_name}`);
      reset({ email: "", password: "", full_name: "", role: "doctor" });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-800">User Management</h1>
        <p className="text-sm text-slate-500">
          Create doctor, nurse, staff, or patient accounts and view existing users.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-700">Create account</h2>
          </CardHeader>
          <CardBody>
            <form
              onSubmit={handleSubmit((values) => createMutation.mutate(values))}
              className="flex flex-col gap-4"
            >
              <TextInput
                label="Full name"
                error={errors.full_name?.message}
                {...register("full_name", { required: "Required" })}
              />
              <TextInput
                label="Email"
                type="email"
                error={errors.email?.message}
                {...register("email", { required: "Required" })}
              />
              <TextInput
                label="Password"
                type="password"
                error={errors.password?.message}
                {...register("password", {
                  required: "Required",
                  minLength: { value: 8, message: "At least 8 characters" },
                })}
              />
              <SelectInput label="Role" {...register("role", { required: true })}>
                {roles.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </SelectInput>
              <Button type="submit" loading={isSubmitting} className="w-full">
                Create account
              </Button>
            </form>
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-slate-700">Existing users</h2>
            <SelectInput
              label=""
              className="w-40"
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value as Role | "")}
            >
              <option value="">All roles</option>
              {roles.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </SelectInput>
          </CardHeader>
          <CardBody>
            <Table
              rows={usersQuery.data ?? []}
              rowKey={(u) => u.id}
              emptyMessage="No users found."
              columns={[
                { header: "Name", render: (u) => u.full_name },
                { header: "Email", render: (u) => u.email },
                { header: "Role", render: (u) => <Badge tone="brand">{u.role}</Badge> },
                {
                  header: "Status",
                  render: (u) => (
                    <Badge tone={u.is_active ? "success" : "neutral"}>
                      {u.is_active ? "active" : "inactive"}
                    </Badge>
                  ),
                },
                { header: "Created", render: (u) => formatDateTime(u.created_at) },
              ]}
            />
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
