import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage } from "@/api/client";
import { TextInput } from "@/components/ui/FormField";
import Button from "@/components/ui/Button";

interface FormValues {
  full_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>();

  async function onSubmit(values: FormValues) {
    setSubmitError(null);
    try {
      await registerUser({
        email: values.email,
        password: values.password,
        full_name: values.full_name,
      });
      toast.success("Account created — welcome to MediAgent!");
      navigate("/patient", { replace: true });
    } catch (err) {
      setSubmitError(getErrorMessage(err));
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 via-white to-slate-50 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-xl font-bold text-white">
            M
          </div>
          <h1 className="text-2xl font-semibold text-slate-800">Create your account</h1>
          <p className="mt-1 text-center text-sm text-slate-500">
            Public registration creates a patient account. Staff can create doctor, nurse, or
            staff accounts.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <TextInput
              label="Full name"
              autoComplete="name"
              placeholder="Jane Doe"
              error={errors.full_name?.message}
              {...register("full_name", { required: "Full name is required" })}
            />
            <TextInput
              label="Email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              error={errors.email?.message}
              {...register("email", { required: "Email is required" })}
            />
            <TextInput
              label="Password"
              type="password"
              autoComplete="new-password"
              placeholder="••••••••"
              error={errors.password?.message}
              {...register("password", {
                required: "Password is required",
                minLength: { value: 8, message: "At least 8 characters" },
              })}
            />
            <TextInput
              label="Confirm password"
              type="password"
              autoComplete="new-password"
              placeholder="••••••••"
              error={errors.confirm_password?.message}
              {...register("confirm_password", {
                required: "Please confirm your password",
                validate: (v) => v === watch("password") || "Passwords do not match",
              })}
            />

            {submitError && (
              <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">
                {submitError}
              </div>
            )}

            <Button type="submit" loading={isSubmitting} className="mt-2 w-full" size="lg">
              Create account
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-brand-600 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
