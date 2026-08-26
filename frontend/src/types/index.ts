export type Role =
  | 'ADMIN'
  | 'GRC_ANALYST'
  | 'SECURITY_ANALYST'
  | 'AUDITOR'
  | 'MANAGER'
  | 'VIEWER';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  organization_id: number;
  created_at: string;
  updated_at: string;
  permissions?: string[];
}

export interface Organization {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  organization_id: number;
  actor_id?: number;
  actor_email: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  status: string;
  ip_address?: string;
  user_agent?: string;
  details?: Record<string, any>;
}

export interface HealthStatus {
  status: string;
  app: string;
  version: string;
  environment: string;
}

// Phase 2 Types
export interface FrameworkSubcategory {
  id: number;
  identifier: string;
  title: string;
  description: string;
  display_order: number;
}

export interface FrameworkCategory {
  id: number;
  identifier: string;
  name: string;
  description?: string;
  display_order: number;
  subcategories?: FrameworkSubcategory[];
}

export interface FrameworkFunction {
  id: number;
  identifier: string;
  name: string;
  description?: string;
  display_order: number;
  categories?: FrameworkCategory[];
}

export interface Framework {
  id: number;
  identifier: string;
  name: string;
  version: string;
  description?: string;
  created_at: string;
  total_functions?: number;
  total_categories?: number;
  total_subcategories?: number;
  functions?: FrameworkFunction[];
}

export type ImplementationStatus =
  | 'NOT_STARTED'
  | 'IN_PROGRESS'
  | 'PARTIALLY_IMPLEMENTED'
  | 'IMPLEMENTED'
  | 'NOT_APPLICABLE'
  | 'NEEDS_REVIEW';

export type Priority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface OrganizationControl {
  id: number;
  organization_id: number;
  subcategory_id: number;
  status: ImplementationStatus;
  priority: Priority;
  owner_id?: number;
  target_date?: string;
  review_date?: string;
  implementation_statement?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  subcategory?: FrameworkSubcategory;
  owner?: User;
  function_identifier?: string;
  function_name?: string;
  category_identifier?: string;
  category_name?: string;
  mapped_policies_count?: number;
}

export interface FunctionProgress {
  name: string;
  total: number;
  implemented: number;
  partially_implemented: number;
  in_progress: number;
  not_started: number;
  score_pct: number;
}

export interface FrameworkProgress {
  framework_id: number;
  framework_identifier: string;
  framework_name: string;
  total_controls: number;
  implemented_count: number;
  partially_implemented_count: number;
  in_progress_count: number;
  not_started_count: number;
  not_applicable_count: number;
  needs_review_count: number;
  compliance_score_pct: number;
  by_function: Record<string, FunctionProgress>;
}

export type PolicyStatus = 'DRAFT' | 'UNDER_REVIEW' | 'APPROVED' | 'PUBLISHED' | 'ARCHIVED';

export type PolicyType =
  | 'ACCESS_CONTROL'
  | 'INFORMATION_SECURITY'
  | 'INCIDENT_RESPONSE'
  | 'DATA_PROTECTION'
  | 'RISK_MANAGEMENT'
  | 'BUSINESS_CONTINUITY'
  | 'VENDOR_MANAGEMENT'
  | 'ACCEPTABLE_USE'
  | 'CRYPTOGRAPHY'
  | 'CHANGE_MANAGEMENT'
  | 'OTHER';

export interface PolicyVersion {
  id: number;
  policy_id: number;
  version_number: number;
  content: string;
  change_summary: string;
  created_by_id?: number;
  created_at: string;
  created_by?: User;
}

export interface Policy {
  id: number;
  organization_id: number;
  title: string;
  description?: string;
  policy_type: PolicyType;
  status: PolicyStatus;
  owner_id?: number;
  effective_date?: string;
  review_date?: string;
  created_at: string;
  updated_at: string;
  owner?: User;
  current_version?: PolicyVersion;
  total_versions: number;
  versions?: PolicyVersion[];
  mapped_subcategories: FrameworkSubcategory[];
}

