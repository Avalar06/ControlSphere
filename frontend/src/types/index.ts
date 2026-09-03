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

// ─────────────────────────────────────────────────────────────────────────────
// Phase 9: Third-Party & Vendor Risk Management (TPRM) Types
// ─────────────────────────────────────────────────────────────────────────────

export type VendorStatus =
  | 'PROSPECT'
  | 'ONBOARDING'
  | 'ACTIVE'
  | 'UNDER_REVIEW'
  | 'SUSPENDED'
  | 'OFFBOARDED';

export type VendorTier =
  | 'TIER_1_CRITICAL'
  | 'TIER_2_SIGNIFICANT'
  | 'TIER_3_MODERATE'
  | 'TIER_4_LOW';

export type VendorRiskBand = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';

export type BusinessCriticality = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type DataClassification = 'RESTRICTED' | 'CONFIDENTIAL' | 'INTERNAL' | 'PUBLIC';

export type NetworkConnectivity =
  | 'DIRECT_API_VPN_DB'
  | 'CREDENTIALED_PORTAL'
  | 'ISOLATED_SAAS'
  | 'AIR_GAPPED_OFFLINE';

export type PiiFinancialAccess =
  | 'DIRECT_PCI_PII_PHI'
  | 'AGGREGATED_ANONYMIZED'
  | 'NO_PII_ACCESS';

export type HostingModel =
  | 'VENDOR_PUBLIC_CLOUD'
  | 'MULTI_TENANT_SAAS'
  | 'DEDICATED_HOSTED'
  | 'ON_PREM_CUSTOMER_DATACENTER';

export type EngagementStatus = 'ACTIVE' | 'PENDING' | 'TERMINATED';

export type VendorAssessmentType =
  | 'INITIAL'
  | 'ANNUAL_REASSESSMENT'
  | 'INCIDENT_TRIGGERED'
  | 'ENGAGEMENT_SPECIFIC';

export type VendorAssessmentStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'IN_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'SUPERSEDED';

export type VendorResponseStatus =
  | 'COMPLIANT'
  | 'PARTIALLY_COMPLIANT'
  | 'NON_COMPLIANT'
  | 'NOT_APPLICABLE';

export type VendorDocumentType =
  | 'SOC2_TYPE_II'
  | 'ISO_27001_CERT'
  | 'PCI_AOC'
  | 'PRIVACY_POLICY'
  | 'PEN_TEST_REPORT'
  | 'BUSINESS_CONTINUITY_PLAN'
  | 'SECURITY_QUESTIONNAIRE'
  | 'OTHER';

export interface Vendor {
  id: number;
  organization_id: number;
  vendor_code: string;
  legal_name: string;
  trade_name?: string;
  business_owner_id?: number;
  vendor_status: VendorStatus;
  calculated_tier: VendorTier;
  override_tier?: VendorTier;
  tier_override_reason?: string;
  tier_overridden_by_id?: number;
  tier_overridden_at?: string;
  calculated_inherent_risk: number;
  residual_risk_score: number;
  risk_band: VendorRiskBand;
  effective_tier: VendorTier;
  created_at: string;
  updated_at: string;
  business_owner?: User;
  tier_overridden_by?: User;
  engagements?: VendorEngagement[];
  assessments?: VendorAssessment[];
  evidence_links?: VendorEvidenceLink[];
}

export interface VendorCreate {
  vendor_code: string;
  legal_name: string;
  trade_name?: string;
  business_owner_id?: number;
}

export interface VendorUpdate {
  legal_name?: string;
  trade_name?: string;
  business_owner_id?: number;
  vendor_status?: VendorStatus;
}

export interface VendorTierOverride {
  override_tier: VendorTier;
  reason: string;
}

export interface VendorEngagement {
  id: number;
  organization_id: number;
  vendor_id: number;
  engagement_code: string;
  engagement_name: string;
  description?: string;
  status: EngagementStatus;
  criticality: BusinessCriticality;
  data_classification: DataClassification;
  hosting_model: HostingModel;
  network_connectivity: NetworkConnectivity;
  pii_access: PiiFinancialAccess;
  calculated_risk_score: number;
  created_at: string;
  updated_at: string;
}

export interface VendorEngagementCreate {
  engagement_code: string;
  engagement_name: string;
  description?: string;
  criticality: BusinessCriticality;
  data_classification: DataClassification;
  hosting_model: HostingModel;
  network_connectivity: NetworkConnectivity;
  pii_access: PiiFinancialAccess;
}

export interface VendorEngagementUpdate {
  engagement_name?: string;
  description?: string;
  status?: EngagementStatus;
  criticality?: BusinessCriticality;
  data_classification?: DataClassification;
  hosting_model?: HostingModel;
  network_connectivity?: NetworkConnectivity;
  pii_access?: PiiFinancialAccess;
}

export interface VendorAssessmentItem {
  id: number;
  organization_id: number;
  assessment_id: number;
  rationalized_common_control_id?: number;
  question_key: string;
  question_text: string;
  response_status: VendorResponseStatus;
  weight: number;
  vendor_response_text?: string;
  assessor_notes?: string;
  findings_count: number;
  created_at: string;
  updated_at: string;
}

export interface VendorAssessmentItemCreate {
  rationalized_common_control_id?: number;
  question_key: string;
  question_text: string;
  response_status?: VendorResponseStatus;
  weight?: number;
  vendor_response_text?: string;
  assessor_notes?: string;
}

export interface VendorAssessmentItemUpdate {
  response_status?: VendorResponseStatus;
  vendor_response_text?: string;
  assessor_notes?: string;
}

export interface VendorAssessment {
  id: number;
  organization_id: number;
  vendor_id: number;
  engagement_id?: number;
  assessment_code: string;
  title: string;
  assessment_type: VendorAssessmentType;
  status: VendorAssessmentStatus;
  assessor_id?: number;
  reviewer_id?: number;
  valid_until?: string;
  calculated_score: number;
  rejection_reason?: string;
  review_notes?: string;
  submitted_at?: string;
  reviewed_at?: string;
  created_at: string;
  updated_at: string;
  assessor?: User;
  reviewer?: User;
  items?: VendorAssessmentItem[];
}

export interface VendorAssessmentCreate {
  engagement_id?: number;
  assessment_code: string;
  title: string;
  assessment_type: VendorAssessmentType;
  valid_until?: string;
  items?: VendorAssessmentItemCreate[];
}

export interface VendorAssessmentUpdate {
  title?: string;
  valid_until?: string;
}

export interface VendorAssessmentReview {
  review_notes?: string;
  rejection_reason?: string;
}

export interface VendorEvidenceLink {
  id: number;
  organization_id: number;
  vendor_id: number;
  evidence_id: number;
  document_type: VendorDocumentType;
  effective_date?: string;
  expiration_date?: string;
  is_verified: boolean;
  verified_by_id?: number;
  verified_at?: string;
  created_at: string;
  evidence?: EvidenceItem;
  verified_by?: User;
}

export interface VendorEvidenceLinkCreate {
  evidence_id: number;
  document_type: VendorDocumentType;
  effective_date?: string;
  expiration_date?: string;
}

export interface VendorInherentRiskBreakdown {
  inherent_risk_score: number;
  calculated_tier: VendorTier;
  effective_tier: VendorTier;
  highest_criticality_engagement_code?: string;
  active_engagements_count: number;
}

export interface VendorResidualRiskBreakdown {
  inherent_risk_score: number;
  latest_assessment_score?: number;
  risk_floor: number;
  base_residual_risk: number;
  finding_penalties: number;
  exception_penalties: number;
  residual_risk_score: number;
  risk_band: VendorRiskBand;
}

export interface VendorRiskPostureResponse {
  vendor_id: number;
  vendor_code: string;
  legal_name: string;
  status: VendorStatus;
  inherent: VendorInherentRiskBreakdown;
  residual: VendorResidualRiskBreakdown;
  engagements: VendorEngagement[];
  latest_approved_assessment?: VendorAssessment;
  evidence_links: VendorEvidenceLink[];
}

export interface VendorOverviewResponse {
  total_vendors: number;
  average_residual_risk: number;
  high_or_critical_risk_vendors: number;
  tier_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  risk_band_distribution: Record<string, number>;
}

// ============================================================================
// Phase 10: Security Incident Management, Breach Governance & Regulatory Disclosure
// ============================================================================

export type IncidentSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type IncidentCategory =
  | 'RANSOMWARE'
  | 'DATA_BREACH'
  | 'UNAUTHORIZED_ACCESS'
  | 'DENIAL_OF_SERVICE'
  | 'INSIDER_THREAT'
  | 'SUPPLY_CHAIN_COMPROMISE'
  | 'OTHER';

export type IncidentStatus =
  | 'DECLARED'
  | 'TRIAGED'
  | 'CONTAINED'
  | 'ERADICATED'
  | 'RECOVERED'
  | 'POST_MORTEM'
  | 'CLOSED';

export type RootCauseClassification =
  | 'CONTROL_FAILURE'
  | 'HUMAN_ERROR'
  | 'ZERO_DAY'
  | 'THIRD_PARTY_FAILURE'
  | 'CONFIGURATION_DRIFT';

export type Regulator =
  | 'GDPR_DPA'
  | 'SEC_8K'
  | 'HHS_OCR'
  | 'PCI_SSC'
  | 'NYDFS'
  | 'STATE_AG';

export type DisclosureStatus =
  | 'NOT_APPLICABLE'
  | 'PENDING'
  | 'DUE'
  | 'NOTIFIED'
  | 'OVERDUE';

export type DisclosureTriggerType =
  | 'INCIDENT_DETECTION'
  | 'MATERIALITY_DETERMINATION'
  | 'PHI_THRESHOLD_BREACH'
  | 'CDE_COMPROMISE'
  | 'LEGAL_DIRECTIVE';

export type TimelineEventType =
  | 'DETECTION'
  | 'CONTAINMENT_ACTION'
  | 'ERADICATION_STEP'
  | 'EVIDENCE_COLLECTED'
  | 'REGULATOR_NOTIFIED'
  | 'COMMAND_TRANSFER'
  | 'POST_MORTEM_NOTE';

export type TimelineEventSource =
  | 'MANUAL_ENTRY'
  | 'SYSTEM_AUTOMATION'
  | 'CCM_DRIFT'
  | 'FORENSIC_LOG';

export type IncidentControlRelationship =
  | 'FAILED_CONTROL'
  | 'DEFICIENT_CONTROL'
  | 'CIRCUMVENTED_CONTROL'
  | 'DETECTING_CONTROL';

export interface SecurityIncident {
  id: number;
  organization_id: number;
  incident_code: string;
  title: string;
  description: string;
  severity: IncidentSeverity;
  category: IncidentCategory;
  status: IncidentStatus;
  incident_commander_id: number;
  business_owner_id?: number;
  closed_by_id?: number;
  detected_at: string;
  declared_at: string;
  contained_at?: string;
  eradicated_at?: string;
  recovered_at?: string;
  post_mortem_at?: string;
  closed_at?: string;
  affected_record_count: number;
  affected_systems_summary?: string;
  financial_impact_estimate: number;
  is_material: boolean;
  materiality_determined_at?: string;
  materiality_determined_by_id?: number;
  root_cause_classification?: RootCauseClassification;
  root_cause_narrative?: string;
  lessons_learned?: string;
  closure_notes?: string;
  compliance_drift_alert_id?: number;
  created_at: string;
  updated_at: string;
  incident_commander?: User;
  business_owner?: User;
  closed_by?: User;
}

