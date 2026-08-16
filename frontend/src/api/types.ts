// Shared types mirroring backend/schemas_api.py

export type Role = "doctor" | "patient" | "nurse" | "staff";

export interface UserOut {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface PatientOut {
  id: number;
  user_id: number | null;
  name: string;
  date_of_birth: string | null;
  phone: string | null;
  created_at: string;
}

export type AssignmentRole = "doctor" | "nurse";

export interface AssignmentOut {
  id: number;
  patient_id: number;
  staff_user_id: number;
  role_at_assignment: AssignmentRole;
  assigned_at: string;
  active: boolean;
}

export interface ReportOut {
  id: number;
  patient_id: number;
  filename: string;
  source_type: string;
  created_at: string;
}

export interface EntitiesJson {
  diseases: string[];
  medicines: string[];
  symptoms: string[];
  lab_tests: string[];
  lab_values: string[];
  dosages: string[];
  dates: string[];
}

export interface EvidenceItem {
  claim: string;
  evidence: string;
  reference_range?: string | null;
}

export interface SummaryJson {
  patient_summary: string;
  key_findings: string[];
  abnormal_values: string[];
  recommendations: string[];
  evidence: EvidenceItem[];
  confidence: string;
}

export interface ReportDetailOut extends ReportOut {
  raw_text: string;
  summary_json: string | null;
  entities_json: string | null;
}

export interface TimelineEvent {
  report_filename: string;
  uploaded_at: string;
  diseases: string[];
  medicines: string[];
  lab_values: string[];
  new_since_previous: string[];
}

export type Autonomy = "A0" | "A1" | "A2";
export type RiskTier = "R0" | "R1" | "R2" | "R3";
export type ExecStatus = "pending" | "running" | "done" | "failed" | "skipped";

export interface ExecutionLogEntry {
  agent_name: string;
  status: ExecStatus;
  detail: string | null;
  duration_ms: number | null;
  autonomy: Autonomy | null;
  risk_tier: RiskTier | null;
}

export interface PlanTask {
  task_type: string;
  description: string;
  payload: Record<string, unknown>;
}

export interface Plan {
  user_request: string;
  tasks: PlanTask[];
}

export interface QAResult {
  question: string;
  answer: string;
  retrieved_chunks: string[];
  confidence: "low" | "medium" | "high";
}

export interface DrugInteractionWarning {
  drug_a: string;
  drug_b: string;
  severity: "moderate" | "major";
  note: string;
}

export interface TriageResult {
  level: "low" | "medium" | "high" | "critical";
  reasons: string[];
}

export interface CriticResult {
  supported: boolean;
  unsupported_claims: string[];
  note: string;
}

export type ConsensusStatus =
  | "unanimous"
  | "weighted_consensus"
  | "disputed"
  | "insufficient_evidence"
  | "safety_vetoed";

export interface EvidenceCitation {
  source_type: string;
  resource_id: string;
  snippet: string;
  confidence_score: number;
}

export interface DifferentialCandidate {
  condition_name: string;
  icd10_code: string | null;
  probability_score: number;
  supporting_evidence: EvidenceCitation[];
  contradicting_evidence: string[];
  recommended_tests: string[];
}

export interface LabTrajectoryPoint {
  test_name: string;
  date_or_seq: string;
  value: number;
  unit: string;
  is_abnormal: boolean;
}

export interface LabTrajectory {
  test_name: string;
  readings: LabTrajectoryPoint[];
  slope_per_interval: number;
  trend_direction: "rising" | "falling" | "stable" | "critical_drop" | "critical_spike";
  clinical_alert: string | null;
}

export interface ConsensusEvaluation {
  consensus_id: string;
  status: ConsensusStatus;
  primary_candidate: DifferentialCandidate | null;
  secondary_candidates: DifferentialCandidate[];
  agreement_entropy: number;
  agent_votes: Record<string, number>;
  critic_notes: string;
  safety_veto_triggered: boolean;
  veto_reason: string | null;
  missing_information: string[];
  human_approval_required: boolean;
  approved_by: string | null;
}

export interface AgentRunResult {
  final_response: string;
  plan: Plan;
  execution_log: ExecutionLogEntry[];
  entities: EntitiesJson | null;
  summary: SummaryJson | null;
  qa_results: QAResult[];
  reminders: ReminderOut[];
  report_file_path: string | null;
  interaction_warnings: DrugInteractionWarning[];
  timeline: TimelineEvent[];
  // v5: Supervisor / Triage / Critic layer
  triage: TriageResult | null;
  verification: CriticResult | null;
  requires_human_review: boolean;
  escalation_reason: string | null;
  // v6: Multi-Agent Consensus & Trajectory Decision Support
  consensus?: ConsensusEvaluation | null;
  lab_trajectories?: LabTrajectory[];
}

export type ScheduleType = "daily" | "monthly" | "unscheduled";

export interface ReminderSlot {
  id: number;
  time_of_day: string;
  day_of_month: number | null;
}

export interface ReminderSlotInput {
  time_of_day: string;
  day_of_month?: number | null;
}

export interface ReminderOut {
  id: number;
  patient_id: number;
  medicine_name: string;
  dosage: string | null;
  schedule_type: ScheduleType;
  quantity_total: number | null;
  quantity_remaining: number | null;
  quantity_per_dose: number | null;
  low_stock_threshold: number | null;
  refill_alert_sent: boolean;
  active: boolean;
  created_at: string;
  slots: ReminderSlot[];
}

export type NotificationType =
  | "dose_reminder"
  | "refill_alert"
  | "missed_dose"
  | "assignment"
  | "system";
export type NotificationStatus = "pending" | "sent" | "failed" | "read";

export interface NotificationOut {
  id: number;
  type: NotificationType;
  title: string;
  body: string;
  channel: string;
  status: NotificationStatus;
  related_reminder_id: number | null;
  related_transcript_id: number | null;
  created_at: string;
  sent_at: string | null;
  read_at: string | null;
}

export type TranscriptStatus =
  | "uploaded"
  | "transcribing"
  | "transcribed"
  | "structuring"
  | "draft_ready"
  | "finalized"
  | "failed";

export interface TranscriptOut {
  id: number;
  patient_id: number;
  doctor_id: number;
  audio_filename: string;
  status: TranscriptStatus;
  duration_seconds: number | null;
  error_detail: string | null;
  created_at: string;
  updated_at: string;
}

export type SoapStatus = "draft" | "finalized";

export interface SoapNoteOut {
  id: number;
  transcript_id: number;
  patient_id: number;
  subjective: string | null;
  objective: string | null;
  assessment: string | null;
  plan: string | null;
  status: SoapStatus;
  linked_report_id: number | null;
  created_at: string;
  finalized_at: string | null;
}

export interface ApiErrorBody {
  detail: string;
}

// -- Analytics (v4) ----------------------------------------------------------
export interface LabTrendPoint {
  report_id: number;
  report_date: string;
  report_filename: string;
  label: string;
  raw_value: string;
  numeric_value: number;
  is_abnormal: boolean;
  reference_range: string;
}

export interface ReminderAdherence {
  reminder_id: number;
  medicine_name: string;
  taken: number;
  skipped: number;
  missed: number;
  adherence_pct: number;
}

export type AbnormalTrend = "up" | "down" | "flat" | "unknown";

export interface AnalyticsSummary {
  total_reports: number;
  total_abnormal_readings: number;
  abnormal_trend: AbnormalTrend;
  active_reminders: number;
  doses_missed_this_week: number;
}

// -- Human-in-the-loop approvals (v5) -----------------------------------------
export type ApprovalType =
  | "triage"
  | "verification"
  | "interaction"
  | "safety_veto"
  | "consensus_dispute"
  | "lab_trajectory";
export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface ApprovalOut {
  id: number;
  patient_id: number;
  type: ApprovalType;
  summary: string;
  detail_json: string;
  status: ApprovalStatus;
  reviewed_by: number | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_at: string;
}

// -- Patient Digital Twin (v5) -------------------------------------------------
export interface DigitalTwin {
  patient_id: number;
  patient_name: string;
  latest_report_filename: string | null;
  latest_report_date: string | null;
  total_reports: number;
  diseases: string[];
  medicines: string[];
  symptoms: string[];
  triage_level: "low" | "medium" | "high" | "critical";
  triage_reasons: string[];
  active_reminders: number;
  overall_adherence_pct: number;
  doses_missed_this_week: number;
  timeline_event_count: number;
}

// -- Agent Registry (v5) --------------------------------------------------------
export interface AgentCapabilityOut {
  name: string;
  module: string;
  description: string;
  reads: string[];
  writes: string[];
  risk: string;
  autonomy: string;
}