// Phase 3 Evidence Types
export type EvidenceType =
  | 'DOCUMENT'
  | 'CONFIGURATION'
  | 'LOG_EXPORT'
  | 'SCREENSHOT'
  | 'POLICY_DOCUMENT'
  | 'AUDIT_REPORT'
  | 'OTHER';

export type EvidenceStatus =
  | 'UPLOADED'
  | 'UNDER_REVIEW'
  | 'ACCEPTED'
  | 'REJECTED'
  | 'SUPERSEDED';

export type ReviewDecision = 'ACCEPT' | 'REJECT';

export interface EvidenceRequirement {
  id: number;
  organization_id: number;
  organization_control_id: number;
  title: string;
  description?: string;
  evidence_type: EvidenceType;
  is_required: boolean;
  guidance?: string;
  created_by_id?: number;
  created_at: string;
  updated_at: string;
  created_by?: User;
  items_count: number;
  accepted_items_count: number;
}

export interface EvidenceReview {
  id: number;
  organization_id: number;
  evidence_id: number;
  reviewer_id?: number;
  decision: ReviewDecision;
  review_notes?: string;
  rejection_reason?: string;
  reviewed_at: string;
  reviewer?: User;
}

export interface EvidenceItem {
  id: number;
  organization_id: number;
  organization_control_id: number;
  evidence_requirement_id?: number;
  uploaded_by_id?: number;
  title: string;
  description?: string;
  original_filename: string;
  stored_filename: string;
  file_extension: string;
  content_type: string;
  file_size: number;
  sha256_hash: string;
  status: EvidenceStatus;
  superseded_by_id?: number;
  created_at: string;
  updated_at: string;
  uploaded_by?: User;
  requirement_title?: string;
  control_identifier?: string;
  control_title?: string;
  latest_review?: EvidenceReview;
  reviews?: EvidenceReview[];
}

export interface ControlEvidenceSummary {
  organization_control_id: number;
  total_requirements: number;
  required_count: number;
  submitted_count: number;
  accepted_count: number;
  rejected_count: number;
  pending_count: number;
  superseded_count: number;
  evidence_coverage_pct: number;
}

export interface OrganizationEvidenceStats {
  total_evidence_items: number;
  accepted_count: number;
  pending_review_count: number;
  rejected_count: number;
  uploaded_count: number;
  superseded_count: number;
  overall_coverage_pct: number;
  controls_missing_required_evidence: number;
}

// Phase 4: Assessments, Findings & Remediation Types
export type AssessmentMethod =
  | 'EXAMINATION'
  | 'INTERVIEW'
  | 'TESTING'
  | 'AUTOMATED_VERIFICATION'
  | 'COMBINED';

export type AssessmentStatus =
  | 'DRAFT'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'SUPERSEDED';

export type AssessmentConclusion =
  | 'EFFECTIVE'
  | 'PARTIALLY_EFFECTIVE'
  | 'INEFFECTIVE'
  | 'NOT_ASSESSED';

export interface AssessmentEvidence {
  id: number;
  organization_id: number;
  assessment_id: number;
  evidence_id: number;
  created_by_id?: number;
  created_at: string;
  evidence?: EvidenceItem;
}

export interface Assessment {
  id: number;
  organization_id: number;
  organization_control_id: number;
  assessor_id?: number;
  assessment_method: AssessmentMethod;
  assessment_scope?: string;
  assessment_date: string;
  status: AssessmentStatus;
  conclusion: AssessmentConclusion;
  summary?: string;
  limitations?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  assessor?: User;
  control_identifier?: string;
  control_title?: string;
  evidence_count: number;
  findings_count: number;
  evidence_links?: AssessmentEvidence[];
}

export interface AssessmentStats {
  total_assessments: number;
  draft_count: number;
  in_progress_count: number;
  completed_count: number;
  superseded_count: number;
  effective_count: number;
  partially_effective_count: number;
  ineffective_count: number;
  not_assessed_count: number;
}

export type FindingType =
  | 'CONTROL_GAP'
  | 'EVIDENCE_GAP'
  | 'POLICY_GAP'
  | 'PROCESS_GAP'
  | 'TECHNICAL_GAP'
  | 'OTHER';