export interface IncidentCreate {
  incident_code: string;
  title: string;
  description: string;
  severity?: IncidentSeverity;
  category?: IncidentCategory;
  detected_at: string;
  declared_at?: string;
  business_owner_id?: number;
  affected_record_count?: number;
  affected_systems_summary?: string;
  financial_impact_estimate?: number;
  compliance_drift_alert_id?: number;
}

export interface IncidentUpdate {
  title?: string;
  description?: string;
  severity?: IncidentSeverity;
  category?: IncidentCategory;
  business_owner_id?: number;
  affected_record_count?: number;
  affected_systems_summary?: string;
  financial_impact_estimate?: number;
  root_cause_classification?: RootCauseClassification;
  root_cause_narrative?: string;
  lessons_learned?: string;
}

export interface IncidentStatusTransition {
  target_status: IncidentStatus;
  notes?: string;
}

export interface IncidentCloseRequest {
  closure_notes: string;
  lessons_learned?: string;
  root_cause_classification?: RootCauseClassification;
  root_cause_narrative?: string;
}

export interface IncidentMaterialityUpdate {
  is_material: boolean;
  materiality_notes?: string;
}

export interface IncidentTimelineEvent {
  id: number;
  organization_id: number;
  incident_id: number;
  event_type: TimelineEventType;
  event_occurred_at: string;
  actor_id: number;
  description: string;
  source: TimelineEventSource;
  created_at: string;
  actor?: User;
}

export interface IncidentTimelineEventCreate {
  event_type: TimelineEventType;
  event_occurred_at: string;
  description: string;
  source?: TimelineEventSource;
}

export interface IncidentControlLink {
  id: number;
  organization_id: number;
  incident_id: number;
  organization_control_id: number;
  relationship_type: IncidentControlRelationship;
  notes?: string;
  created_at: string;
  organization_control?: OrganizationControl;
}

export interface IncidentControlLinkCreate {
  organization_control_id: number;
  relationship_type?: IncidentControlRelationship;
  notes?: string;
}

export interface IncidentVendorLink {
  id: number;
  organization_id: number;
  incident_id: number;
  vendor_id: number;
  vendor_engagement_id?: number;
  is_vendor_originated: boolean;
  notes?: string;
  created_at: string;
  vendor?: Vendor;
  vendor_engagement?: VendorEngagement;
}

export interface IncidentVendorLinkCreate {
  vendor_id: number;
  vendor_engagement_id?: number;
  is_vendor_originated?: boolean;
  notes?: string;
}

export interface IncidentRegulatoryDisclosure {
  id: number;
  organization_id: number;
  incident_id: number;
  regulator: Regulator;
  status: DisclosureStatus;
  rule_version: string;
  calculation_version: string;
  trigger_type: DisclosureTriggerType;
  triggered_at: string;
  triggered_by_id?: number;
  deadline_at: string;
  notified_at?: string;
  notified_by_id?: number;
  notification_reference_code?: string;
  exemption_reason?: string;
  disclosure_notes?: string;
  created_at: string;
  updated_at: string;
  triggered_by?: User;
  notified_by?: User;
}

export interface IncidentRegulatoryDisclosureCreate {
  regulator: Regulator;
  trigger_type?: DisclosureTriggerType;
  triggered_at: string;
  rule_version?: string;
  calculation_version?: string;
}

export interface IncidentRegulatoryNotificationRequest {
  notification_reference_code: string;
  disclosure_notes?: string;
}

export interface IncidentRegulatoryExemptionRequest {
  exemption_reason: string;
}

export interface IncidentDetailRead extends SecurityIncident {
  timeline_events: IncidentTimelineEvent[];
  disclosures: IncidentRegulatoryDisclosure[];
  control_links: IncidentControlLink[];
  vendor_links: IncidentVendorLink[];
  ttc_hours?: number;
  mttr_hours?: number;
  incident_age_hours?: number;
}

export interface IncidentOverviewResponse {
  total_incidents: number;
  open_incidents: number;
  critical_or_high_incidents: number;
  material_incidents: number;
  overdue_disclosures: number;
  status_distribution: Record<string, number>;
  severity_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
  average_ttc_hours?: number;
  average_mttr_hours?: number;
}

// ─── PHASE 11: REMEDIATION ORCHESTRATION, CAPA & CLOSED-LOOP ASSURANCE ───────

export type RemediationSourceType =
  | 'FINDING'
  | 'CCM_DRIFT'
  | 'SECURITY_INCIDENT'
  | 'TPRM_ASSESSMENT'
  | 'AUDIT';

export type RemediationRootCauseClassification =
  | 'CONTROL_DEFICIENCY'
  | 'CONFIGURATION_DRIFT'
  | 'HUMAN_ERROR'
  | 'VENDOR_DEFAULT'
  | 'ARCHITECTURAL_GAP';

export type RemediationStatus =
  | 'DRAFT'
  | 'APPROVED'
  | 'IN_EXECUTION'
  | 'PENDING_VALIDATION'
  | 'VERIFIED_CLOSED'
  | 'CANCELLED';

export type RemediationSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type TaskStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';

export type EvidenceVerificationStatus = 'SUBMITTED' | 'VALIDATED' | 'REJECTED';

export type ReTestResult = 'PASS' | 'FAIL' | 'INCONCLUSIVE';

export type SlaStatus =
  | 'NOT_STARTED'
  | 'ON_TRACK'
  | 'AT_RISK'
  | 'BREACHED'
  | 'COMPLETED_ON_TIME'
  | 'COMPLETED_LATE';

export interface RemediationEvidenceLink {
  id: number;
  organization_id: number;
  remediation_task_id: number;
  evidence_id: number;
  verification_status: EvidenceVerificationStatus;
  notes?: string;
  created_at: string;
  evidence?: EvidenceItem;
}

export interface RemediationEvidenceLinkCreate {
  evidence_id: number;
  notes?: string;
}

export interface RemediationTask {
  id: number;
  organization_id: number;
  remediation_plan_id: number;
  task_seq: number;
  title: string;
  description: string;
  assignee_id?: number;
  due_date?: string;
  status: TaskStatus;
  completed_at?: string;
  implementation_notes?: string;
  created_at: string;
  updated_at: string;
  assignee?: User;
  evidence_links?: RemediationEvidenceLink[];
}

export interface RemediationTaskCreate {
  task_seq: number;
  title: string;
  description: string;
  assignee_id?: number;
  due_date?: string;
}

export interface RemediationTaskUpdate {
  title?: string;
  description?: string;
  assignee_id?: number;
  due_date?: string;
  status?: TaskStatus;
  implementation_notes?: string;
}

export interface RemediationReTestRecord {
  id: number;
  organization_id: number;
  remediation_plan_id: number;
  test_executed_at: string;
  tester_id: number;
  test_result: ReTestResult;
  metric_observed_value?: number;
  evidence_id?: number;
  validation_narrative: string;
  created_at: string;
  tester?: User;
  evidence?: EvidenceItem;
}

export interface RemediationReTestCreate {
  test_executed_at: string;
  test_result: ReTestResult;
  metric_observed_value?: number;
  evidence_id?: number;
  validation_narrative: string;
}

export interface RemediationPlan {
  id: number;
  organization_id: number;
  plan_code: string;
  title: string;
  problem_statement: string;
  root_cause_classification: RemediationRootCauseClassification;
  source_type: RemediationSourceType;
  severity: RemediationSeverity;
  status: RemediationStatus;
  plan_owner_id: number;
  approved_by_id?: number;
  approved_at?: string;
  started_at?: string;
  target_completion_at?: string;
  verified_by_id?: number;
  verified_at?: string;
  verification_notes?: string;
  cancellation_notes?: string;
  validation_attempts_count: number;
  rei_score?: number;
  ttr_hours?: number;
  is_immutable: boolean;
  finding_id?: number;
  compliance_drift_alert_id?: number;
  security_incident_id?: number;
  vendor_assessment_id?: number;
  audit_id?: number;
  created_at: string;
  updated_at: string;
  sla_status?: SlaStatus;
  remaining_hours?: number;
  plan_owner?: User;
  approved_by?: User;
  verified_by?: User;
  finding?: Finding;
  compliance_drift_alert?: ComplianceDriftAlert;
  security_incident?: SecurityIncident;
  vendor_assessment?: VendorAssessment;
  audit?: Audit;
}

export interface RemediationPlanDetailRead extends RemediationPlan {
  tasks: RemediationTask[];
  retest_records: RemediationReTestRecord[];
}

export interface RemediationPlanCreate {
  plan_code: string;
  title: string;
  problem_statement: string;
  root_cause_classification: RemediationRootCauseClassification;
  source_type: RemediationSourceType;
  severity?: RemediationSeverity;
  finding_id?: number;
  compliance_drift_alert_id?: number;
  security_incident_id?: number;
  vendor_assessment_id?: number;
  audit_id?: number;
  target_completion_at?: string;
}

export interface RemediationPlanUpdate {
  title?: string;
  problem_statement?: string;
  root_cause_classification?: RemediationRootCauseClassification;
  severity?: RemediationSeverity;
  target_completion_at?: string;
}

export interface RemediationPlanApproveRequest {
  target_completion_at?: string;
  notes?: string;
}

export interface RemediationPlanCancelRequest {
  cancellation_notes: string;
}

export interface RemediationPlanRejectValidationRequest {
  rejection_notes: string;
}

export interface RemediationPlanVerifyCloseRequest {
  verification_notes: string;
}

export interface RemediationOverviewResponse {
  total_plans: number;
  open_plans: number;
  critical_or_high_plans: number;
  pending_validation_plans: number;
  sla_breached_plans: number;
  average_rei_score?: number;
  average_ttr_hours?: number;
  status_distribution: Record<string, number>;
  severity_distribution: Record<string, number>;
  source_distribution: Record<string, number>;
  sla_distribution: Record<string, number>;
}

// ─── Phase 12: Cyber Risk Quantification & Loss Modeling (QUANTUM-GRC) ──────

export type ScenarioStatus = 'DRAFT' | 'ACTIVE' | 'FROZEN' | 'ARCHIVED';

export type ThreatActorCategory =
  | 'CYBERCRIMINAL'
  | 'NATION_STATE'
  | 'INSIDER'
  | 'HACKTIVIST'
  | 'ACCIDENTAL';

export type AppetiteStatus = 'DRAFT' | 'APPROVED' | 'SUPERSEDED';

export type AppetiteBreachState =
  | 'WITHIN_APPETITE'
  | 'EXCEEDS_ALE'
  | 'EXCEEDS_VAR'
  | 'EXCEEDS_BOTH';

