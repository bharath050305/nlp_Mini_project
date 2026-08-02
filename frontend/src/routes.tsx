import { Navigate, createBrowserRouter } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import RoleGuard, { RequireAuth } from "@/components/layout/RoleGuard";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import PatientDashboard from "@/pages/patient/PatientDashboard";
import DoctorPatientListPage from "@/pages/doctor/DoctorPatientListPage";
import PatientDetailPage from "@/pages/doctor/PatientDetailPage";
import TranscriptUploadPage from "@/pages/doctor/TranscriptUploadPage";
import TranscriptReviewPage from "@/pages/doctor/TranscriptReviewPage";
import NursePatientListPage from "@/pages/nurse/NursePatientListPage";
import NursePatientDetailPage from "@/pages/nurse/NursePatientDetailPage";
import StaffUserManagementPage from "@/pages/staff/StaffUserManagementPage";
import AssignmentManagementPage from "@/pages/staff/AssignmentManagementPage";
import NotificationsPage from "@/pages/shared/NotificationsPage";
import RootRedirect from "@/pages/RootRedirect";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <RootRedirect /> },
          { path: "/notifications", element: <NotificationsPage /> },
          {
            element: <RoleGuard allow={["patient"]} />,
            children: [{ path: "/patient", element: <PatientDashboard /> }],
          },
          {
            element: <RoleGuard allow={["doctor"]} />,
            children: [
              { path: "/doctor", element: <DoctorPatientListPage /> },
              { path: "/doctor/patients/:patientId", element: <PatientDetailPage /> },
              { path: "/doctor/transcripts/upload", element: <TranscriptUploadPage /> },
              { path: "/doctor/transcripts/:transcriptId", element: <TranscriptReviewPage /> },
            ],
          },
          {
            element: <RoleGuard allow={["nurse"]} />,
            children: [
              { path: "/nurse", element: <NursePatientListPage /> },
              { path: "/nurse/patients/:patientId", element: <NursePatientDetailPage /> },
            ],
          },
          {
            element: <RoleGuard allow={["staff"]} />,
            children: [
              { path: "/staff", element: <StaffUserManagementPage /> },
              { path: "/staff/assignments", element: <AssignmentManagementPage /> },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
