export type DataSensitivityLevel =
  | 'PUBLIC'
  | 'INTERNAL'
  | 'CONFIDENTIAL'
  | 'RESTRICTED_PII'
  | 'SPECIAL_CATEGORY_SENSITIVE_PHI';

export type DataAssetLifecycle =
  | 'DISCOVERED'
  | 'REGISTERED'
  | 'CLASSIFIED'
  | 'ACTIVE'
  | 'DEPRECATED'
  | 'RETIRED';

export type DataAssetType =
  | 'DATABASE_TABLE'
  | 'DATA_LAKE_BUCKET'
  | 'MESSAGE_STREAM'
  | 'FILE_SHARE'
  | 'SAAS_DATASET'
  | 'AI_TRAINING_CORPUS'
  | 'BACKUP_ARCHIVE'
  | 'API_FEED';

export type DataClassificationSchemeStatus =
  | 'DRAFT'
  | 'PENDING_APPROVAL'
  | 'ACTIVE'
  | 'SUPERSEDED'
  | 'ARCHIVED';

export type DataClassificationApprovalStatus =
  | 'UNCLASSIFIED'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED';

export type DataClassificationRecordStatus =
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'SUPERSEDED';

export type DataClassificationChangeType =
  | 'INITIAL'
  | 'UPGRADE'
  | 'DOWNGRADE'
  | 'REVALIDATION';

export type DataLineageRelationshipType =
  | 'ETL_TRANSFORMATION'
  | 'STREAM_REPLICATION'
  | 'API_SYNDICATION'
  | 'AGGREGATION'
  | 'AI_FEATURE_EXTRACTION'
  | 'BACKUP_SNAPSHOT'
  | 'EXPORT_ARCHIVE';

export type DataLineageStatus =
  | 'PENDING_APPROVAL'
  | 'ACTIVE'
  | 'REVOKED'
  | 'SUPERSEDED';

export type DataDisposalMethod =
  | 'NONE'
  | 'CRYPTOGRAPHIC_ERASURE'
  | 'SECURE_OVERWRITE'
  | 'PHYSICAL_DESTRUCTION'
  | 'ANONYMIZATION_RETENTION'
  | 'ARCHIVAL_COLD_STORAGE';

export type DataCloudHostingRole =
  | 'PRIMARY_STORE'
  | 'REPLICA_STORE'
  | 'BACKUP_ARCHIVE'
  | 'PROCESSING_COMPUTE'
  | 'INGESTION_GATEWAY';

export type DataProcessingUsageRole =
  | 'PRIMARY_SOURCE'
  | 'DERIVED_OUTPUT'
  | 'ANALYTICS_INPUT'
  | 'ARCHIVE_RETENTION'
  | 'VENDOR_TRANSFER';

export type DataControlObjective =
  | 'ENCRYPTION_AT_REST'
  | 'ENCRYPTION_IN_TRANSIT'
  | 'ACCESS_CONTROL'
  | 'DATA_MASKING_PSEUDONYMIZATION'
  | 'RETENTION_DISPOSAL'
  | 'BACKUP_INTEGRITY'
  | 'DLP_MONITORING';

export type DataEvidencePurpose =
  | 'CLASSIFICATION_JUSTIFICATION'
  | 'ENCRYPTION_ATTESTATION'
  | 'LINEAGE_VERIFICATION'
  | 'OWNERSHIP_STEWARDSHIP_ATTESTATION'
  | 'RETENTION_DISPOSAL_CERTIFICATE';

export interface DataClassificationLevel {
  id: number;
  organization_id: number;
  scheme_id: number;
  level_code: string;
  name: string;
  description?: string | null;
  ordinal_rank: number;
  mapped_sensitivity_level: DataSensitivityLevel;
  requires_encryption_at_rest: boolean;
  requires_encryption_in_transit: boolean;
  requires_four_eyes_approval: boolean;
  default_retention_months?: number | null;
  required_disposal_method?: DataDisposalMethod | null;
  created_at: string;
  updated_at: string;
}

export interface DataClassificationLevelCreate {
  level_code: string;
  name: string;
  description?: string;
  ordinal_rank: number;
  mapped_sensitivity_level: DataSensitivityLevel;
  requires_encryption_at_rest?: boolean;
  requires_encryption_in_transit?: boolean;
  requires_four_eyes_approval?: boolean;
  default_retention_months?: number;
  required_disposal_method?: DataDisposalMethod;
}

export interface DataClassificationScheme {
  id: number;
  organization_id: number;
  scheme_code: string;
  name: string;
  description?: string | null;
  version: number;
  status: DataClassificationSchemeStatus;
  is_default: boolean;
  created_by_id: number;
  approved_by_id?: number | null;
  approved_at?: string | null;
  levels: DataClassificationLevel[];
  created_at: string;
  updated_at: string;
}