export interface QuantitativeRiskScenario {
  id: number;
  organization_id: number;
  scenario_code: string;
  title: string;
  description: string;
  status: ScenarioStatus;
  threat_actor_category: ThreatActorCategory;

  // Upstream Linkages
  risk_id?: number;
  organization_control_id?: number;
  vendor_id?: number;

  // Three-Point Threat & Loss Inputs
  tef_min: number;
  tef_mode: number;
  tef_max: number;
  tcap: number;

  pl_min: number;
  pl_mode: number;
  pl_max: number;

  sl_min: number;
  sl_mode: number;
  sl_max: number;
  slop: number;

  // Server-Authoritative Telemetry
  control_strength: number;
  vulnerability_factor: number;
  loss_event_frequency: number;
  single_loss_expectancy: number;
  annualized_loss_expectancy: number;
  var_95_parametric?: number;
  var_99_parametric?: number;
  var_95_empirical?: number;
  var_99_empirical?: number;

  // Governance & Immutability
  is_immutable: boolean;
  is_ccm_stale: boolean;
  calculation_version: string;
  input_snapshot_hash?: string;
  calculated_at?: string;

  created_by_id: number;
  created_at: string;
  updated_at: string;
  created_by?: User;
}

export interface QuantitativeRiskScenarioCreate {
  scenario_code: string;
  title: string;
  description: string;
  threat_actor_category?: ThreatActorCategory;
  risk_id?: number;
  organization_control_id?: number;
  vendor_id?: number;
  tef_min?: number;
  tef_mode?: number;
  tef_max?: number;
  tcap?: number;
  pl_min?: number;
  pl_mode?: number;
  pl_max?: number;
  sl_min?: number;
  sl_mode?: number;
  sl_max?: number;
  slop?: number;
}

export interface QuantitativeRiskScenarioUpdate {
  title?: string;
  description?: string;
  threat_actor_category?: ThreatActorCategory;
  risk_id?: number;
  organization_control_id?: number;
  vendor_id?: number;
  tef_min?: number;
  tef_mode?: number;
  tef_max?: number;
  tcap?: number;
  pl_min?: number;
  pl_mode?: number;
  pl_max?: number;
  sl_min?: number;
  sl_mode?: number;
  sl_max?: number;
  slop?: number;
}

export interface QuantitativeSimulationRequest {
  trial_count?: number;
  simulation_seed?: number;
}

export interface QuantitativeSimulationRun {
  id: number;
  organization_id: number;
  scenario_id: number;
  trial_count: number;
  simulation_seed: number;
  algorithm_version: string;

  mean_loss: number;
  variance_loss: number;
  std_dev_loss: number;

  percentile_10: number;
  percentile_50: number;
  percentile_90: number;
  percentile_95: number;
  percentile_99: number;

  simulated_by_id: number;
  simulated_at: string;
  simulated_by?: User;
}

export interface RosiAnalysisCreate {
  remediation_plan_id: number;
  remediation_cost: number;
  projected_control_strength_delta?: number;
}

export interface RosiAnalysis {
  id: number;
  organization_id: number;
  scenario_id: number;
  remediation_plan_id: number;

  remediation_cost: number;
  current_ale: number;
  projected_ale: number;
  risk_reduction_ale: number;
  net_economic_benefit: number;
  rosi_percentage: number;

  created_by_id: number;
  created_at: string;
  created_by?: User;
}

export interface FinancialRiskAppetiteCreate {
  ale_limit: number;
  var_95_limit: number;
  notes?: string;
}

export interface FinancialRiskAppetiteApproveRequest {
  notes?: string;
}

export interface FinancialRiskAppetite {
  id: number;
  organization_id: number;
  version: number;
  ale_limit: number;
  var_95_limit: number;
  status: AppetiteStatus;
  notes?: string;

  requested_by_id: number;
  approved_by_id?: number;
  created_at: string;
  approved_at?: string;

  requested_by?: User;
  approved_by?: User;
}

export interface QuantOverviewResponse {
  total_scenarios: number;
  active_scenarios: number;
  frozen_scenarios: number;
  portfolio_ale: number;
  portfolio_var_95: number;
  appetite_status: AppetiteBreachState;
  ale_limit?: number;
  var_95_limit?: number;
  threat_category_distribution: Record<string, number>;
  top_risk_scenarios: QuantitativeRiskScenario[];
}

// ─── Phase 13: Operational Resilience & Business Impact Analysis (RESILIENCE-GRC)

export type CriticalityTier = 'TIER_1' | 'TIER_2' | 'TIER_3' | 'TIER_4';

export type BiaStatus = 'DRAFT' | 'ACTIVE' | 'SUPERSEDED' | 'ARCHIVED';

export type DependencyType = 'VENDOR' | 'CONTROL';

export interface BusinessProcessBase {
  name: string;
  description?: string | null;
  criticality_tier: CriticalityTier;
}

export interface BusinessProcessCreate extends BusinessProcessBase {}

export interface BusinessProcessUpdate {
  name?: string;
  description?: string | null;
  criticality_tier?: CriticalityTier;
}

export interface ProcessDependency {
  id: number;
  organization_id: number;
  process_id: number;
  dependency_type: DependencyType;
  dependency_id: number;
  notes?: string | null;
  created_at: string;
}

export interface ProcessDependencyCreate {
  process_id: number;
  dependency_type: DependencyType;
  dependency_id: number;
  notes?: string | null;
}

export interface BusinessImpactAnalysisBase {
  rto_hours: number;
  rpo_hours: number;
  mtd_hours: number;
  hourly_downtime_cost: number;
  fixed_outage_cost: number;
  notes?: string | null;
}

export interface BusinessImpactAnalysisCreate extends BusinessImpactAnalysisBase {
  process_id: number;
}

export interface BusinessImpactAnalysisApproveRequest {
  notes?: string | null;
}

export interface BusinessImpactAnalysis extends BusinessImpactAnalysisBase {
  id: number;
  organization_id: number;
  process_id: number;
  status: BiaStatus;
  version: number;
  requested_by_id: number;
  approved_by_id?: number | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
  requested_by?: User;
  approved_by?: User;
}

export interface BusinessProcess extends BusinessProcessBase {
  id: number;
  organization_id: number;
  owner_id: number;
  created_at: string;
  updated_at: string;
  owner?: User;
  active_bia?: BusinessImpactAnalysis | null;
  dependencies?: ProcessDependency[];
}

export interface OutageCostCalculationRequest {
  duration_hours: number;
  hourly_downtime_cost: number;
  fixed_outage_cost?: number;
}

export interface OutageCostCalculationResult {
  duration_hours: number;
  fixed_outage_cost: number;
  hourly_downtime_cost: number;
  variable_outage_cost: number;
  total_projected_loss: number;
}

// ─── Phase 14: EXPOSURE-GRC Types ─────────────────────────────────────────────

export type ExposureSeverity =
  | 'CRITICAL'
  | 'HIGH'
  | 'MEDIUM'
  | 'LOW'
  | 'INFORMATIONAL';

export type ExposureStatus =
  | 'OPEN'
  | 'UNDER_INVESTIGATION'
  | 'REMEDIATING'
  | 'EXCEPTION_REQUESTED'
  | 'EXCEPTION_APPROVED'
  | 'EXCEPTION_REJECTED'
  | 'RESOLVED';

export type AssetType =
  | 'SERVER'
  | 'DATABASE'
  | 'CLOUD_SERVICE'
  | 'NETWORK_DEVICE'
  | 'APPLICATION';

export type Environment = 'PRODUCTION' | 'STAGING' | 'DEVELOPMENT';

export type ExceptionApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';

export interface ExposureAssetLinkBase {
  asset_identifier: string;
  asset_type: AssetType;
  environment: Environment;
  process_id?: number | null;
  vendor_id?: number | null;
  control_id?: number | null;
  notes?: string | null;
}

export interface ExposureAssetLinkCreate extends ExposureAssetLinkBase {}

export interface ExposureAssetLink extends ExposureAssetLinkBase {
  id: number;
  organization_id: number;
  exposure_id: number;
  created_at: string;
  process_name?: string | null;
  process_tier?: CriticalityTier | null;
  vendor_name?: string | null;
  control_title?: string | null;
}

export interface ExposureExceptionBase {
  requested_sla_due: string;
  justification: string;
  compensating_controls?: string | null;
}

export interface ExposureExceptionCreate extends ExposureExceptionBase {}

export interface ExposureExceptionReviewRequest {
  decision: 'APPROVED' | 'REJECTED';
  review_notes?: string | null;
}

export interface ExposureException extends ExposureExceptionBase {
  id: number;
  organization_id: number;
  exposure_id: number;
  requested_by_id: number;
  approved_by_id?: number | null;
  status: ExceptionApprovalStatus;
  original_sla_due: string;
  requested_sla_due: string;
  justification: string;
  compensating_controls?: string | null;
  review_notes?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  requested_by?: User | null;
  approved_by?: User | null;
}

export interface VulnerabilityExposureBase {
  cve_id: string;
  cwe_id?: string | null;
  title: string;
  description?: string | null;
  cvss_score: number;
  cvss_vector?: string | null;
  epss_score: number;
  cisa_kev: boolean;
  severity: ExposureSeverity;
}

export interface VulnerabilityExposureCreate extends VulnerabilityExposureBase {
  discovered_at?: string | null;
  remediation_sla_due?: string | null;
}

export interface VulnerabilityExposureUpdate {
  title?: string;
  description?: string | null;
  cwe_id?: string | null;
  cvss_score?: number;
  cvss_vector?: string | null;
  epss_score?: number;
  cisa_kev?: boolean;
  severity?: ExposureSeverity;
}

export interface VulnerabilityExposureStatusUpdate {
  status: ExposureStatus;
  notes?: string | null;
}

export interface VulnerabilityExposure extends VulnerabilityExposureBase {
  id: number;
  organization_id: number;
  status: ExposureStatus;
  exposure_index: number;
  remediation_sla_due: string;
  remediation_plan_id?: number | null;
  discovered_at: string;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
  asset_links?: ExposureAssetLink[];
  exceptions?: ExposureException[];
}

export interface ExposureIndexCalculateRequest {
  cvss_score: number;
  epss_score: number;
  cisa_kev: boolean;
  highest_process_tier?: CriticalityTier | null;
}

export interface ExposureIndexCalculateResponse {
  cvss_score: number;
  epss_score: number;
  cisa_kev: boolean;
  base_score: number;
  blast_radius_multiplier: number;
  exposure_index: number;
}

export interface ExposureSummaryResponse {
  total_exposures: number;
  critical_exposures: number;
  high_exposures: number;
  cisa_kev_count: number;
  active_exceptions_count: number;
  sla_breached_count: number;
  sla_breach_rate_percent: number;
  average_exposure_index: number;
  severity_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
}

// ─── Phase 15: AI-GRC Domain Types ──────────────────────────────────────────

export type AISystemType =
  | 'LLM_APPLICATION'
  | 'AGENTIC_WORKFLOW'
  | 'EMBEDDED_ML'
  | 'COMPUTER_VISION'
  | 'RECOMMENDER'
  | 'PREDICTIVE_ANALYTICS';

