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