export interface DataClassificationSchemeCreate {
  scheme_code: string;
  name: string;
  description?: string;
  version?: number;
  is_default?: boolean;
}

export interface GovernedDataAsset {
  id: number;
  organization_id: number;
  asset_code: string;
  name: string;
  description?: string | null;
  asset_type: DataAssetType;
  lifecycle_state: DataAssetLifecycle;
  data_sensitivity_level: DataSensitivityLevel;
  data_volume_range: string;
  storage_type: string;
  hosting_jurisdiction: string;
  is_encrypted_at_rest: boolean;
  is_encrypted_in_transit: boolean;
  is_pseudonymized: boolean;
  retention_period_months?: number | null;

  owner_id: number;
  steward_id?: number | null;
  cloud_asset_id?: number | null;
  business_process_id?: number | null;
  ai_system_id?: number | null;
  vendor_id?: number | null;

  classification_scheme_id?: number | null;
  classification_level_id?: number | null;
  classification_status: DataClassificationApprovalStatus;
  classified_by_id?: number | null;
  classification_approved_by_id?: number | null;
  classification_approved_at?: string | null;
  last_reviewed_at?: string | null;

  owner_transfer_status: string;
  pending_owner_id?: number | null;
  owner_transfer_requested_by_id?: number | null;
  owner_transfer_justification?: string | null;

  deprecation_notes?: string | null;
  disposal_method?: DataDisposalMethod | null;
  retirement_requested_by_id?: number | null;
  retired_by_id?: number | null;
  retired_at?: string | null;
  retirement_notes?: string | null;
  retirement_evidence_id?: number | null;

  created_at: string;
  updated_at: string;
}

export interface GovernedDataAssetCreate {
  asset_code: string;
  name: string;
  description?: string;
  asset_type?: DataAssetType;
  initial_lifecycle_state?: 'DISCOVERED' | 'REGISTERED';
  data_sensitivity_level?: DataSensitivityLevel;
  data_volume_range?: string;
  storage_type?: string;
  hosting_jurisdiction?: string;
  is_encrypted_at_rest?: boolean;
  is_encrypted_in_transit?: boolean;
  is_pseudonymized?: boolean;
  retention_period_months?: number;
  owner_id?: number;
  steward_id?: number;
  cloud_asset_id?: number;
  business_process_id?: number;
  ai_system_id?: number;
  vendor_id?: number;
}

export interface GovernedDataAssetUpdate {
  name?: string;
  description?: string;
  asset_type?: DataAssetType;
  data_volume_range?: string;
  storage_type?: string;
  hosting_jurisdiction?: string;
  is_encrypted_at_rest?: boolean;
  is_encrypted_in_transit?: boolean;
  is_pseudonymized?: boolean;
  retention_period_months?: number;
}

export interface DataClassificationRequestCreate {
  scheme_id: number;
  level_id: number;
  justification: string;
  require_approval?: boolean;
}

export interface DataClassificationRejectRequest {
  rejection_reason: string;
}

export interface DataClassificationRecord {
  id: number;
  organization_id: number;
  data_asset_id: number;
  version: number;
  scheme_id: number;
  level_id: number;
  previous_level_id?: number | null;
  previous_sensitivity_level?: DataSensitivityLevel | null;
  new_sensitivity_level: DataSensitivityLevel;
  change_type: DataClassificationChangeType;
  status: DataClassificationRecordStatus;
  justification: string;
  requested_by_id: number;
  approved_by_id?: number | null;
  approved_at?: string | null;
  rejection_reason?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  created_at: string;
}

export interface DataOwnershipUpdateRequest {
  owner_id?: number;
  steward_id?: number;
  justification: string;
  require_approval?: boolean;
}

export interface DataAssetRegisterRequest {
  owner_id?: number;
  steward_id: number;
  notes?: string;
}

export interface DataAssetDeprecateRequest {
  deprecation_notes: string;
}

export interface DataAssetRetireRequest {
  disposal_method: DataDisposalMethod;
  retirement_notes: string;
  retirement_evidence_id?: number | null;
}

export interface DataAssetRestoreRequest {
  restoration_justification: string;
}

