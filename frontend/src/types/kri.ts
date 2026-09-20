export type KriStatus = 'ACTIVE' | 'INACTIVE' | 'DEPRECATED';

export type KriDirection = 'LOWER_IS_BETTER' | 'HIGHER_IS_BETTER' | 'WITHIN_RANGE';

export type KriFrequency = 'CONTINUOUS' | 'HOURLY' | 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'QUARTERLY';

export type KriSourceType =
  | 'MANUAL'
  | 'AUTOMATED_AGENT'
  | 'CONTINUOUS_MONITORING'
  | 'INTEGRATION_API'
  | 'IMPORT';

export type KriEvaluationStatus =
  | 'WITHIN_APPETITE'
  | 'WARNING_BREACH'
  | 'CRITICAL_BREACH'
  | 'INSUFFICIENT_DATA';

export type BreachStatus =
  | 'DETECTED'
  | 'ACKNOWLEDGED'
  | 'ESCALATED'
  | 'RECOVERED'
  | 'CLOSED';

export type AppetiteStatementStatus =
  | 'DRAFT'
  | 'UNDER_REVIEW'
  | 'APPROVED'
  | 'SUPERSEDED'
  | 'RETIRED';

export interface RiskAppetiteStatement {
  id: number;
  organization_id: number;
  statement_code: string;
  title: string;
  executive_summary: string;
  category_appetites?: Record<string, string>;
  overall_loss_tolerance_pct?: number | null;
  financial_appetite_id?: number | null;
  status: AppetiteStatementStatus;
  effective_from: string;
  effective_to?: string | null;
  review_cadence_months: number;
  created_by_id?: number | null;
  approved_by_id?: number | null;
  approved_at?: string | null;
  approval_justification?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RiskAppetiteStatementCreate {
  statement_code: string;
  title: string;
  executive_summary: string;
  category_appetites?: Record<string, string>;
  overall_loss_tolerance_pct?: number | null;
  financial_appetite_id?: number | null;
  effective_from: string;
  effective_to?: string | null;
  review_cadence_months?: number;
}

export interface RiskAppetiteApprovePayload {
  approval_justification: string;
}

export interface KriThreshold {
  id: number;
  organization_id: number;
  kri_id: number;
  version: number;
  target_value?: number | null;
  warning_threshold?: number | null;
  critical_threshold?: number | null;
  min_acceptable_value?: number | null;
  max_acceptable_value?: number | null;
  effective_from: string;
  effective_to?: string | null;
  rationale?: string | null;
  is_active: boolean;
  created_by_id?: number | null;
  created_at: string;
}

export interface KriThresholdCreate {
  target_value?: number | null;
  warning_threshold?: number | null;
  critical_threshold?: number | null;
  min_acceptable_value?: number | null;
  max_acceptable_value?: number | null;
  effective_from?: string | null;
  effective_to?: string | null;
  rationale?: string | null;
}

export interface KeyRiskIndicator {
  id: number;
  organization_id: number;
  kri_code: string;
  title: string;
  description?: string | null;
  risk_category: string;
  unit_of_measure: string;
  direction: KriDirection;
  frequency: KriFrequency;
  source_type: KriSourceType;
  status: KriStatus;
  owner_id?: number | null;
  current_value?: number | null;
  current_evaluation_status: KriEvaluationStatus;
  last_evaluated_at?: string | null;
  consecutive_normal_readings: number;
  active_threshold?: KriThreshold | null;
  created_at: string;
  updated_at: string;
}

export interface KeyRiskIndicatorCreate {
  kri_code: string;
  title: string;
  description?: string;
  risk_category: string;
  unit_of_measure: string;
  direction?: KriDirection;
  frequency?: KriFrequency;
  source_type?: KriSourceType;
  owner_id?: number;
  initial_threshold?: KriThresholdCreate;
}

export interface KriObservation {
  id: number;
  organization_id: number;
  kri_id: number;
  observed_value: number;
  unit: string;
  observed_at: string;
  ingested_at: string;
  source_type: KriSourceType;
  reporter_id?: number | null;
  source_system?: string | null;
  batch_reference?: string | null;
  raw_payload_hash: string;
  idempotency_key?: string | null;
  created_at: string;
  evaluation_status?: KriEvaluationStatus;
  breach_id?: number | null;
}

export interface KriObservationCreate {
  observed_value: number;
  unit: string;
  observed_at: string;
  source_type?: KriSourceType;
  source_system?: string;
  batch_reference?: string;
  idempotency_key?: string;
}

export interface KriBreachRecord {
  id: number;
  organization_id: number;
  kri_id: number;
  threshold_id?: number | null;
  trigger_observation_id?: number | null;
  breach_code: string;
  status: BreachStatus;
  breach_severity: string;
  initial_observed_value: number;
  peak_value: number;
  detected_at: string;
  acknowledged_at?: string | null;
  acknowledged_by_id?: number | null;
  recovery_detected_at?: string | null;
  closed_at?: string | null;
  closed_by_id?: number | null;
  closure_notes?: string | null;
  escalated_finding_id?: number | null;
  escalated_at?: string | null;
  consecutive_recovery_readings: number;
  last_evaluated_at: string;
  created_at: string;
  updated_at: string;
}

export interface KriBreachAcknowledgePayload {
  notes?: string;
}

export interface KriBreachEscalateFindingPayload {
  organization_control_id: number;
  title?: string;
  description?: string;
  severity?: string;
  recommendation?: string;
}

export interface KriBreachClosePayload {
  closure_notes: string;
}

export interface KriRiskLink {
  id: number;
  organization_id: number;
  kri_id: number;
  risk_id: number;
  correlation_weight: number;
  notes?: string | null;
  linked_at: string;
  linked_by_id?: number | null;
}

export interface KriRiskLinkCreate {
  risk_id: number;
  correlation_weight?: number;
  notes?: string;
}

export interface KriTelemetryOverview {
  total_kris: number;
  active_kris: number;
  within_appetite_count: number;
  warning_breach_count: number;
  critical_breach_count: number;
  open_breaches_count: number;
  stale_kris_count: number;
  latest_appetite_statement?: RiskAppetiteStatement | null;
}