export type FindingSeverity =
  | 'CRITICAL'
  | 'HIGH'
  | 'MEDIUM'
  | 'LOW'
  | 'INFORMATIONAL';

export type FindingStatus =
  | 'OPEN'
  | 'IN_REMEDIATION'
  | 'PENDING_VALIDATION'
  | 'RESOLVED'
  | 'ACCEPTED_RISK'
  | 'CLOSED';

export interface FindingEvidence {
  id: number;
  organization_id: number;
  finding_id: number;
  evidence_id: number;
  created_by_id?: number;
  created_at: string;
  evidence?: EvidenceItem;
}

export interface Finding {
  id: number;
  organization_id: number;
  organization_control_id: number;
  assessment_id?: number;
  title: string;
  description: string;
  finding_type: FindingType;
  severity: FindingSeverity;
  impact: number;
  likelihood: number;
  risk_score: number;
  risk_band: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  recommendation: string;
  root_cause?: string;
  owner_id?: number;
  due_date?: string;
  overdue_status: 'ON_TRACK' | 'DUE_SOON' | 'OVERDUE' | 'NO_DUE_DATE' | 'COMPLETED';
  status: FindingStatus;
  remediation_plan?: string;
  remediation_notes?: string;
  resolution?: string;
  resolved_at?: string;
  resolved_by_id?: number;
  closed_at?: string;
  closed_by_id?: number;
  risk_acceptance_justification?: string;
  risk_accepted_at?: string;
  risk_accepted_by_id?: number;
  risk_acceptance_expiry?: string;
  created_by_id?: number;
  created_at: string;
  updated_at: string;
  owner?: User;
  created_by?: User;
  resolved_by?: User;
  closed_by?: User;
  risk_accepted_by?: User;
  control_identifier?: string;
  control_title?: string;
  assessment_summary?: string;
  evidence_count: number;
  evidence_links?: FindingEvidence[];
}

export interface FindingStats {
  total_findings: number;
  open_count: number;
  in_remediation_count: number;
  pending_validation_count: number;
  resolved_count: number;
  accepted_risk_count: number;
  closed_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  informational_count: number;
  overdue_count: number;
  due_soon_count: number;
  on_track_count: number;
}

// Phase 5: Risk Management, Exceptions & Executive Governance Types
export type RiskCategory =
  | 'CYBERSECURITY'
  | 'COMPLIANCE'
  | 'OPERATIONAL'
  | 'FINANCIAL'
  | 'STRATEGIC'
  | 'REPUTATIONAL'
  | 'THIRD_PARTY'
  | 'LEGAL';

export type RiskSource =
  | 'INTERNAL_AUDIT'
  | 'EXTERNAL_AUDIT'
  | 'THREAT_INTELLIGENCE'
  | 'VULNERABILITY_ASSESSMENT'
  | 'INCIDENT'
  | 'VENDOR_ASSESSMENT'
  | 'REGULATORY_CHANGE'
  | 'BUSINESS_OPERATION';

export type RiskStatus =
  | 'IDENTIFIED'
  | 'ASSESSED'
  | 'TREATMENT_PLANNED'
  | 'MITIGATING'
  | 'MONITORING'
  | 'ACCEPTED'
  | 'CLOSED';

export type RiskTreatmentStrategy =
  | 'MITIGATE'
  | 'TRANSFER'
  | 'AVOID'
  | 'ACCEPT'
  | 'NOT_SPECIFIED';

export interface RiskControlLink {
  id: number;
  organization_id: number;
  risk_id: number;
  organization_control_id: number;
  created_by_id?: number;
  created_at: string;
  organization_control?: OrganizationControl;
}

export interface RiskFindingLink {
  id: number;
  organization_id: number;
  risk_id: number;
  finding_id: number;
  created_by_id?: number;
  created_at: string;
  finding?: Finding;
}