export interface DataLineageEdge {
  id: number;
  organization_id: number;
  edge_code: string;
  version: number;
  source_data_asset_id: number;
  target_data_asset_id: number;
  relationship_type: DataLineageRelationshipType;
  transformation_summary?: string | null;
  field_mapping_manifest?: Array<Record<string, unknown>> | null;
  is_encrypted_in_transit: boolean;
  is_masked_or_anonymized: boolean;
  processing_activity_id?: number | null;
  cloud_asset_id?: number | null;
  status: DataLineageStatus;
  provenance_hash: string;
  created_by_id: number;
  approved_by_id?: number | null;
  approved_at?: string | null;
  revoked_by_id?: number | null;
  revoked_at?: string | null;
  revocation_reason?: string | null;
  effective_from: string;
  effective_to?: string | null;
  created_at: string;
}

export interface DataLineageEdgeCreate {
  edge_code: string;
  source_data_asset_id: number;
  target_data_asset_id: number;
  relationship_type?: DataLineageRelationshipType;
  transformation_summary?: string;
  field_mapping_manifest?: Array<Record<string, unknown>>;
  is_encrypted_in_transit?: boolean;
  is_masked_or_anonymized?: boolean;
  processing_activity_id?: number;
  cloud_asset_id?: number;
  require_approval?: boolean;
}

export interface DataLineageEdgeRevokeRequest {
  revocation_reason: string;
}

export interface DataAssetCloudLink {
  id: number;
  organization_id: number;
  data_asset_id: number;
  cloud_asset_id: number;
  hosting_role: DataCloudHostingRole;
  notes?: string | null;
  linked_by_id?: number | null;
  created_at: string;
}

export interface DataAssetCloudLinkCreate {
  cloud_asset_id: number;
  hosting_role?: DataCloudHostingRole;
  notes?: string;
}

export interface DataAssetProcessingLink {
  id: number;
  organization_id: number;
  data_asset_id: number;
  processing_activity_id: number;
  usage_role: DataProcessingUsageRole;
  notes?: string | null;
  linked_by_id?: number | null;
  created_at: string;
}

export interface DataAssetProcessingLinkCreate {
  processing_activity_id: number;
  usage_role?: DataProcessingUsageRole;
  notes?: string;
}

export interface DataAssetControlLink {
  id: number;
  organization_id: number;
  data_asset_id: number;
  organization_control_id: number;
  control_objective: DataControlObjective;
  is_mandatory: boolean;
  coverage_notes?: string | null;
  linked_by_id?: number | null;
  created_at: string;
}

export interface DataAssetControlLinkCreate {
  organization_control_id: number;
  control_objective?: DataControlObjective;
  is_mandatory?: boolean;
  coverage_notes?: string;
}

export interface DataAssetEvidenceLink {
  id: number;
  organization_id: number;
  data_asset_id: number;
  evidence_item_id: number;
  evidence_purpose: DataEvidencePurpose;
  notes?: string | null;
  linked_by_id?: number | null;
  created_at: string;
}

export interface DataAssetEvidenceLinkCreate {
  evidence_item_id: number;
  evidence_purpose?: DataEvidencePurpose;
  notes?: string;
}

export interface CloudPostureAlignmentInfo {
  cloud_posture_aligned: boolean;
  linked_cloud_asset_ids: number[];
  mismatch_flags: string[];
}

export interface RegulatoryObligationRef {
  obligation_id: number;
  obligation_code: string;
  title: string;
  mandate_id: number;
  organization_control_id?: number | null;
  compliance_status: string;
}

export interface GovernedDataAssetDossier {
  asset: GovernedDataAsset;
  owner_active: boolean;
  steward_active?: boolean | null;
  cloud_alignment: CloudPostureAlignmentInfo;
  classification_history: DataClassificationRecord[];
  upstream_lineage: DataLineageEdge[];
  downstream_lineage: DataLineageEdge[];
  cloud_links: DataAssetCloudLink[];
  processing_links: DataAssetProcessingLink[];
  control_links: DataAssetControlLink[];
  evidence_links: DataAssetEvidenceLink[];
  regulatory_obligations: RegulatoryObligationRef[];
}

export interface DataGovernanceSummary {
  total_assets: number;
  active_assets: number;
  discovered_unregistered_assets: number;
  deprecated_assets: number;
  retired_assets: number;
  classified_assets_count: number;
  pending_classification_approvals: number;
  unclassified_assets_count: number;
  restricted_or_phi_assets_count: number;
  owner_coverage_pct: number;
  steward_coverage_pct: number;
  inactive_owner_count: number;
  active_lineage_edges_count: number;
  pending_lineage_approvals_count: number;
  cloud_linked_assets_count: number;
  cloud_posture_mismatch_count: number;
  processing_linked_assets_count: number;
  control_linked_assets_count: number;
  evidence_linked_assets_count: number;
  governance_health_score: number;
  sensitivity_distribution: Record<string, number>;
  lifecycle_distribution: Record<string, number>;
}