export type AILifecycleState =
  | 'DEVELOPMENT'
  | 'VALIDATION'
  | 'ETHICAL_REVIEW'
  | 'APPROVED_STAGING'
  | 'PRODUCTION'
  | 'DECOMMISSIONED'
  | 'REJECTED';

export type AIRegulatoryTier =
  | 'PROHIBITED'
  | 'HIGH_RISK'
  | 'GPAI_SYSTEMIC_RISK'
  | 'LIMITED_RISK'
  | 'MINIMAL_RISK';

export type AIAutonomyLevel =
  | 'NO_AUTONOMY'
  | 'HUMAN_IN_THE_LOOP'
  | 'HUMAN_ON_THE_LOOP'
  | 'FULL_AUTONOMY';

export type AIDataSensitivity =
  | 'PUBLIC'
  | 'INTERNAL'
  | 'CONFIDENTIAL'
  | 'RESTRICTED_PII_PHI';

export type AIHostingType =
  | 'CLOUD_THIRD_PARTY'
  | 'ON_PREMISE_SELF_HOSTED'
  | 'HYBRID_VPC'
  | 'EDGE_DEVICE';

export type AIApprovalStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'WITHDRAWN';

export interface AIModelCardBase {
  version: string;
  intended_use: string;
  out_of_scope_uses?: string | null;
  bias_mitigation_notes?: string | null;
  training_data_provenance?: string | null;
  synthetic_data_percentage: number;
  hallucination_rate_percent: number;
  prompt_injection_resistance_score: number;
  toxicity_filter_efficiency_score: number;
  benchmark_eval_dataset?: string | null;
  benchmark_score?: number | null;
}

export interface AIModelCardCreate extends AIModelCardBase {}

export interface AIModelCard extends AIModelCardBase {
  id: number;
  organization_id: number;
  ai_system_id: number;
  created_at: string;
  updated_at: string;
}

export interface AIDeploymentApprovalCreate {
  target_environment: string;
  risk_acceptance_justification: string;
  human_oversight_measures: string;
}

export interface AIDeploymentApprovalReviewRequest {
  decision: 'APPROVED' | 'REJECTED';
  reviewer_notes?: string | null;
}

export interface AIDeploymentApproval {
  id: number;
  organization_id: number;
  ai_system_id: number;
  requested_by_id: number;
  reviewed_by_id?: number | null;
  target_environment: string;
  approval_status: AIApprovalStatus;
  risk_acceptance_justification: string;
  human_oversight_measures: string;
  reviewer_notes?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  requested_by?: User | null;
  reviewed_by?: User | null;
}

export interface AISystemBase {
  system_code: string;
  name: string;
  description?: string | null;
  system_type: AISystemType;
  regulatory_tier: AIRegulatoryTier;
  autonomy_level: AIAutonomyLevel;
  data_sensitivity: AIDataSensitivity;
  hosting_type: AIHostingType;
  foundation_model_name?: string | null;
  model_version?: string | null;
  training_data_cutoff?: string | null;
  parameters_billion?: number | null;
  context_window_tokens?: number | null;
  compute_flops_exponent?: number | null;
  business_process_id?: number | null;
  vendor_id?: number | null;
  remediation_plan_id?: number | null;
}

export interface AISystemCreate extends AISystemBase {}

export interface AISystemUpdate {
  name?: string;
  description?: string | null;
  system_type?: AISystemType;
  regulatory_tier?: AIRegulatoryTier;
  autonomy_level?: AIAutonomyLevel;
  data_sensitivity?: AIDataSensitivity;
  hosting_type?: AIHostingType;
  foundation_model_name?: string | null;
  model_version?: string | null;
  training_data_cutoff?: string | null;
  parameters_billion?: number | null;
  context_window_tokens?: number | null;
  compute_flops_exponent?: number | null;
  business_process_id?: number | null;
  vendor_id?: number | null;
  remediation_plan_id?: number | null;
}

export interface AISystemStatusUpdate {
  lifecycle_state: AILifecycleState;
  notes?: string | null;
}

export interface AISystem extends AISystemBase {
  id: number;
  organization_id: number;
  lifecycle_state: AILifecycleState;
  algorithmic_risk_index: number;
  eu_compliance_score: number;
  is_prohibited_practice: boolean;
  requires_conformity_assessment: boolean;
  owner_id: number;
  approved_by_id?: number | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
  owner?: User | null;
  approved_by?: User | null;
  model_cards?: AIModelCard[];
  deployment_approvals?: AIDeploymentApproval[];
}

export interface AIIndexCalculateRequest {
  regulatory_tier: AIRegulatoryTier;
  autonomy_level: AIAutonomyLevel;
  data_sensitivity: AIDataSensitivity;
  process_tier?: string | null;
  hallucination_rate_percent?: number;
  prompt_injection_resistance_score?: number;
}

export interface AIIndexCalculateResponse {
  base_risk: number;
  autonomy_multiplier: number;
  process_tier_multiplier: number;
  safety_penalty: number;
  algorithmic_risk_index: number;
}