export interface Risk {
  id: number;
  organization_id: number;
  title: string;
  description: string;
  risk_category: RiskCategory;
  risk_source: RiskSource;
  owner_id?: number;
  inherent_impact: number;
  inherent_likelihood: number;
  inherent_score: number;
  inherent_band: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  residual_impact?: number;
  residual_likelihood?: number;
  residual_score?: number;
  residual_band?: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  target_risk_band: string;
  appetite_status: 'WITHIN_APPETITE' | 'NEAR_LIMIT' | 'ABOVE_APPETITE';
  status: RiskStatus;
  treatment_strategy: RiskTreatmentStrategy;
  treatment_plan?: string;
  treatment_owner_id?: number;
  treatment_due_date?: string;
  treatment_overdue_status: 'ON_TRACK' | 'DUE_SOON' | 'OVERDUE' | 'NO_DUE_DATE' | 'COMPLETED';
  review_date?: string;
  risk_acceptance_justification?: string;
  risk_accepted_at?: string;
  risk_accepted_by_id?: number;
  risk_acceptance_expiry?: string;
  created_by_id?: number;
  created_at: string;
  updated_at: string;
  owner?: User;
  treatment_owner?: User;
  created_by?: User;
  risk_accepted_by?: User;
  linked_controls_count: number;
  linked_findings_count: number;
  control_links?: RiskControlLink[];
  finding_links?: RiskFindingLink[];
}

export interface HeatmapCell {
  likelihood: number;
  impact: number;
  score: number;
  band: string;
  count: number;
}

export interface RiskStats {
  total_risks: number;
  identified_count: number;
  assessed_count: number;
  treatment_planned_count: number;
  mitigating_count: number;
  monitoring_count: number;
  accepted_count: number;
  closed_count: number;
  critical_inherent_count: number;
  high_inherent_count: number;
  moderate_inherent_count: number;
  low_inherent_count: number;
  above_appetite_count: number;
  near_limit_count: number;
  within_appetite_count: number;
  overdue_treatments_count: number;
  due_soon_treatments_count: number;
  inherent_vs_residual_reduction: number;
}

export type ExceptionType =
  | 'CONTROL_DEVIATION'
  | 'POLICY_EXCEPTION'
  | 'CONFIGURATION_STANDARD'
  | 'THIRD_PARTY_VENDOR'
  | 'ACCESS_CONTROL'
  | 'OTHER';

export type ExceptionStatus =
  | 'REQUESTED'
  | 'UNDER_REVIEW'
  | 'APPROVED'
  | 'ACTIVE'
  | 'EXPIRED'
  | 'REJECTED'
  | 'CLOSED';

export interface ExceptionCompensatingControl {
  id: number;
  organization_id: number;
  exception_id: number;
  organization_control_id: number;
  implementation_notes?: string;
  created_by_id?: number;
  created_at: string;
  organization_control?: OrganizationControl;
}

export interface SecurityException {
  id: number;
  organization_id: number;
  title: string;
  description: string;
  justification: string;
  exception_type: ExceptionType;
  status: ExceptionStatus;
  effective_status: string;
  requested_by_id?: number;
  owner_id?: number;
  reviewer_id?: number;
  requested_at: string;
  approved_at?: string;
  effective_date?: string;
  expiry_date: string;
  review_date?: string;
  residual_risk_level: string;
  approval_notes?: string;
  rejection_reason?: string;
  closure_notes?: string;
  closed_at?: string;
  closed_by_id?: number;
  linked_organization_control_id?: number;
  linked_policy_id?: number;
  linked_finding_id?: number;
  created_at: string;
  updated_at: string;
  requested_by?: User;
  owner?: User;
  reviewer?: User;
  closed_by?: User;
  linked_control?: OrganizationControl;
  linked_policy?: Policy;
  linked_finding?: Finding;
  compensating_controls_count: number;
  compensating_controls?: ExceptionCompensatingControl[];
}

export interface ExceptionStats {
  total_exceptions: number;
  requested_count: number;
  under_review_count: number;
  active_count: number;
  expired_count: number;
  rejected_count: number;
  closed_count: number;
  expiring_soon_count: number;
}

// ─── Phase 6: Audit Management ───────────────────────────────────────────────

