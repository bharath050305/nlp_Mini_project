import type { Role } from "@/api/types";

export interface NavItem {
  label: string;
  to: string;
  end?: boolean;
}

export const navByRole: Record<Role, NavItem[]> = {
  patient: [
    { label: "Dashboard", to: "/patient", end: true },
    { label: "Notifications", to: "/notifications" },
  ],
  doctor: [
    { label: "My Patients", to: "/doctor", end: true },
    { label: "Upload Consultation", to: "/doctor/transcripts/upload" },
    { label: "Notifications", to: "/notifications" },
  ],
  nurse: [
    { label: "My Patients", to: "/nurse", end: true },
    { label: "Notifications", to: "/notifications" },
  ],
  staff: [
    { label: "Users", to: "/staff", end: true },
    { label: "Assignments", to: "/staff/assignments" },
    { label: "Notifications", to: "/notifications" },
  ],
};

export const roleLandingPath: Record<Role, string> = {
  patient: "/patient",
  doctor: "/doctor",
  nurse: "/nurse",
  staff: "/staff",
};

export const roleLabel: Record<Role, string> = {
  patient: "Patient",
  doctor: "Doctor",
  nurse: "Nurse",
  staff: "Staff",
};