export interface AIPostureSummaryResponse {
  total_ai_systems: number;
  high_risk_systems: number;
  prohibited_systems: number;
  production_systems: number;
  pending_approvals_count: number;
  average_algorithmic_risk_index: number;
  tier_distribution: Record<string, number>;
  lifecycle_distribution: Record<string, number>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Phase 16: Continuous Privacy Governance & RoPA Inventory (PRIVACY-GRC)
// ═══════════════════════════════════════════════════════════════════════════════

export type DataSensitivityLevel =
  | 'PUBLIC'
  | 'INTERNAL'
  | 'CONFIDENTIAL'
  | 'RESTRICTED_PII'
  | 'SPECIAL_CATEGORY';

export type ProcessingLegalBasis =
  | 'CONSENT'
  | 'CONTRACT_PERFORMANCE'
  | 'LEGAL_OBLIGATION'
  | 'VITAL_INTERESTS'
  | 'PUBLIC_TASK'
  | 'LEGITIMATE_INTERESTS';

export type ProcessingLifecycleState =
  | 'DRAFT'
  | 'DPO_REVIEW'
  | 'ACTIVE'
  | 'SUSPENDED'
  | 'ARCHIVED'
  | 'RETIRED';

export type TransferMechanism =
  | 'NONE_INTRA_EEA'
  | 'ADEQUACY_DECISION'
  | 'STANDARD_CONTRACTUAL_CLAUSES_SCC'
  | 'BINDING_CORPORATE_RULES_BCR'
  | 'DEROGATION_EXPLICIT_CONSENT'
  | 'NO_SAFEGUARDS_PROHIBITED';

export type JurisdictionRiskTier =
  | 'ADEQUATE_EEA_EQUIVALENT'
  | 'MODERATE_SAFEGUARDS_REQUIRED'
  | 'HIGH_RISK_SURVEILLANCE'
  | 'RESTRICTED_EMBARGOED';

export type DPIARiskBand =
  | 'LOW'
  | 'MODERATE'
  | 'HIGH'
  | 'VERY_HIGH'
  | 'CRITICAL';

export type PrivacyApprovalStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED';

// ─── 1. Data Assets Contracts ──────────────────────────────────────────────────

export interface DataAssetBase {
  asset_code: string;
  name: string;
  description?: string | null;
  data_sensitivity_level: DataSensitivityLevel;
  data_volume_range: string;
  storage_type: string;
  hosting_jurisdiction: string;
  is_encrypted_at_rest: boolean;
  is_encrypted_in_transit: boolean;
  is_pseudonymized: boolean;
  retention_period_months?: number | null;
  business_process_id?: number | null;
  ai_system_id?: number | null;
  vendor_id?: number | null;
}

export interface DataAssetCreate extends DataAssetBase {}

export interface DataAssetUpdate {
  name?: string;
  description?: string | null;
  data_sensitivity_level?: DataSensitivityLevel;
  data_volume_range?: string;
  storage_type?: string;
  hosting_jurisdiction?: string;
  is_encrypted_at_rest?: boolean;
  is_encrypted_in_transit?: boolean;
  is_pseudonymized?: boolean;
  retention_period_months?: number | null;
  business_process_id?: number | null;
  ai_system_id?: number | null;
  vendor_id?: number | null;
}

export interface DataAsset extends DataAssetBase {
  id: number;
  organization_id: number;
  owner_id: number;
  created_at: string;
  updated_at: string;
  owner?: User | null;
}

// ─── 2. Processing Activities (RoPA) Contracts ────────────────────────────────

export interface ProcessingActivityBase {
  activity_code: string;
  name: string;
  purpose_description: string;
  legal_basis: ProcessingLegalBasis;
  data_subject_categories: string;
  personal_data_categories: string;
  is_special_category_data: boolean;
  is_automated_decision_making: boolean;
  is_large_scale_monitoring: boolean;
  is_vulnerable_subjects: boolean;
  is_cross_border_transfer: boolean;
  transfer_mechanism: TransferMechanism;
  destination_country?: string | null;
  security_measures_summary?: string | null;
  data_controller_name?: string | null;
  business_process_id?: number | null;
  ai_system_id?: number | null;
  vendor_id?: number | null;
}

export interface ProcessingActivityCreate extends ProcessingActivityBase {}

export interface ProcessingActivityUpdate {
  name?: string;
  purpose_description?: string;
  legal_basis?: ProcessingLegalBasis;
  data_subject_categories?: string;
  personal_data_categories?: string;
  is_special_category_data?: boolean;
  is_automated_decision_making?: boolean;
  is_large_scale_monitoring?: boolean;
  is_vulnerable_subjects?: boolean;
  is_cross_border_transfer?: boolean;
  transfer_mechanism?: TransferMechanism;
  destination_country?: string | null;
  security_measures_summary?: string | null;
  data_controller_name?: string | null;
  business_process_id?: number | null;
  ai_system_id?: number | null;
  vendor_id?: number | null;
}

export interface ProcessingActivityStatusUpdate {
  lifecycle_state: ProcessingLifecycleState;
  notes?: string | null;
}

export interface ProcessingActivity extends ProcessingActivityBase {
  id: number;
  organization_id: number;
  lifecycle_state: ProcessingLifecycleState;
  dpo_approval_status: PrivacyApprovalStatus;
  owner_id: number;
  approved_by_dpo_id?: number | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
  owner?: User | null;
  approved_by_dpo?: User | null;
  dpia_assessments?: DPIAAssessment[];
  transfer_assessments?: DataTransferAssessment[];
}

// ─── 3. DPIA Assessment Contracts ─────────────────────────────────────────────

export interface DPIABase {
  assessment_code: string;
  processing_activity_id: number;
  necessity_proportionality_score: number;
  data_subject_rights_score: number;
  safeguards_mitigation_score: number;
  automated_decision_making_risk: boolean;
  large_scale_monitoring_risk: boolean;
  vulnerable_subjects_risk: boolean;
  prior_consultation_required: boolean;
  remediation_plan_id?: number | null;
}

export interface DPIACreate extends DPIABase {}

export interface DPIAUpdate {
  necessity_proportionality_score?: number;
  data_subject_rights_score?: number;
  safeguards_mitigation_score?: number;
  automated_decision_making_risk?: boolean;
  large_scale_monitoring_risk?: boolean;
  vulnerable_subjects_risk?: boolean;
  prior_consultation_required?: boolean;
  remediation_plan_id?: number | null;
}

export interface DPIAReviewRequest {
  decision: PrivacyApprovalStatus;
  recommendation_notes: string;
}

export interface DPIAAssessment extends DPIABase {
  id: number;
  organization_id: number;
  inherent_risk_score: number;
  residual_risk_score: number;
  risk_band: DPIARiskBand;
  dpo_consultation_status: PrivacyApprovalStatus;
  dpo_recommendation_notes?: string | null;
  dpo_reviewed_by_id?: number | null;
  dpo_reviewed_at?: string | null;
  created_by_id: number;
  created_at: string;
  updated_at: string;
  created_by?: User | null;
  dpo_reviewed_by?: User | null;
}

// ─── 4. Data Transfer Assessment Contracts ────────────────────────────────────

export interface DataTransferBase {
  transfer_code: string;
  processing_activity_id: number;
  source_country: string;
  destination_country: string;
  destination_jurisdiction_tier: JurisdictionRiskTier;
  transfer_mechanism: TransferMechanism;
  supplementary_safeguards_description?: string | null;
  supplementary_measures_score: number;
  government_access_risk_score: number;
  legal_remedies_score: number;
  audit_notes?: string | null;
}

export interface DataTransferCreate extends DataTransferBase {}

export interface DataTransferUpdate {
  destination_country?: string;
  destination_jurisdiction_tier?: JurisdictionRiskTier;
  transfer_mechanism?: TransferMechanism;
  supplementary_safeguards_description?: string | null;
  supplementary_measures_score?: number;
  government_access_risk_score?: number;
  legal_remedies_score?: number;
  audit_notes?: string | null;
}

export interface DataTransferReviewRequest {
  decision: PrivacyApprovalStatus;
  reviewer_notes: string;
}

export interface DataTransferAssessment extends DataTransferBase {
  id: number;
  organization_id: number;
  transfer_risk_index: number;
  approval_status: PrivacyApprovalStatus;
  requested_by_id: number;
  approved_by_id?: number | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
  requested_by?: User | null;
  approved_by?: User | null;
}

// ─── 5. Posture & Calculation Preview Contracts ───────────────────────────────

export interface PrivacyPostureSummaryResponse {
  total_data_assets: number;
  total_processing_activities: number;
  active_ropa_count: number;
  high_risk_processing_count: number;
  cross_border_transfers_count: number;
  pending_dpia_approvals: number;
  pending_transfer_approvals: number;
  average_residual_risk_score: number;
  risk_band_distribution: Record<string, number>;
  legal_basis_distribution: Record<string, number>;
  sensitivity_distribution: Record<string, number>;
}

export interface DPIACalculatePreviewRequest {
  sensitivity_level?: DataSensitivityLevel;
  volume_tier?: string;
  is_special_category?: boolean;
  automated_decision_making_risk?: boolean;
  large_scale_monitoring_risk?: boolean;
  vulnerable_subjects_risk?: boolean;
  safeguards_mitigation_score?: number;
  has_threat_exposure?: boolean;
}

export interface DPIACalculatePreviewResponse {
  inherent_risk_score: number;
  residual_risk_score: number;
  risk_band: DPIARiskBand;
  prior_consultation_required: boolean;
}

export interface DataTransferCalculatePreviewRequest {
  destination_jurisdiction_tier?: JurisdictionRiskTier;
  transfer_mechanism?: TransferMechanism;
  supplementary_measures_score?: number;
}

export interface DataTransferCalculatePreviewResponse {
  transfer_risk_index: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Phase 17: Software Supply Chain & SBOM Governance (SUPPLYCHAIN-GRC)
// ═══════════════════════════════════════════════════════════════════════════════

export type SoftwareProductType =
  | 'INTERNAL_APPLICATION'
  | 'MICROSERVICE'
  | 'COTS_SOFTWARE'
  | 'OPEN_SOURCE_LIBRARY'
  | 'EMBEDDED_FIRMWARE'
  | 'CLOUD_SERVICE';

export type ProductLifecycleState =
  | 'DRAFT'
  | 'ACTIVE'
  | 'DEPRECATED'
  | 'RETIRED';

export type SupplyChainRiskBand =
  | 'LOW'
  | 'MODERATE'
  | 'HIGH'
  | 'CRITICAL';

export type SBOMFormat =
  | 'CYCLONEDX_JSON'
  | 'SPDX_JSON'
  | 'SWID_XML'
  | 'CUSTOM_JSON';

export type SBOMStatus =
  | 'ACTIVE'
  | 'SUPERSEDED'
  | 'ARCHIVED';

export type PackageEcosystem =
  | 'NPM'
  | 'PYPI'
  | 'MAVEN'
  | 'GO'
  | 'CARGO'
  | 'NUGET'
  | 'RUBYGEMS'
  | 'COMPOSER'
  | 'DEBIAN'
  | 'ALPINE'
  | 'DOCKER'
  | 'GENERIC';

export type LicenseRiskCategory =
  | 'PERMISSIVE'
  | 'WEAK_COPYLEFT'
  | 'STRONG_COPYLEFT'
  | 'PROHIBITED'
  | 'UNCLASSIFIED';

export type SupplyChainApprovalStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'REVOKED';

// ─── 1. Software Products ─────────────────────────────────────────────────────

export interface SoftwareProductBase {
  product_code: string;
  name: string;
  description?: string | null;
  product_type: SoftwareProductType;
  criticality_tier: BusinessCriticality;
  version_tag: string;
  repository_url?: string | null;
  build_pipeline_url?: string | null;
  business_process_id?: number | null;
  ai_system_id?: number | null;
  vendor_id?: number | null;
  remediation_plan_id?: number | null;
}

export interface SoftwareProductCreate extends SoftwareProductBase {}

export interface SoftwareProductUpdate {
  name?: string;
  description?: string | null;
  criticality_tier?: BusinessCriticality;
  version_tag?: string;
  repository_url?: string | null;
  build_pipeline_url?: string | null;
  business_process_id?: number | null;
  ai_system_id?: number | null;
  vendor_id?: number | null;
  remediation_plan_id?: number | null;
}

export interface SoftwareProductStatusUpdate {
  status: ProductLifecycleState;
  notes?: string | null;
}

export interface SoftwareProduct extends SoftwareProductBase {
  id: number;
  organization_id: number;
  lifecycle_state: ProductLifecycleState;
  owner_id: number;
  supply_chain_exposure_index: number;
  risk_band: SupplyChainRiskBand;
  created_at: string;
  updated_at: string;
  owner?: User | null;
  sboms?: SBOMDocument[];
}

// ─── 2. SBOM Documents ────────────────────────────────────────────────────────

export interface SBOMDocumentBase {
  sbom_code: string;
  format: SBOMFormat;
  spec_version: string;
  author_name?: string | null;
  tool_name?: string | null;
  sha256_hash: string;
  raw_payload?: Record<string, any> | null;
}

export interface SBOMDocumentCreate extends SBOMDocumentBase {}

export interface SBOMDocument extends SBOMDocumentBase {
  id: number;
  organization_id: number;
  software_product_id: number;
  status: SBOMStatus;
  ingested_by_id: number;
  total_components_count: number;
  vulnerable_components_count: number;
  prohibited_licenses_count: number;
  created_at: string;
  updated_at: string;
  ingested_by?: User | null;
  components?: SoftwareComponent[];
}

// ─── 3. Software Components ───────────────────────────────────────────────────

export interface SoftwareComponentBase {
  purl?: string | null;
  name: string;
  version: string;
  ecosystem: PackageEcosystem;
  declared_license?: string | null;
  license_category: LicenseRiskCategory;
  is_direct_dependency: boolean;
  dependency_depth: number;
  is_license_prohibited: boolean;
  supplier_name?: string | null;
}

export interface SoftwareComponentCreate extends SoftwareComponentBase {}

export interface SoftwareComponent extends SoftwareComponentBase {
  id: number;
  organization_id: number;
  sbom_document_id: number;
  inherent_vulnerability_score: number;
  component_risk_index: number;
  risk_band: SupplyChainRiskBand;
  vulnerabilities_count: number;
  is_exempted: boolean;
  created_at: string;
  updated_at: string;
  vulnerability_links?: ComponentVulnerabilityLink[];
}

// ─── 4. Component Vulnerability Links ──────────────────────────────────────────

export interface ComponentVulnerabilityLinkBase {
  vulnerability_id: number;
  is_exploitable_in_context: boolean;
  reachability_status?: string | null;
  fix_available: boolean;
  analysis_notes?: string | null;
}

export interface ComponentVulnerabilityLinkCreate extends ComponentVulnerabilityLinkBase {}

export interface ComponentVulnerabilityLink extends ComponentVulnerabilityLinkBase {
  id: number;
  organization_id: number;
  component_id: number;
  linked_by_id: number;
  created_at: string;
  linked_by?: User | null;
  vulnerability?: VulnerabilityExposure | null;
}

// ─── 5. License Policies & Exemptions ──────────────────────────────────────────

export interface LicenseCompliancePolicyBase {
  license_name: string;
  spdx_identifier?: string | null;
  risk_category: LicenseRiskCategory;
  is_strictly_prohibited: boolean;
  justification_required: boolean;
}

export interface LicenseCompliancePolicyCreate extends LicenseCompliancePolicyBase {}

export interface LicenseCompliancePolicy extends LicenseCompliancePolicyBase {
  id: number;
  organization_id: number;
  created_at: string;
  updated_at: string;
}

export interface SupplyChainExemptionBase {
  exemption_code: string;
  reason: string;
  compensating_controls: string;
  expires_at?: string | null;
  component_id?: number | null;
  software_product_id?: number | null;
}

export interface SupplyChainExemptionCreate extends SupplyChainExemptionBase {}

export interface SupplyChainExemptionReview {
  decision: SupplyChainApprovalStatus;
  reviewer_notes: string;
}

export interface SupplyChainExemption extends SupplyChainExemptionBase {
  id: number;
  organization_id: number;
  approval_status: SupplyChainApprovalStatus;
  requested_by_id: number;
  reviewed_by_id?: number | null;
  reviewed_at?: string | null;
  reviewer_notes?: string | null;
  created_at: string;
  updated_at: string;
  requested_by?: User | null;
  reviewed_by?: User | null;
}

// ─── 6. Preview & Posture Telemetry ───────────────────────────────────────────

export interface ComponentCalculatePreviewRequest {
  cvss_scores?: number[];
  exploitability_flags?: boolean[];
  epss_scores?: number[];
  is_cisa_kev?: boolean;
  license_risk?: LicenseRiskCategory;
  dependency_depth?: number;
  is_exempted?: boolean;
}

export interface ComponentCalculatePreviewResponse {
  inherent_vulnerability_score: number;
  depth_multiplier: number;
  license_penalty: number;
  component_risk_index: number;
  risk_band: SupplyChainRiskBand;
}

export interface ProductCalculatePreviewRequest {
  component_risk_indices?: number[];
}

export interface ProductCalculatePreviewResponse {
  supply_chain_exposure_index: number;
  risk_band: SupplyChainRiskBand;
}

export interface SupplyChainPostureSummaryResponse {
  total_products: number;
  active_products_count: number;
  total_components_cataloged: number;
  vulnerable_components_count: number;
  prohibited_license_violations: number;
  pending_exemptions_count: number;
  average_exposure_index: number;
  risk_band_distribution: Record<string, number>;
  product_type_distribution: Record<string, number>;
  ecosystem_distribution: Record<string, number>;
}

// ============================================================================
// PHASE 18: CLOUDSEC-GRC — CLOUD SECURITY POSTURE MANAGEMENT (CSPM)
// ============================================================================

export type CloudProvider = 'AWS' | 'AZURE' | 'GCP' | 'OCI' | 'ALIBABA';

export type CloudAssetType =
  | 'S3_BUCKET'
  | 'IAM_ROLE'
  | 'EC2_INSTANCE'
  | 'KUBERNETES_CLUSTER'
  | 'RDS_DATABASE'
  | 'KEY_VAULT'
  | 'SECURITY_GROUP'
  | 'SERVERLESS_FUNCTION'
  | 'CONTAINER_REGISTRY'
  | 'VIRTUAL_NETWORK';

export type CloudEnvironment = 'PRODUCTION' | 'STAGING' | 'DEVELOPMENT' | 'SANDBOX';
export type CloudCriticality = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type CloudPostureStatus = 'COMPLIANT' | 'NON_COMPLIANT' | 'DEVIATED' | 'UNASSESSED';
export type CloudLifecycleState = 'ACTIVE' | 'PROVISIONING' | 'MAINTENANCE' | 'DECOMMISSIONED';

export type BenchmarkFramework =
  | 'CIS_AWS_FOUNDATIONS'
  | 'CIS_AZURE_FOUNDATIONS'
  | 'CIS_GCP_FOUNDATIONS'
  | 'NIST_SP_800_53_CLOUD'
  | 'SOC2_CLOUD_SECURITY';

export type RuleSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type EvaluationStatus = 'PASSED' | 'FAILED' | 'SUPPRESSED' | 'REMEDIATED';
export type DriftSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type DriftStatus = 'DETECTED' | 'ACCEPTED_CHANGE' | 'REMEDIATING' | 'REVERTED';
export type DataAccessScope = 'FULL_DATASTORE' | 'RESTRICTED_READ' | 'METADATA_ONLY';
export type BlastRadiusBand = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';

export interface CloudAssetBase {
  asset_code: string;
  provider: CloudProvider;
  account_id: string;
  region: string;
  resource_type: CloudAssetType;
  resource_arn: string;
  resource_name: string;
  environment: CloudEnvironment;
  criticality: CloudCriticality;
  is_internet_facing: boolean;
  encryption_enabled: boolean;
  software_product_id?: number | null;
  remediation_plan_id?: number | null;
  tags?: string | null;
  configuration_metadata?: string | null;
}

export interface CloudAssetCreate extends CloudAssetBase {}

export interface CloudAssetUpdate {
  resource_name?: string;
  environment?: CloudEnvironment;
  criticality?: CloudCriticality;
  is_internet_facing?: boolean;
  encryption_enabled?: boolean;
  software_product_id?: number | null;
  remediation_plan_id?: number | null;
  tags?: string | null;
  configuration_metadata?: string | null;
}

export interface CloudAssetStatusUpdate {
  lifecycle_state: CloudLifecycleState;
  notes?: string;
}

export interface CloudAsset extends CloudAssetBase {
  id: number;
  organization_id: number;
  posture_status: CloudPostureStatus;
  posture_score: number;
  blast_radius_score: number;
  lifecycle_state: CloudLifecycleState;
  owner_id: number;
  created_at: string;
  updated_at: string;
}

export interface CloudBenchmarkRuleBase {
  rule_code: string;
  title: string;
  description: string;
  section: string;
  severity: RuleSeverity;
  rationale?: string | null;
  remediation_guidance?: string | null;
  control_id?: number | null;
}

export interface CloudBenchmarkRuleCreate extends CloudBenchmarkRuleBase {
  benchmark_id: number;
}

export interface CloudBenchmarkRule extends CloudBenchmarkRuleBase {
  id: number;
  benchmark_id: number;
  created_at: string;
}

export interface CloudSecurityBenchmarkBase {
  benchmark_code: string;
  name: string;
  version: string;
  framework: BenchmarkFramework;
  provider: CloudProvider;
  description?: string | null;
  is_active: boolean;
}

export interface CloudSecurityBenchmarkCreate extends CloudSecurityBenchmarkBase {}

export interface CloudSecurityBenchmark extends CloudSecurityBenchmarkBase {
  id: number;
  total_rules_count: number;
  rules: CloudBenchmarkRule[];
  created_at: string;
}

export interface CloudSecurityFindingCreate {
  finding_code: string;
  cloud_asset_id: number;
  rule_id: number;
  evaluation_status: EvaluationStatus;
  severity: RuleSeverity;
  actual_value?: string | null;
  expected_value?: string | null;
  remediation_plan_id?: number | null;
}

export interface CloudSecurityFinding {
  id: number;
  organization_id: number;
  finding_code: string;
  cloud_asset_id: number;
  rule_id: number;
  evaluation_status: EvaluationStatus;
  severity: RuleSeverity;
  risk_score: number;
  actual_value?: string | null;
  expected_value?: string | null;
  remediation_plan_id?: number | null;
  evaluated_at: string;
  resolved_at?: string | null;
}

export interface CloudConfigurationDriftCreate {
  drift_code: string;
  cloud_asset_id: number;
  attribute_path: string;
  baseline_value: string;
  drifted_value: string;
  drift_severity: DriftSeverity;
}

export interface CloudConfigurationDrift {
  id: number;
  organization_id: number;
  drift_code: string;
  cloud_asset_id: number;
  attribute_path: string;
  baseline_value: string;
  drifted_value: string;
  drift_severity: DriftSeverity;
  drift_score: number;
  status: DriftStatus;
  detected_at: string;
  resolved_at?: string | null;
}

export interface CloudIAMBlastRadiusCreate {
  analysis_code: string;
  cloud_asset_id: number;
  iam_principal_arn: string;
  effective_permissions_count: number;
  admin_privilege_granted: boolean;
  cross_account_access: boolean;
  data_access_scope: DataAccessScope;
}

export interface CloudIAMBlastRadiusPreviewRequest {
  effective_permissions_count: number;
  admin_privilege_granted: boolean;
  cross_account_access: boolean;
  data_access_scope: DataAccessScope;
}

export interface CloudIAMBlastRadiusPreviewResponse {
  blast_radius_index: number;
  risk_band: BlastRadiusBand;
  breakdown: Record<string, number>;
}

export interface CloudIAMBlastRadius {
  id: number;
  organization_id: number;
  analysis_code: string;
  cloud_asset_id: number;
  iam_principal_arn: string;
  effective_permissions_count: number;
  admin_privilege_granted: boolean;
  cross_account_access: boolean;
  data_access_scope: DataAccessScope;
  blast_radius_index: number;
  risk_band: BlastRadiusBand;
  analyzed_at: string;
}

export interface CloudPostureSummaryResponse {
  total_cloud_assets: number;
  compliant_assets_count: number;
  non_compliant_assets_count: number;
  deviated_assets_count: number;
  total_open_findings: number;
  critical_findings_count: number;
  active_drifts_count: number;
  average_posture_score: number;
  average_blast_radius_score: number;
  provider_distribution: Record<string, number>;
  environment_distribution: Record<string, number>;
}

// ============================================================================
// PHASE 19: IDENTITY-GRC — IDENTITY GOVERNANCE & ADMINISTRATION (IGA)
// ============================================================================

export type IdentityType =
  | 'WORKFORCE_EMPLOYEE'
  | 'CONTRACTOR'
  | 'SERVICE_ACCOUNT'
  | 'MACHINE_WORKLOAD'
  | 'EXTERNAL_PARTNER';

export type EmploymentStatus = 'ACTIVE' | 'LEAVE' | 'TERMINATED' | 'SUSPENDED';
export type IdentityRiskBand = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
export type SystemType =
  | 'ACTIVE_DIRECTORY'
  | 'OKTA'
  | 'AWS_IAM'
  | 'AZURE_RBAC'
  | 'DATABASE_ROLE'
  | 'SAAS_APPLICATION';

export type AssignmentType = 'DIRECT' | 'ROLE_INHERITED' | 'JIT_ELEVATION';
export type CampaignType =
  | 'PERIODIC_USER_ACCESS_REVIEW'
  | 'PRIVILEGED_ACCESS_CERTIFICATION'
  | 'SOD_CONFLICT_REVIEW'
  | 'TERMINATION_AUDIT';

export type CampaignStatus = 'DRAFT' | 'ACTIVE' | 'IN_REVIEW' | 'FINALIZED' | 'CANCELLED';
export type CertificationDecision = 'PENDING' | 'CERTIFIED' | 'REVOKED' | 'EXCEPTION_APPROVED';
export type JITApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'REVOKED';
export type TrustLevel = 'HIGH_TRUST' | 'CONDITIONAL_TRUST' | 'LOW_TRUST' | 'UNTRUSTED';
export type SoDPolicySeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM';
export type SoDViolationStatus = 'ACTIVE_VIOLATION' | 'EXCEPTION_GRANTED' | 'REMEDIATED';

export interface GovernedIdentityBase {
  identity_code: string;
  email: string;
  full_name: string;
  identity_type: IdentityType;
  department?: string | null;
  employment_status: EmploymentStatus;
  is_privileged: boolean;
  mfa_enabled: boolean;
  cloud_asset_id?: number | null;
  user_id?: number | null;
}

export interface GovernedIdentityCreate extends GovernedIdentityBase {}

export interface GovernedIdentityUpdate {
  full_name?: string;
  department?: string | null;
  employment_status?: EmploymentStatus;
  is_privileged?: boolean;
  mfa_enabled?: boolean;
  cloud_asset_id?: number | null;
  user_id?: number | null;
}

export interface GovernedIdentity extends GovernedIdentityBase {
  id: number;
  organization_id: number;
  risk_score: number;
  risk_band: IdentityRiskBand;
  created_at: string;
  updated_at: string;
}

export interface IdentityEntitlementBase {
  entitlement_code: string;
  name: string;
  system_type: SystemType;
  resource_name: string;
  permission_scope: string;
  is_privileged: boolean;
  is_high_risk: boolean;
  risk_weight: number;
  description?: string | null;
}

export interface IdentityEntitlementCreate extends IdentityEntitlementBase {}

export interface IdentityEntitlement extends IdentityEntitlementBase {
  id: number;
  organization_id: number;
  created_at: string;
}

export interface EntitlementAssignmentCreate {
  entitlement_id: number;
  assignment_type?: AssignmentType;
  expires_at?: string | null;
}

export interface EntitlementAssignment {
  id: number;
  organization_id: number;
  identity_id: number;
  entitlement_id: number;
  assigned_at: string;
  expires_at?: string | null;
  assignment_type: AssignmentType;
  is_active: boolean;
  entitlement?: IdentityEntitlement;
}

export interface AccessCertificationCampaignCreate {
  campaign_code: string;
  title: string;
  description?: string | null;
  campaign_type?: CampaignType;
  deadline: string;
}

export interface AccessCertificationCampaign {
  id: number;
  organization_id: number;
  campaign_code: string;
  title: string;
  description?: string | null;
  campaign_type: CampaignType;
  status: CampaignStatus;
  total_items_count: number;
  certified_items_count: number;
  revoked_items_count: number;
  deadline: string;
  finalized_at?: string | null;
  created_by_id: number;
  created_at: string;
  updated_at: string;
}

export interface AccessCertificationItemReview {
  decision: CertificationDecision;
  decision_justification?: string | null;
  remediation_plan_id?: number | null;
}

export interface AccessCertificationItem {
  id: number;
  organization_id: number;
  campaign_id: number;
  identity_id: number;
  entitlement_id: number;
  decision: CertificationDecision;
  decision_justification?: string | null;
  reviewer_id?: number | null;
  reviewed_at?: string | null;
  is_sod_violation: boolean;
  remediation_plan_id?: number | null;
  identity?: GovernedIdentity;
  entitlement?: IdentityEntitlement;
}

export interface JITAccessRequestCreate {
  request_code: string;
  identity_id: number;
  entitlement_id: number;
  requested_duration_minutes: number;
  business_justification: string;
}

export interface JITAccessReviewRequest {
  approved: boolean;
  notes?: string;
}

export interface JITAccessRequest {
  id: number;
  organization_id: number;
  request_code: string;
  identity_id: number;
  entitlement_id: number;
  requested_duration_minutes: number;
  business_justification: string;
  approval_status: JITApprovalStatus;
  requested_by_id: number;
  approved_by_id?: number | null;
  valid_from?: string | null;
  valid_until?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ZeroTrustAssessmentCreate {
  assessment_code: string;
  device_health_score: number;
  auth_strength_score: number;
  context_risk_score: number;
  behavioral_anomaly_score: number;
}

export interface ZeroTrustPreviewRequest {
  device_health_score: number;
  auth_strength_score: number;
  context_risk_score: number;
  behavioral_anomaly_score: number;
}

export interface ZeroTrustPreviewResponse {
  zero_trust_assurance_score: number;
  trust_level: TrustLevel;
  breakdown: Record<string, number>;
}

export interface ZeroTrustAssessment {
  id: number;
  organization_id: number;
  assessment_code: string;
  identity_id: number;
  device_health_score: number;
  auth_strength_score: number;
  context_risk_score: number;
  behavioral_anomaly_score: number;
  zero_trust_assurance_score: number;
  trust_level: TrustLevel;
  evaluated_at: string;
}

export interface SoDConflictPolicyCreate {
  policy_code: string;
  name: string;
  entitlement_a_id: number;
  entitlement_b_id: number;
  severity?: SoDPolicySeverity;
  description?: string | null;
}

export interface SoDConflictPolicy {
  id: number;
  organization_id: number;
  policy_code: string;
  name: string;
  entitlement_a_id: number;
  entitlement_b_id: number;
  severity: SoDPolicySeverity;
  description?: string | null;
  created_at: string;
}

export interface SoDConflictViolation {
  id: number;
  organization_id: number;
  identity_id: number;
  policy_id: number;
  status: SoDViolationStatus;
  remediation_plan_id?: number | null;
  detected_at: string;
  resolved_at?: string | null;
  policy?: SoDConflictPolicy;
}

export interface IdentityPostureSummaryResponse {
  total_identities: number;
  privileged_identities_count: number;
  high_risk_identities_count: number;
  active_sod_violations_count: number;
  pending_certifications_count: number;
  pending_jit_requests_count: number;
  average_identity_risk_score: number;
  average_zero_trust_score: number;
  identity_type_distribution: Record<string, number>;
  system_entitlement_distribution: Record<string, number>;
}

// ── Phase 20 Executive Governance & Board Telemetry (EXECUTIVE-GRC) ───────────

export type DossierType =
  | 'BOARD_SUMMARY'
  | 'REGULATORY_SUBMISSION'
  | 'ANNUAL_COMPLIANCE'
  | 'FORENSIC_AUDIT'
  | 'CYBER_INSURANCE';

export type DossierStatus = 'DRAFT' | 'COMPILED' | 'UNDER_REVIEW' | 'FINALIZED';

export type BriefingStatus = 'DRAFT' | 'SUBMITTED_FOR_REVIEW' | 'APPROVED' | 'REJECTED' | 'SUPERSEDED';

export type ExportFormat = 'PDF' | 'JSON' | 'CSV';

export type ArtifactType = 'DOSSIER_PACKAGE' | 'EXECUTIVE_BRIEFING' | 'POSTURE_SNAPSHOT';

export interface DomainPostureItem {
  domain_key: string;
  domain_name: string;
  score: number;
  weight: number;
  status: string;
  summary: Record<string, any>;
}

export interface TopRiskItem {
  id: number;
  title: string;
  risk_category: string;
  inherent_score: number;
  residual_score?: number | null;
  appetite_status: string;
}

export interface CriticalFindingItem {
  id: number;
  title: string;
  severity: string;
  status: string;
  due_date?: string | null;
  owner_name?: string | null;
}

export interface ExecutiveTelemetryResponse {
  overall_posture_score: number;
  inherent_risk_index: number;
  residual_risk_index: number;
  risk_reduction_percentage: number;
  financial_exposure_ale: number;
  var_95_exposure: number;
  financial_appetite_utilization_pct: number;
  audit_readiness_index: number;
  remediation_sla_health_score: number;
  framework_compliance_summary: Record<string, any>;
  domain_posture_breakdown: Record<string, { name: string; score: number; weight: number }>;
  top_risks: TopRiskItem[];
  critical_findings: CriticalFindingItem[];
  calculated_at: string;
}

export interface ExecutiveTrendDataPoint {
  timestamp: string;
  overall_posture_score: number;
  inherent_risk_index: number;
  residual_risk_index: number;
  financial_exposure_ale: number;
  audit_readiness_index: number;
  remediation_sla_health_score: number;
}

export interface ExecutiveTrendsResponse {
  window_days: number;
  data_points: ExecutiveTrendDataPoint[];
}

export interface ExecutiveSnapshotCreate {
  snapshot_code: string;
  notes?: string;
}

export interface ExecutiveSnapshot {
  id: number;
  organization_id: number;
  snapshot_code: string;
  calculated_at: string;
  overall_posture_score: number;
  inherent_risk_index: number;
  residual_risk_index: number;
  financial_exposure_ale: number;
  var_95_exposure: number;
  audit_readiness_index: number;
  remediation_sla_health_score: number;
  framework_compliance_summary: Record<string, any>;
  domain_posture_breakdown: Record<string, { name: string; score: number; weight: number }>;
  top_risks_snapshot: any[];
  critical_findings_snapshot: any[];
  source_manifest: Record<string, any>;
  data_hash_sha256: string;
  created_by_id: number;
  created_at: string;
}

export interface ExecutiveDossierCreate {
  dossier_code: string;
  title: string;
  description?: string;
  dossier_type?: DossierType;
  scope_framework_ids?: number[];
  snapshot_id?: number | null;
  executive_summary?: string;
  regulatory_commentary?: string;
}

export interface ExecutiveDossierUpdate {
  title?: string;
  description?: string;
  scope_framework_ids?: number[];
  snapshot_id?: number | null;
  executive_summary?: string;
  regulatory_commentary?: string;
}

export interface ExecutiveDossier {
  id: number;
  organization_id: number;
  dossier_code: string;
  title: string;
  description?: string | null;
  dossier_type: DossierType;
  status: DossierStatus;
  scope_framework_ids: number[];
  snapshot_id?: number | null;
  executive_summary?: string | null;
  regulatory_commentary?: string | null;
  compiled_sections?: Record<string, any> | null;
  compiled_at?: string | null;
  compiled_by_id?: number | null;
  finalized_at?: string | null;
  finalized_by_id?: number | null;
  created_by_id: number;
  created_at: string;
  updated_at: string;
}

export interface ExecutiveBriefingCreate {
  briefing_code: string;
  title: string;
  reporting_period_start: string;
  reporting_period_end: string;
  snapshot_id: number;
  executive_summary: string;
  key_achievements?: string[];
  emerging_risks?: string[];
  strategic_recommendations?: string;
}

export interface ExecutiveBriefingReview {
  approved: boolean;
  review_notes?: string;
}

export interface ExecutiveBriefing {
  id: number;
  organization_id: number;
  briefing_code: string;
  title: string;
  reporting_period_start: string;
  reporting_period_end: string;
  status: BriefingStatus;
  snapshot_id: number;
  executive_summary: string;
  key_achievements: string[];
  emerging_risks: string[];
  strategic_recommendations?: string | null;
  period_over_period_deltas: Record<string, any>;
  generated_by_id: number;
  approved_by_id?: number | null;
  approved_at?: string | null;
  review_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExecutiveExportArtifact {
  id: number;
  organization_id: number;
  export_code: string;
  export_format: ExportFormat;
  artifact_type: ArtifactType;
  dossier_id?: number | null;
  briefing_id?: number | null;
  snapshot_id?: number | null;
  storage_key: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_checksum: string;
  generated_by_id: number;
  generated_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 21: Regulatory-GRC Types
// ─────────────────────────────────────────────────────────────────────────────

export type RegulatoryAuthorityType = 'GOVERNMENT' | 'STANDARDS_BODY' | 'INDUSTRY_REGULATOR' | 'LEGAL_COURT' | 'INTERNATIONAL_AGENCY';
export type RegulatoryTrustTier = 'OFFICIAL' | 'STANDARD' | 'ADVISORY';
export type RegulatoryEnforceability = 'MANDATORY' | 'VOLUNTARY_STANDARD';
export type RegulatoryMandateStatus = 'DRAFT' | 'ACTIVE' | 'SUPERSEDED' | 'ARCHIVED';
export type RegulatoryApplicability = 'APPLICABLE' | 'EXEMPT' | 'UNDER_EVALUATION';
export type RegulatoryComplianceStatus = 'COMPLIANT' | 'PARTIALLY_COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW';
export type RegulatoryChangeType = 'NEW_MANDATE' | 'AMENDMENT' | 'GUIDANCE_UPDATE' | 'ENFORCEMENT_DATE_SHIFT' | 'REPEAL';
export type RegulatoryChangeSeverity = 'CRITICAL' | 'MAJOR' | 'MINOR' | 'ADMINISTRATIVE';
export type RegulatoryChangeStatus = 'STAGED' | 'VALIDATED' | 'UNDER_REVIEW' | 'REVIEWED' | 'APPROVED' | 'ACTIVE' | 'DISMISSED';
export type RegulatoryImpactLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
export type RegulatoryImpactStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';

export interface RegulatorySource {
  id: number;
  organization_id: number;
  source_code: string;
  name: string;
  authority_type: RegulatoryAuthorityType;
  jurisdiction: string;
  website_url?: string | null;
  trust_tier: RegulatoryTrustTier;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RegulatorySourceCreate {
  source_code: string;
  name: string;
  authority_type: RegulatoryAuthorityType;
  jurisdiction: string;
  website_url?: string;
  trust_tier?: RegulatoryTrustTier;
  description?: string;
  is_active?: boolean;
}

export interface RegulatoryMandate {
  id: number;
  organization_id: number;
  source_id: number;
  mandate_code: string;
  title: string;
  short_name: string;
  legal_citation?: string | null;
  jurisdiction: string;
  enforceability_level: RegulatoryEnforceability;
  status: RegulatoryMandateStatus;
  framework_id?: number | null;
  description?: string | null;
  effective_date?: string | null;
  sunset_date?: string | null;
  created_by_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface RegulatoryMandateCreate {
  source_id: number;
  mandate_code: string;
  title: string;
  short_name: string;
  legal_citation?: string;
  jurisdiction: string;
  enforceability_level?: RegulatoryEnforceability;
  status?: RegulatoryMandateStatus;
  framework_id?: number;
  description?: string;
  effective_date?: string;
  sunset_date?: string;
}

export interface RegulatoryObligation {
  id: number;
  organization_id: number;
  mandate_id: number;
  version_id?: number | null;
  obligation_code: string;
  title: string;
  description: string;
  article_reference?: string | null;
  applicability: RegulatoryApplicability;
  organization_control_id?: number | null;
  compliance_status: RegulatoryComplianceStatus;
  created_at: string;
  updated_at: string;
}

export interface RegulatoryObligationCreate {
  mandate_id: number;
  version_id?: number;
  obligation_code: string;
  title: string;
  description: string;
  article_reference?: string;
  applicability?: RegulatoryApplicability;
  organization_control_id?: number;
  compliance_status?: RegulatoryComplianceStatus;
}

export interface RegulatoryChangeEvent {
  id: number;
  organization_id: number;
  mandate_id: number;
  change_code: string;
  title: string;
  change_type: RegulatoryChangeType;
  severity: RegulatoryChangeSeverity;
  status: RegulatoryChangeStatus;
  official_publication_date: string;
  enforcement_date?: string | null;
  source_url?: string | null;
  content_hash_sha256: string;
  raw_summary: string;
  review_notes?: string | null;
  dismissal_reason?: string | null;
  created_by_id: number;
  approved_by_id?: number | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RegulatoryChangeEventCreate {
  mandate_id: number;
  change_code: string;
  title: string;
  change_type?: RegulatoryChangeType;
  severity?: RegulatoryChangeSeverity;
  official_publication_date: string;
  enforcement_date?: string;
  source_url?: string;
  raw_summary: string;
}

export interface RegulatoryChangeReviewRequest {
  impact_level: RegulatoryImpactLevel;
  impacted_control_ids?: number[];
  impacted_policy_ids?: number[];
  gap_analysis_summary: string;
  action_plan?: string;
  review_notes?: string;
}

export interface RegulatoryChangeApproveRequest {
  review_notes?: string;
}

export interface RegulatoryChangeDismissRequest {
  dismissal_reason: string;
}

export interface RegulatoryImpactAssessment {
  id: number;
  organization_id: number;
  change_event_id: number;
  assessment_code: string;
  title: string;
  impact_level: RegulatoryImpactLevel;
  status: RegulatoryImpactStatus;
  impacted_control_ids?: string | null;
  impacted_policy_ids?: string | null;
  gap_analysis_summary: string;
  action_plan?: string | null;
  created_by_id: number;
  reviewed_by_id?: number | null;
  approved_by_id?: number | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 22: Integration-GRC Types
// ─────────────────────────────────────────────────────────────────────────────

export type IntegrationProviderType = 'AWS' | 'AZURE' | 'GCP' | 'GITHUB' | 'GOOGLE' | 'JIRA' | 'OKTA' | 'SERVICENOW' | 'CUSTOM_REST';
export type IntegrationAuthType = 'API_KEY' | 'BEARER_TOKEN' | 'BASIC_AUTH' | 'OAUTH2' | 'STS_ROLE' | 'MUTUAL_TLS';
export type IntegrationConnectionStatus = 'ACTIVE' | 'INACTIVE' | 'ERROR' | 'UNAUTHENTICATED';
export type EvidenceCollectorType = 'AWS_IAM_MFA' | 'AWS_S3_ENCRYPTION' | 'AWS_CLOUDTRAIL_ACTIVE' | 'GITHUB_BRANCH_PROTECTION' | 'GITHUB_CODE_SCANNING' | 'AZURE_USER_MFA' | 'JIRA_INCIDENT_SLA' | 'CUSTOM_SCRIPT';
export type CollectionRunStatus = 'QUEUED' | 'RUNNING' | 'SUCCESS' | 'PARTIAL_FAILURE' | 'FAILED';
export type CollectionValidationStatus = 'RAW' | 'SYNTAX_VALIDATED' | 'SCHEMA_CONFORMANT' | 'VALIDATION_FAILED';

export interface IntegrationProvider {
  id: number;
  provider_type: IntegrationProviderType;
  name: string;
  description?: string | null;
  auth_type: IntegrationAuthType;
  supported_scopes: string[];
  allowed_domains: string[];
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface IntegrationConnection {
  id: number;
  organization_id: number;
  provider_id: number;
  connection_code: string;
  name: string;
  status: IntegrationConnectionStatus;
  base_url?: string | null;
  granted_scopes: string[];
  last_health_check_at?: string | null;
  last_health_status?: string | null;
  last_error_message?: string | null;
  is_credential_configured: boolean;
  created_by_id: number;
  created_at: string;
  updated_at: string;
}

export interface IntegrationConnectionCreate {
  provider_id: number;
  connection_code: string;
  name: string;
  base_url?: string;
  granted_scopes: string[];
}

export interface IntegrationCredentialCreate {
  auth_type: IntegrationAuthType;
  credentials: Record<string, string>;
}

export interface IntegrationCredentialResponse {
  key_id: string;
  auth_type: IntegrationAuthType;
  version: number;
  is_configured: boolean;
  rotated_at?: string | null;
  created_at: string;
}

export interface EvidenceCollectionJob {
  id: number;
  organization_id: number;
  connection_id: number;
  organization_control_id: number;
  evidence_requirement_id?: number | null;
  job_code: string;
  title: string;
  collector_type: EvidenceCollectorType;
  collection_parameters?: Record<string, any> | null;
  frequency_hours: number;
  is_enabled: boolean;
  max_payload_bytes: number;
  last_run_at?: string | null;
  last_run_status?: string | null;
  created_by_id: number;
  created_at: string;
  updated_at: string;
}

export interface EvidenceCollectionJobCreate {
  connection_id: number;
  organization_control_id: number;
  evidence_requirement_id?: number;
  job_code: string;
  title: string;
  collector_type: EvidenceCollectorType;
  collection_parameters?: Record<string, any>;
  frequency_hours?: number;
  is_enabled?: boolean;
  max_payload_bytes?: number;
}

export interface EvidenceCollectionRun {
  id: number;
  organization_id: number;
  job_id: number;
  connection_id: number;
  evidence_item_id?: number | null;
  run_code: string;
  status: CollectionRunStatus;
  started_at: string;
  completed_at?: string | null;
  source_system: string;
  source_identifier: string;
  source_version?: string | null;
  observed_at: string;
  records_collected_count: number;
  payload_sha256: string;
  validation_status: CollectionValidationStatus;
  error_code?: string | null;
  error_message?: string | null;
  provenance_manifest?: Record<string, any> | null;
  triggered_by_id: number;
  created_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 23: Continuous-GRC Types
// ─────────────────────────────────────────────────────────────────────────────

export type ComplianceDriftVector =
  | 'CCM_HEALTH_DEGRADATION'
  | 'INTEGRATION_PIPELINE_FAILURE'
  | 'REGULATORY_CHANGE_EXPOSURE'
  | 'FINDING_SLA_BREACH'
  | 'HARMONIZED_FRAMEWORK_GAP';

export type ComplianceDriftSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type ComplianceDriftStatus = 'OPEN' | 'ACKNOWLEDGED' | 'REMEDIATION_TRIGGERED' | 'RESOLVED' | 'SUPPRESSED';

export interface ContinuousComplianceProfile {
  id: number;
  organization_id: number;
  profile_name: string;
  is_enabled: boolean;
  evaluation_cadence_hours: number;
  drift_critical_threshold: number;
  drift_high_threshold: number;
  min_control_health_score: number;
  max_evidence_age_days: number;
  max_open_finding_sla_breach_count: number;
  auto_trigger_capa_on_critical_drift: boolean;
  last_evaluated_at?: string | null;
  created_by_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ContinuousComplianceProfileUpdate {
  profile_name?: string;
  is_enabled?: boolean;
  evaluation_cadence_hours?: number;
  drift_critical_threshold?: number;
  drift_high_threshold?: number;
  min_control_health_score?: number;
  max_evidence_age_days?: number;
  max_open_finding_sla_breach_count?: number;
  auto_trigger_capa_on_critical_drift?: boolean;
}

export interface ComplianceDriftRecord {
  id: number;
  organization_id: number;
  organization_control_id?: number | null;
  remediation_plan_id?: number | null;
  drift_code: string;
  drift_vector: ComplianceDriftVector;
  severity: ComplianceDriftSeverity;
  status: ComplianceDriftStatus;
  title: string;
  description: string;
  root_cause_metric?: string | null;
  baseline_value?: number | null;
  observed_value?: number | null;
  detected_at: string;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UnifiedAssurancePosture {
  overall_assurance_score: number;
  controls_assurance_score: number;
  evidence_pipeline_score: number;
  regulatory_compliance_score: number;
  remediation_sla_score: number;
  cloud_identity_posture_score: number;
  harmonized_frameworks_score: number;
  active_drift_count: number;
  critical_drift_count: number;
  pillar_breakdown: Record<string, { score: number; weight: number; status: string }>;
  framework_compliance_breakdown: Record<string, { compliance_rate: number; status: string }>;
  last_evaluated_at: string;
  calculation_version: string;
}

export interface ContinuousAssuranceSnapshotCreate {
  snapshot_code: string;
}

export interface ContinuousAssuranceSnapshot {
  id: number;
  organization_id: number;
  snapshot_code: string;
  captured_at: string;
  overall_assurance_score: number;
  controls_assurance_score: number;
  evidence_pipeline_score: number;
  regulatory_compliance_score: number;
  remediation_sla_score: number;
  cloud_identity_posture_score: number;
  harmonized_frameworks_score: number;
  active_drift_count: number;
  critical_drift_count: number;
  pillar_breakdown: Record<string, any>;
  framework_compliance_breakdown: Record<string, any>;
  data_hash_sha256: string;
  calculation_version: string;
  created_by_id: number;
  created_at: string;
}