export type AuditType = 'INTERNAL' | 'EXTERNAL' | 'REGULATORY' | 'COMPLIANCE' | 'OPERATIONAL' | 'TECHNICAL' | 'THIRD_PARTY';

export type AuditStatus = 'PLANNED' | 'INITIATED' | 'FIELDWORK' | 'REVIEW' | 'REPORTING' | 'COMPLETED' | 'CLOSED';

export type AuditOpinion = 'UNISSUED' | 'UNQUALIFIED' | 'QUALIFIED' | 'ADVERSE' | 'DISCLAIMER';

export type ProcedureResult = 'NOT_STARTED' | 'IN_PROGRESS' | 'PASSED' | 'PARTIALLY_PASSED' | 'FAILED' | 'NOT_APPLICABLE';

export interface Audit {
  id: number;
  organization_id: number;
  title: string;
  audit_type: AuditType;
  audit_reference?: string;
  objective: string;
  scope_description?: string;
  methodology?: string;
  limitations?: string;
  summary?: string;
  framework_id?: number;
  lead_auditor_id?: number;
  audit_team_notes?: string;
  planned_start_date?: string;
  planned_end_date?: string;
  actual_start_date?: string;
  actual_end_date?: string;
  status: AuditStatus;
  opinion: AuditOpinion;
  opinion_issued_by_id?: number;
  opinion_issued_at?: string;
  opinion_notes?: string;
  closed_at?: string;
  closed_by_id?: number;
  closure_notes?: string;
  created_by_id?: number;
  created_at: string;
  updated_at: string;
  scope_controls_count: number;
  procedures_count: number;
  findings_count: number;
  // Detail-only fields
  scope_controls?: AuditScopeControl[];
  procedures?: AuditProcedure[];
  finding_links?: AuditFindingLink[];
}

export interface AuditScopeControl {
  id: number;
  audit_id: number;
  organization_control_id: number;
  scope_notes?: string;
  created_by_id?: number;
  created_at: string;
}

export interface AuditProcedure {
  id: number;
  audit_id: number;
  organization_control_id?: number;
  title: string;
  objective?: string;
  test_steps?: string;
  expected_result?: string;
  actual_result?: string;
  assessment_method?: string;
  result: ProcedureResult;
  execution_notes?: string;
  limitations?: string;
  tester_id?: number;
  execution_date?: string;
  created_by_id?: number;
  created_at: string;
  updated_at: string;
  evidence_count: number;
}

export interface AuditFindingLink {
  id: number;
  audit_id: number;
  finding_id: number;
  source_procedure_id?: number;
  link_notes?: string;
  created_by_id?: number;
  created_at: string;
}

export interface AuditProcedureEvidence {
  id: number;
  procedure_id: number;
  evidence_id: number;
  link_notes?: string;
  created_by_id?: number;
  created_at: string;
}

export interface AuditReadiness {
  audit_id: number;
  audit_status: AuditStatus;
  controls_in_scope: number;
  controls_with_evidence: number;
  controls_assessed: number;
  procedures_total: number;
  procedures_not_started: number;
  procedures_in_progress: number;
  procedures_passed: number;
  procedures_partially_passed: number;
  procedures_failed: number;
  procedures_not_applicable: number;
  procedures_completed: number;
  findings_total: number;
  findings_open: number;
  findings_critical: number;
  findings_high: number;
  findings_in_remediation: number;
  active_exceptions_in_scope: number;
  readiness_score: number;
  readiness_band: 'NOT_READY' | 'PARTIALLY_READY' | 'SUBSTANTIALLY_READY' | 'READY';
  readiness_blockers: string[];
}

export interface AuditStats {
  total_audits: number;
  planned_count: number;
  in_progress_count: number;
  completed_count: number;
  closed_count: number;
  open_findings_across_audits: number;
  critical_findings_count: number;
  unissued_opinion_count: number;
}

