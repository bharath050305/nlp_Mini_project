import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import clsx from "clsx";

interface WrapperProps {
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
  required?: boolean;
}

export function FieldWrapper({ label, error, hint, children, required }: WrapperProps) {
  return (
    <label className="block">
      {label && (
        <span className="mb-1 block text-sm font-medium text-slate-700">
          {label}
          {required && <span className="text-rose-500"> *</span>}
        </span>
      )}
      {children}
      {hint && !error && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
      {error && <p className="mt-1 text-xs text-rose-600">{error}</p>}
    </label>
  );
}

const inputBase =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm placeholder:text-slate-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  hint?: string;
};

export function TextInput({ label, error, hint, required, className, ...rest }: InputProps) {
  return (
    <FieldWrapper label={label} error={error} hint={hint} required={required}>
      <input className={clsx(inputBase, error && "border-rose-300", className)} {...rest} />
    </FieldWrapper>
  );
}

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
};

export function SelectInput({
  label,
  error,
  hint,
  required,
  className,
  children,
  ...rest
}: SelectProps) {
  return (
    <FieldWrapper label={label} error={error} hint={hint} required={required}>
      <select className={clsx(inputBase, error && "border-rose-300", className)} {...rest}>
        {children}
      </select>
    </FieldWrapper>
  );
}

export function TextAreaInput({
  label,
  error,
  hint,
  required,
  className,
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  error?: string;
  hint?: string;
}) {
  return (
    <FieldWrapper label={label} error={error} hint={hint} required={required}>
      <textarea className={clsx(inputBase, "min-h-[90px] resize-y", error && "border-rose-300", className)} {...rest} />
    </FieldWrapper>
  );
}