// ── Phase 7 Continuous Control Monitoring Types ──────────────────────────────
export type ControlHealthStatus = 'HEALTHY' | 'DEGRADED' | 'AT_RISK' | 'FAILING';
export type EvaluationTrigger = 'SCHEDULED' | 'MANUAL' | 'EVENT_DRIVEN';
export type DriftAlertType =
  | 'EVIDENCE_EXPIRED'
  | 'EVIDENCE_MISSING'
  | 'ASSESSMENT_OVERDUE'
  | 'CRITICAL_FINDING_SLA_BREACH'
  | 'EXCEPTION_EXPIRING_SOON'
  | 'EXCEPTION_EXPIRED'
  | 'CONTROL_DEGRADED';
export type DriftAlertSeverity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type DriftAlertStatus = 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED' | 'DISMISSED';

export interface ControlHealthSnapshot {
  id: number;
  organization_id: number;
  organization_control_id: number;
  health_score: number;
  health_status: ControlHealthStatus;
  evidence_freshness_score: number;
  assessment_currency_score: number;
  finding_penalty_score: number;
  exception_penalty_score: number;
  active_findings_count: number;
  critical_high_findings_count: number;
  active_exceptions_count: number;
  accepted_evidence_count: number;
  days_since_last_evidence?: number;
  days_since_last_assessment?: number;
  evaluated_at: string;
  evaluation_trigger: EvaluationTrigger;
}

export interface ControlHealthSummary {
  organization_control_id: number;
  control_code?: string;
  control_title?: string;
  category_code?: string;
  function_code?: string;
  implementation_status: string;
  health_score: number;
  health_status: ControlHealthStatus;
  evidence_freshness_score: number;
  assessment_currency_score: number;
  finding_penalty_score: number;
  exception_penalty_score: number;
  active_findings_count: number;
  critical_high_findings_count: number;
  active_exceptions_count: number;
  accepted_evidence_count: number;
  days_since_last_evidence?: number;
  days_since_last_assessment?: number;
  last_evaluated_at?: string;
  active_drift_alerts_count: number;
}

export interface ComplianceDriftAlert {
  id: number;
  organization_id: number;
  organization_control_id: number;
  alert_type: DriftAlertType;
  severity: DriftAlertSeverity;
  status: DriftAlertStatus;
  title: string;
  description: string;
  remediation_guidance?: string;
  acknowledged_by_id?: number;
  acknowledged_at?: string;
  resolved_by_id?: number;
  resolved_at?: string;
  resolution_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface MonitoringConfig {
  id: number;
  organization_id: number;
  frequency_hours: number;
  is_enabled: boolean;
  evidence_max_age_days: number;
  assessment_max_age_days: number;
  exception_warning_window_days: number;
  finding_sla_critical_days: number;
  finding_sla_high_days: number;
  last_run_at?: string;
  last_run_status?: string;
  created_at: string;
  updated_at: string;
}

export interface MonitoringOverview {
  average_health_score: number;
  overall_health_status: ControlHealthStatus;
  total_monitored_controls: number;
  healthy_controls_count: number;
  degraded_controls_count: number;
  at_risk_controls_count: number;
  failing_controls_count: number;
  active_drift_alerts_count: number;
  critical_drift_alerts_count: number;
  high_drift_alerts_count: number;
  medium_drift_alerts_count: number;
  low_drift_alerts_count: number;
  evidence_freshness_aggregate_pct: number;
  controls_assessed_currency_pct: number;
  last_evaluation_run?: string;
}

export interface EvaluationRunResult {
  evaluated_controls_count: number;
  alerts_generated_count: number;
  alerts_auto_resolved_count: number;
  average_health_score: number;
  evaluated_at: string;
}

// ── Phase 8: Multi-Framework Harmonization & Control Rationalization ─────────

export type MappingType = 'EXACT' | 'SUBSET' | 'SUPERSET' | 'PARTIAL' | 'CORRELATED';

export type CommonControlDomain =
  | 'IDENTITY_ACCESS'
  | 'CRYPTOGRAPHY'
  | 'DATA_PROTECTION'
  | 'INCIDENT_MANAGEMENT'
  | 'VULNERABILITY_MANAGEMENT'
  | 'BUSINESS_CONTINUITY'
  | 'GOVERNANCE_RISK'
  | 'PHYSICAL_SECURITY'
  | 'OTHER';

export type RationalizationStatus = 'DRAFT' | 'ACTIVE' | 'RETIRED';

export interface FrameworkCrosswalkMapping {
  id: number;
  source_subcategory_id: number;
  target_subcategory_id: number;
  mapping_type: MappingType;
  confidence_score: number;
  bidirectional: boolean;
  rationale: string;
  created_at: string;
  updated_at: string;
  source_identifier?: string;
  source_title?: string;
  target_identifier?: string;
  target_title?: string;
}

export interface CrosswalkMappingCreate {
  source_subcategory_id: number;
  target_subcategory_id: number;
  mapping_type: MappingType;
  confidence_score: number;
  bidirectional: boolean;
  rationale: string;
}

export interface CrosswalkMappingUpdate {
  mapping_type?: MappingType;
  confidence_score?: number;
  bidirectional?: boolean;
  rationale?: string;
}

export interface CommonControlMapping {
  id: number;
  organization_id: number;
  rationalized_common_control_id: number;
  organization_control_id: number;
  weight: number;
  created_at: string;
  control_subcategory_identifier?: string;
  control_subcategory_title?: string;
  control_status?: string;
  control_health_score?: number;
  control_health_status?: string;
}

export interface CommonControlMappingCreate {
  organization_control_id: number;
  weight: number;
}

export interface RationalizedCommonControl {
  id: number;
  organization_id: number;
  common_control_code: string;
  title: string;
  description: string;
  domain: CommonControlDomain;
  rationalization_status: RationalizationStatus;
  owner_id?: number;
  deprecation_reason?: string;
  inherited_health_score: number;
  inherited_health_status: ControlHealthStatus;
  mapped_controls_count: number;
  created_at: string;
  updated_at: string;
  mappings?: CommonControlMapping[];
}

export interface CommonControlCreate {
  common_control_code: string;
  title: string;
  description: string;
  domain: CommonControlDomain;
  rationalization_status?: RationalizationStatus;
  owner_id?: number;
  deprecation_reason?: string;
  initial_control_ids?: number[];
}

export interface CommonControlUpdate {
  title?: string;
  description?: string;
  domain?: CommonControlDomain;
  rationalization_status?: RationalizationStatus;
  owner_id?: number;
  deprecation_reason?: string;
}

export interface FrameworkComplianceSnapshot {
  id: number;
  organization_id: number;
  framework_id: number;
  calculation_version: string;
  coverage_percentage: number;
  compliance_health_score: number;
  total_subcategories: number;
  covered_subcategories: number;
  unmapped_subcategories: number;
  evaluated_at: string;
  created_at: string;
  framework_identifier?: string;
  framework_name?: string;
}

export interface FrameworkCompliancePostureOverview {
  framework_id: number;
  framework_identifier: string;
  framework_name: string;
  total_subcategories: number;
  directly_covered_subcategories: number;
  crosswalk_covered_subcategories: number;
  total_covered_subcategories: number;
  coverage_percentage: number;
  compliance_health_score: number;
  evaluated_at?: string;
}

export interface SubcategoryComplianceMatrixItem {
  subcategory_id: number;
  subcategory_identifier: string;
  subcategory_title: string;
  category_identifier: string;
  function_identifier: string;
  is_directly_covered: boolean;
  is_crosswalk_covered: boolean;
  source_subcategory_id?: number;
  source_identifier?: string;
  crosswalk_confidence?: number;
  effective_health_score: number;
  health_status: string;
}

export interface FrameworkDetailedPostureResponse {
  overview: FrameworkCompliancePostureOverview;
  subcategories: SubcategoryComplianceMatrixItem[];
}

export interface MultiFrameworkPostureResponse {
  frameworks: FrameworkCompliancePostureOverview[];
  total_common_controls: number;
  average_common_control_health: number;
  evaluated_at: string;
}

export interface HarmonizationEvaluationResponse {
  organization_id: number;
  evaluated_common_controls: number;
  evaluated_frameworks: number;
  snapshots_created: number;
  evaluated_at: string;
}