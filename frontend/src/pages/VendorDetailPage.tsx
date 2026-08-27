import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileCheck2,
  FolderCheck,
  Plus,
  RefreshCw,
  Server,
  ShieldAlert,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { tprmService } from '../lib/tprmService';
import { harmonizationService } from '../lib/harmonizationService';
import { api } from '../lib/api';
import type {
  BusinessCriticality,
  DataClassification,
  EvidenceItem,
  HostingModel,
  NetworkConnectivity,
  PiiFinancialAccess,
  RationalizedCommonControl,
  Vendor,
  VendorAssessment,
  VendorAssessmentCreate,
  VendorAssessmentItemCreate,
  VendorAssessmentType,
  VendorDocumentType,
  VendorEngagementCreate,
  VendorEvidenceLinkCreate,
  VendorRiskPostureResponse,
  VendorStatus,
  VendorTier,
} from '../types';

export const VendorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const vendorId = Number(id);
  const navigate = useNavigate();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');
  const canAssess = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');
  const canApprove = hasRole('ADMIN', 'MANAGER');

  const [loading, setLoading] = useState(true);
  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [posture, setPosture] = useState<VendorRiskPostureResponse | null>(null);
  const [assessments, setAssessments] = useState<VendorAssessment[]>([]);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([]);
  const [commonControls, setCommonControls] = useState<RationalizedCommonControl[]>([]);

  const [activeTab, setActiveTab] = useState<'posture' | 'engagements' | 'assessments' | 'evidence'>('posture');

  // Tier Override Modal
  const [showTierModal, setShowTierModal] = useState(false);
  const [overrideTier, setOverrideTier] = useState<VendorTier>('TIER_1_CRITICAL');
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideLoading, setOverrideLoading] = useState(false);
  const [overrideError, setOverrideError] = useState<string | null>(null);

  // Status Change Modal
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [newStatus, setNewStatus] = useState<VendorStatus>('ACTIVE');
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Create Engagement Modal
  const [showEngagementModal, setShowEngagementModal] = useState(false);
  const [engagementForm, setEngagementForm] = useState<VendorEngagementCreate>({
    engagement_code: '',
    engagement_name: '',
    description: '',
    criticality: 'MEDIUM',
    data_classification: 'INTERNAL',
    hosting_model: 'MULTI_TENANT_SAAS',
    network_connectivity: 'ISOLATED_SAAS',
    pii_access: 'NO_PII_ACCESS',
  });
  const [engagementLoading, setEngagementLoading] = useState(false);
  const [engagementError, setEngagementError] = useState<string | null>(null);

  // Create Assessment Modal
  const [showAssessmentModal, setShowAssessmentModal] = useState(false);
  const [assessmentForm, setAssessmentForm] = useState<VendorAssessmentCreate>({
    assessment_code: '',
    title: '',
    assessment_type: 'INITIAL',
    valid_until: undefined,
  });
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [assessmentError, setAssessmentError] = useState<string | null>(null);

  // Link Evidence Modal
  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [evidenceForm, setEvidenceForm] = useState<VendorEvidenceLinkCreate>({
    evidence_id: 0,
    document_type: 'SOC2_TYPE_II',
    effective_date: undefined,
    expiration_date: undefined,
  });
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  const fetchVendorData = async () => {
    if (!vendorId) return;
    setLoading(true);
    try {
      const [vendorData, postureData, assessmentsData, evidenceData, ccData] =
        await Promise.all([
          tprmService.getVendor(vendorId),
          tprmService.getVendorRiskPosture(vendorId).catch(() => null),
          tprmService.listVendorAssessments(vendorId).catch(() => []),
          api.get<EvidenceItem[]>('/evidence').then((r) => r.data).catch(() => []),
          harmonizationService.listCommonControls().catch(() => []),
        ]);

      setVendor(vendorData);
      setPosture(postureData);
      setAssessments(assessmentsData);
      setEvidenceItems(evidenceData);
      setCommonControls(ccData);
    } catch (err) {
      console.error('Failed to fetch vendor workspace', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVendorData();
  }, [vendorId]);

  // Handle Tier Override
  const handleTierOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vendor) return;
    if (overrideReason.trim().length < 10) {
      setOverrideError('Justification reason must be at least 10 characters.');
      return;
    }

    setOverrideLoading(true);
    setOverrideError(null);
    try {
      const updated = await tprmService.overrideTier(vendor.id, {
        override_tier: overrideTier,
        reason: overrideReason.trim(),
      });
      setVendor(updated);
      setShowTierModal(false);
      setOverrideReason('');
      await fetchVendorData();
    } catch (err: any) {
      setOverrideError(err.response?.data?.detail || 'Failed to override tier.');
    } finally {
      setOverrideLoading(false);
    }
  };

  // Handle Status Update
  const handleStatusChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vendor) return;
    setStatusLoading(true);
    setStatusError(null);
    try {
      const updated = await tprmService.updateVendor(vendor.id, {
        vendor_status: newStatus,
      });
      setVendor(updated);
      setShowStatusModal(false);
      await fetchVendorData();
    } catch (err: any) {
      setStatusError(err.response?.data?.detail || 'Invalid status transition.');
    } finally {
      setStatusLoading(false);
    }
  };

  // Handle Create Engagement
  const handleCreateEngagement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vendor) return;
    if (!engagementForm.engagement_code.trim() || !engagementForm.engagement_name.trim()) {
      setEngagementError('Engagement code and name are required.');
      return;
    }

    setEngagementLoading(true);
    setEngagementError(null);
    try {
      await tprmService.createEngagement(vendor.id, {
        ...engagementForm,
        engagement_code: engagementForm.engagement_code.trim().toUpperCase(),
        engagement_name: engagementForm.engagement_name.trim(),
      });
      setShowEngagementModal(false);
      setEngagementForm({
        engagement_code: '',
        engagement_name: '',
        description: '',
        criticality: 'MEDIUM',
        data_classification: 'INTERNAL',
        hosting_model: 'MULTI_TENANT_SAAS',
        network_connectivity: 'ISOLATED_SAAS',
        pii_access: 'NO_PII_ACCESS',
      });
      await fetchVendorData();
    } catch (err: any) {
      setEngagementError(err.response?.data?.detail || 'Failed to create engagement.');
    } finally {
      setEngagementLoading(false);
    }
  };

  // Handle Create Assessment
  const handleCreateAssessment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vendor) return;
    if (!assessmentForm.assessment_code.trim() || !assessmentForm.title.trim()) {
      setAssessmentError('Assessment code and title are required.');
      return;
    }

    setAssessmentLoading(true);
    setAssessmentError(null);
    try {
      const initialItems: VendorAssessmentItemCreate[] = commonControls.slice(0, 10).map((cc) => ({
        rationalized_common_control_id: cc.id,
        question_key: `Q-${cc.common_control_code}`,
        question_text: `Does the vendor maintain verified controls for ${cc.title}? (${cc.description})`,
        weight: 1.0,
      }));

      if (initialItems.length === 0) {
        initialItems.push(
          { question_key: 'Q-IAM-01', question_text: 'Enforces Multi-Factor Authentication (MFA) on all administrative and corporate access', weight: 2.0 },
          { question_key: 'Q-ENC-01', question_text: 'Encrypts customer data in transit (TLS 1.3) and at rest (AES-256)', weight: 2.0 },
          { question_key: 'Q-LOG-01', question_text: 'Maintains centralized audit logging and continuous security monitoring', weight: 1.5 },
          { question_key: 'Q-BCP-01', question_text: 'Demonstrates tested Business Continuity and Disaster Recovery (BCDR) procedures', weight: 1.0 },
          { question_key: 'Q-VUL-01', question_text: 'Performs annual third-party penetration testing and prompt vulnerability remediation', weight: 1.5 }
        );
      }

      const created = await tprmService.createVendorAssessment(vendor.id, {
        assessment_code: assessmentForm.assessment_code.trim().toUpperCase(),
        title: assessmentForm.title.trim(),
        assessment_type: assessmentForm.assessment_type,
        valid_until: assessmentForm.valid_until || undefined,
        items: initialItems,
      });

      setShowAssessmentModal(false);
      setAssessmentForm({
        assessment_code: '',
        title: '',
        assessment_type: 'INITIAL',
        valid_until: undefined,
      });
      await fetchVendorData();
      navigate(`/vendors/assessments/${created.id}`);
    } catch (err: any) {
      setAssessmentError(err.response?.data?.detail || 'Failed to create assessment.');
    } finally {
      setAssessmentLoading(false);
    }
  };

  // Handle Link Evidence
  const handleLinkEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vendor || !evidenceForm.evidence_id) {
      setEvidenceError('Please select a valid Evidence item.');
      return;
    }

    setEvidenceLoading(true);
    setEvidenceError(null);
    try {
      await tprmService.linkVendorEvidence(vendor.id, {
        evidence_id: Number(evidenceForm.evidence_id),
        document_type: evidenceForm.document_type,
        effective_date: evidenceForm.effective_date || undefined,
        expiration_date: evidenceForm.expiration_date || undefined,
      });
      setShowEvidenceModal(false);
      setEvidenceForm({
        evidence_id: 0,
        document_type: 'SOC2_TYPE_II',
        effective_date: undefined,
        expiration_date: undefined,
      });
      await fetchVendorData();
    } catch (err: any) {
      setEvidenceError(err.response?.data?.detail || 'Failed to link evidence.');
    } finally {
      setEvidenceLoading(false);
    }
  };

  // Handle Unlink Evidence
  const handleUnlinkEvidence = async (linkId: number) => {
    if (!vendor) return;
    if (!window.confirm('Unlink this evidence document from the vendor?')) return;
    try {
      await tprmService.unlinkVendorEvidence(vendor.id, linkId);
      await fetchVendorData();
    } catch (err) {
      console.error('Failed to unlink evidence', err);
    }
  };

  if (loading && !vendor) {
    return (
      <div className="py-20 text-center text-slate-500">
        <RefreshCw size={24} className="animate-spin mx-auto mb-3 text-indigo-400" />
        <span>Loading vendor governance workspace...</span>
      </div>
    );
  }

  if (!vendor) {
    return (
      <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-lg">
        <AlertCircle size={32} className="mx-auto mb-2 text-red-400" />
        <h2 className="text-lg font-bold text-slate-100">Vendor Profile Not Found</h2>
        <p className="text-xs text-slate-400 mt-1">
          The requested vendor ID does not exist or belongs to another organization tenant.
        </p>
        <button
          onClick={() => navigate('/vendors')}
          className="mt-4 px-4 py-2 text-xs font-semibold rounded-md bg-indigo-600 text-white"
        >
          Return to Vendor Portfolio
        </button>
      </div>
    );
  }

  const isOverridden = !!vendor.override_tier;

  return (
    <div className="space-y-6">
      {/* Back link & Title Bar */}
      <div>
        <Link
          to="/vendors"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-indigo-400 transition-colors mb-3"
        >
          <ArrowLeft size={14} />
          <span>Back to Vendor Portfolio</span>
        </Link>

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 bg-slate-900/90 p-5 rounded-xl border border-slate-800 shadow-xs">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                {vendor.vendor_code}
              </span>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
                {vendor.legal_name}
              </h1>
              {vendor.trade_name && (
                <span className="text-xs text-slate-400 italic">
                  (DBA: {vendor.trade_name})
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 pt-1">
              <span>
                Owner:{' '}
                <strong className="text-slate-200">
                  {vendor.business_owner?.full_name || 'Unassigned'}
                </strong>
              </span>
              <span>&bull;</span>
              <span>
                Status:{' '}
                <strong className="text-slate-200">{vendor.vendor_status}</strong>
              </span>
              {canManage && (
                <button
                  onClick={() => {
                    setNewStatus(vendor.vendor_status);
                    setShowStatusModal(true);
                  }}
                  className="text-indigo-400 hover:text-indigo-300 underline font-medium text-[11px]"
                >
                  Change Status
                </button>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Effective Tier Badge & Override */}
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <div className="text-right">
                <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                  Effective Tier
                </div>
                <div className="text-xs font-mono font-bold text-indigo-400">
                  {vendor.effective_tier.replace('_', ' ')}
                  {isOverridden && <span className="text-amber-400 ml-1 font-bold">*</span>}
                </div>
              </div>

              {canApprove && (
                <button
                  onClick={() => {
                    setOverrideTier(vendor.effective_tier);
                    setShowTierModal(true);
                  }}
                  title="Override Tier (Four-Eyes Approval Required)"
                  className="px-2 py-1 text-[10px] font-semibold rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
                >
                  Override
                </button>
              )}
            </div>

            {/* Inherent Risk Score */}
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-center min-w-[100px]">
              <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                Inherent Risk
              </div>
              <div className="text-base font-mono font-bold text-slate-200">
                {vendor.calculated_inherent_risk.toFixed(1)}
              </div>
            </div>

            {/* Residual Risk Score & Band */}
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-center min-w-[120px]">
              <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                Residual Risk
              </div>
              <div className="flex items-center justify-center gap-1.5">
                <span className="text-base font-mono font-bold text-amber-400">
                  {vendor.residual_risk_score.toFixed(1)}
                </span>
                <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800">
                  {vendor.risk_band}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-px">
        <button
          onClick={() => setActiveTab('posture')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'posture'
              ? 'border-indigo-500 text-indigo-400 bg-slate-900/50'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity size={14} />
          <span>Risk Posture &amp; Telemetry</span>
        </button>

        <button
          onClick={() => setActiveTab('engagements')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'engagements'
              ? 'border-indigo-500 text-indigo-400 bg-slate-900/50'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Server size={14} />
          <span>Engagements &amp; Services ({vendor.engagements?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('assessments')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'assessments'
              ? 'border-indigo-500 text-indigo-400 bg-slate-900/50'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileCheck2 size={14} />
          <span>Questionnaires &amp; Assessments ({assessments.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('evidence')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'evidence'
              ? 'border-indigo-500 text-indigo-400 bg-slate-900/50'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FolderCheck size={14} />
          <span>Evidence &amp; Certifications ({vendor.evidence_links?.length || 0})</span>
        </button>
      </div>

      {/* Tab 1: Risk Posture & Telemetry */}
      {activeTab === 'posture' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Inherent Risk Decomposition Card */}
            <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={18} className="text-red-400" />
                  <h3 className="text-sm font-bold text-slate-100">
                    Inherent Risk Engine Breakdown
                  </h3>
                </div>
                <span className="font-mono text-base font-bold text-slate-100">
                  {vendor.calculated_inherent_risk.toFixed(1)} / 100
                </span>
              </div>

              <p className="text-xs text-slate-400">
                Formula: Maximum calculated engagement risk across all active engagements:
                <br />
                <code className="font-mono text-[11px] text-indigo-300">
                  EngagementRisk = 0.30&times;Criticality + 0.30&times;Data + 0.20&times;Network + 0.10&times;PII + 0.10&times;Hosting
                </code>
              </p>

              <div className="space-y-2 pt-2 border-t border-slate-800/80 text-xs">
                <div className="flex justify-between text-slate-300">
                  <span>Calculated Tier:</span>
                  <span className="font-mono font-semibold text-slate-100">
                    {vendor.calculated_tier}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Effective Tier (Gov):</span>
                  <span className="font-mono font-semibold text-indigo-400">
                    {vendor.effective_tier}
                  </span>
                </div>
                {vendor.override_tier && (
                  <div className="p-2.5 rounded-md bg-amber-950/40 border border-amber-800/50 text-[11px] text-amber-300">
                    <strong>Tier Override Active:</strong> {vendor.tier_override_reason}
                    <br />
                    <span className="text-slate-400 text-[10px]">
                      Overridden at: {vendor.tier_overridden_at ? new Date(vendor.tier_overridden_at).toLocaleString() : 'N/A'}
                    </span>
                  </div>
                )}
                <div className="flex justify-between text-slate-300">
                  <span>Active Engagements Scoped:</span>
                  <span className="font-mono font-semibold text-slate-100">
                    {vendor.engagements?.filter((e) => e.status === 'ACTIVE').length || 0}
                  </span>
                </div>
              </div>
            </div>

            {/* Residual Risk Decomposition Card */}
            <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={18} className="text-emerald-400" />
                  <h3 className="text-sm font-bold text-slate-100">
                    Residual Risk Telemetry Engine
                  </h3>
                </div>
                <span className="font-mono text-base font-bold text-amber-400">
                  {vendor.residual_risk_score.toFixed(1)} / 100
                </span>
              </div>

              <p className="text-xs text-slate-400">
                Formula: Residual risk with 20% floor, questionnaire attenuation, and penalty additions:
                <br />
                <code className="font-mono text-[11px] text-indigo-300">
                  Residual = clamp(max(Floor, Inherent &times; (1.0 - 0.70 &times; Score)) + Penalties, 0, 100)
                </code>
              </p>

              <div className="space-y-2 pt-2 border-t border-slate-800/80 text-xs">
                <div className="flex justify-between text-slate-300">
                  <span>20% Defensible Risk Floor:</span>
                  <span className="font-mono text-slate-300">
                    {(0.20 * vendor.calculated_inherent_risk).toFixed(1)}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Latest Approved Assessment Score:</span>
                  <span className="font-mono text-slate-300">
                    {posture?.residual?.latest_assessment_score !== undefined && posture?.residual?.latest_assessment_score !== null
                      ? `${posture.residual.latest_assessment_score.toFixed(1)}%`
                      : 'Unassessed (0.0% Attenuation)'}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Finding &amp; Exception Penalties:</span>
                  <span className="font-mono text-slate-300">+0.0</span>
                </div>
                <div className="flex justify-between text-slate-300 font-semibold border-t border-slate-800 pt-1.5">
                  <span>Final Risk Band:</span>
                  <span className="text-amber-400 font-mono">{vendor.risk_band}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Engagements & Services */}
      {activeTab === 'engagements' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-100">
              Contracted Engagements &amp; Services
            </h3>
            {canManage && (
              <button
                onClick={() => setShowEngagementModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                <Plus size={13} />
                <span>Add Engagement</span>
              </button>
            )}
          </div>

          <div className="rounded-lg bg-slate-900/90 border border-slate-800 overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/70 text-slate-400 font-semibold uppercase text-[11px]">
                  <th className="py-3 px-4">Code &amp; Name</th>
                  <th className="py-3 px-4">Criticality</th>
                  <th className="py-3 px-4">Data Classification</th>
                  <th className="py-3 px-4">Network &amp; Hosting</th>
                  <th className="py-3 px-4">PII Access</th>
                  <th className="py-3 px-4">Calculated Risk</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {!vendor.engagements || vendor.engagements.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      No engagements recorded for this vendor. Inherent risk defaults to 0.0.
                    </td>
                  </tr>
                ) : (
                  vendor.engagements.map((eng) => (
                    <tr key={eng.id} className="hover:bg-slate-800/30">
                      <td className="py-3.5 px-4">
                        <div className="font-mono font-bold text-indigo-400">
                          {eng.engagement_code}
                        </div>
                        <div className="text-slate-200 font-medium mt-0.5">
                          {eng.engagement_name}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-300">
                        {eng.criticality}
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">
                        {eng.data_classification}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                        <div>{eng.network_connectivity}</div>
                        <div className="text-slate-500">{eng.hosting_model}</div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">
                        {eng.pii_access}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-100">
                        {eng.calculated_risk_score.toFixed(1)}
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            eng.status === 'ACTIVE'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {eng.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Questionnaires & Assessments */}
      {activeTab === 'assessments' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-100">
              Vendor Questionnaires &amp; Security Assessments
            </h3>
            {canAssess && (
              <button
                onClick={() => setShowAssessmentModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                <Plus size={13} />
                <span>Launch Assessment</span>
              </button>
            )}
          </div>

          <div className="rounded-lg bg-slate-900/90 border border-slate-800 overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/70 text-slate-400 font-semibold uppercase text-[11px]">
                  <th className="py-3 px-4">Code &amp; Title</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Lifecycle Status</th>
                  <th className="py-3 px-4">Calculated Score</th>
                  <th className="py-3 px-4">Assessor / Reviewer</th>
                  <th className="py-3 px-4">Valid Until</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {assessments.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      No assessments launched yet. Launch an assessment to evaluate questionnaire responses.
                    </td>
                  </tr>
                ) : (
                  assessments.map((ass) => (
                    <tr
                      key={ass.id}
                      onClick={() => navigate(`/vendors/assessments/${ass.id}`)}
                      className="hover:bg-slate-800/40 cursor-pointer"
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-mono font-bold text-indigo-400">
                          {ass.assessment_code}
                        </div>
                        <div className="text-slate-200 font-semibold mt-0.5">
                          {ass.title}
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-slate-300">
                        {ass.assessment_type.replace('_', ' ')}
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            ass.status === 'APPROVED'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : ass.status === 'IN_REVIEW'
                              ? 'bg-purple-950 text-purple-400 border border-purple-800'
                              : ass.status === 'SUBMITTED'
                              ? 'bg-blue-950 text-blue-400 border border-blue-800'
                              : ass.status === 'REJECTED'
                              ? 'bg-red-950 text-red-400 border border-red-800'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {ass.status}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 font-mono font-bold text-slate-100">
                        {ass.calculated_score.toFixed(1)}%
                      </td>

                      <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                        <div>Assessor: {ass.assessor?.full_name || 'N/A'}</div>
                        {ass.reviewer && <div>Reviewer: {ass.reviewer.full_name}</div>}
                      </td>

                      <td className="py-3.5 px-4 text-slate-400">
                        {ass.valid_until ? new Date(ass.valid_until).toLocaleDateString() : 'N/A'}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <span className="text-indigo-400 hover:text-indigo-300 font-semibold text-xs inline-flex items-center gap-1">
                          <span>Open Assessment</span>
                          <ExternalLink size={13} />
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 4: Evidence & Certifications */}
      {activeTab === 'evidence' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-100">
              Linked Certifications &amp; Assurance Artifacts
            </h3>
            {canManage && (
              <button
                onClick={() => setShowEvidenceModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                <Plus size={13} />
                <span>Link Evidence Document</span>
              </button>
            )}
          </div>

          <div className="rounded-lg bg-slate-900/90 border border-slate-800 overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/70 text-slate-400 font-semibold uppercase text-[11px]">
                  <th className="py-3 px-4">Document Type</th>
                  <th className="py-3 px-4">Evidence Title / File</th>
                  <th className="py-3 px-4">Verification Status</th>
                  <th className="py-3 px-4">Effective Date</th>
                  <th className="py-3 px-4">Expiration Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {!vendor.evidence_links || vendor.evidence_links.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      No external audit certifications or evidence items linked to this vendor.
                    </td>
                  </tr>
                ) : (
                  vendor.evidence_links.map((link) => (
                    <tr key={link.id} className="hover:bg-slate-800/30">
                      <td className="py-3.5 px-4 font-semibold text-slate-200">
                        {link.document_type.replace('_', ' ')}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-slate-200">
                          {link.evidence?.title || `Evidence Item #${link.evidence_id}`}
                        </div>
                        {link.evidence?.original_filename && (
                          <div className="text-[11px] text-slate-400 font-mono">
                            {link.evidence.original_filename}
                          </div>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        {link.is_verified ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                            <CheckCircle2 size={13} />
                            <span>Verified</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-amber-400 font-semibold">
                            <Clock size={13} />
                            <span>Pending Review</span>
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">
                        {link.effective_date ? new Date(link.effective_date).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">
                        {link.expiration_date ? new Date(link.expiration_date).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        {canManage && (
                          <button
                            onClick={() => handleUnlinkEvidence(link.id)}
                            title="Unlink Evidence"
                            className="text-red-400 hover:text-red-300 p-1 rounded hover:bg-slate-800 transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tier Override Modal */}
      {showTierModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 shadow-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-amber-400" />
                <h3 className="text-base font-bold text-slate-100">
                  Authoritative Tier Override
                </h3>
              </div>
              <button
                onClick={() => setShowTierModal(false)}
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleTierOverride} className="p-6 space-y-4">
              {overrideError && (
                <div className="p-3 rounded-md bg-red-950/80 border border-red-800 text-xs text-red-300">
                  {overrideError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Override Tier Selection
                </label>
                <select
                  value={overrideTier}
                  onChange={(e) => setOverrideTier(e.target.value as VendorTier)}
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 focus:outline-hidden focus:border-indigo-500"
                >
                  <option value="TIER_1_CRITICAL">Tier 1 (Critical)</option>
                  <option value="TIER_2_SIGNIFICANT">Tier 2 (Significant)</option>
                  <option value="TIER_3_MODERATE">Tier 3 (Moderate)</option>
                  <option value="TIER_4_LOW">Tier 4 (Low)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Mandatory Governance Justification (min 10 characters) <span className="text-red-400">*</span>
                </label>
                <textarea
                  required
                  rows={4}
                  placeholder="State the business rationale, risk committee decision, or compensating factors justifying this tier override..."
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowTierModal(false)}
                  className="px-4 py-2 text-xs font-medium rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={overrideLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-md bg-amber-600 hover:bg-amber-500 text-white disabled:opacity-50"
                >
                  {overrideLoading ? 'Applying...' : 'Apply Tier Override'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Status Change Modal */}
      {showStatusModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 shadow-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-100">
                Transition Vendor Status
              </h3>
              <button
                onClick={() => setShowStatusModal(false)}
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleStatusChange} className="p-6 space-y-4">
              {statusError && (
                <div className="p-3 rounded-md bg-red-950/80 border border-red-800 text-xs text-red-300">
                  {statusError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Lifecycle Status
                </label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value as VendorStatus)}
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 focus:outline-hidden focus:border-indigo-500"
                >
                  <option value="PROSPECT">PROSPECT</option>
                  <option value="ONBOARDING">ONBOARDING</option>
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="UNDER_REVIEW">UNDER_REVIEW</option>
                  <option value="SUSPENDED">SUSPENDED</option>
                  <option value="OFFBOARDED">OFFBOARDED</option>
                </select>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowStatusModal(false)}
                  className="px-4 py-2 text-xs font-medium rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={statusLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-md bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                >
                  {statusLoading ? 'Updating...' : 'Update Status'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Engagement Modal */}
      {showEngagementModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-xl bg-slate-900 border border-slate-800 shadow-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server size={18} className="text-indigo-400" />
                <h3 className="text-base font-bold text-slate-100">
                  Register New Engagement / Service
                </h3>
              </div>
              <button
                onClick={() => setShowEngagementModal(false)}
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateEngagement} className="p-6 space-y-4">
              {engagementError && (
                <div className="p-3 rounded-md bg-red-950/80 border border-red-800 text-xs text-red-300">
                  {engagementError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Engagement Code <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. ENG-AWS-PROD"
                    value={engagementForm.engagement_code}
                    onChange={(e) =>
                      setEngagementForm({
                        ...engagementForm,
                        engagement_code: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 text-xs font-mono rounded-md bg-slate-950 border border-slate-800 text-slate-100 focus:outline-hidden focus:border-indigo-500 uppercase"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Engagement Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Production Cloud Hosting"
                    value={engagementForm.engagement_name}
                    onChange={(e) =>
                      setEngagementForm({
                        ...engagementForm,
                        engagement_name: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 focus:outline-hidden focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Business Criticality (30%)
                  </label>
                  <select
                    value={engagementForm.criticality}
                    onChange={(e) =>
                      setEngagementForm({
                        ...engagementForm,
                        criticality: e.target.value as BusinessCriticality,
                      })
                    }
                    className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                  >
                    <option value="CRITICAL">CRITICAL (100 pts)</option>
                    <option value="HIGH">HIGH (75 pts)</option>
                    <option value="MEDIUM">MEDIUM (50 pts)</option>
                    <option value="LOW">LOW (25 pts)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Data Classification (30%)
                  </label>
                  <select
                    value={engagementForm.data_classification}
                    onChange={(e) =>
                      setEngagementForm({
                        ...engagementForm,
                        data_classification: e.target.value as DataClassification,
                      })
                    }
                    className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                  >
                    <option value="RESTRICTED">RESTRICTED (100 pts)</option>
                    <option value="CONFIDENTIAL">CONFIDENTIAL (75 pts)</option>
                    <option value="INTERNAL">INTERNAL (40 pts)</option>
                    <option value="PUBLIC">PUBLIC (10 pts)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Network Connectivity (20%)
                  </label>
                  <select
                    value={engagementForm.network_connectivity}
                    onChange={(e) =>
                      setEngagementForm({
                        ...engagementForm,
                        network_connectivity: e.target.value as NetworkConnectivity,
                      })
                    }
                    className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                  >
                    <option value="DIRECT_API_VPN_DB">DIRECT API / VPN / DB (100 pts)</option>
                    <option value="CREDENTIALED_PORTAL">CREDENTIALED PORTAL (60 pts)</option>
                    <option value="ISOLATED_SAAS">ISOLATED SAAS (30 pts)</option>
                    <option value="AIR_GAPPED_OFFLINE">AIR GAPPED / OFFLINE (0 pts)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    PII / Financial Access (10%)
                  </label>
                  <select
                    value={engagementForm.pii_access}
                    onChange={(e) =>
                      setEngagementForm({
                        ...engagementForm,
                        pii_access: e.target.value as PiiFinancialAccess,
                      })
                    }
                    className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                  >
                    <option value="DIRECT_PCI_PII_PHI">DIRECT PCI / PII / PHI (100 pts)</option>
                    <option value="AGGREGATED_ANONYMIZED">AGGREGATED / ANONYMIZED (50 pts)</option>
                    <option value="NO_PII_ACCESS">NO PII ACCESS (0 pts)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Hosting Model (10%)
                </label>
                <select
                  value={engagementForm.hosting_model}
                  onChange={(e) =>
                    setEngagementForm({
                      ...engagementForm,
                      hosting_model: e.target.value as HostingModel,
                    })
                  }
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                >
                  <option value="VENDOR_PUBLIC_CLOUD">VENDOR PUBLIC CLOUD (100 pts)</option>
                  <option value="MULTI_TENANT_SAAS">MULTI-TENANT SAAS (80 pts)</option>
                  <option value="DEDICATED_HOSTED">DEDICATED HOSTED (40 pts)</option>
                  <option value="ON_PREM_CUSTOMER_DATACENTER">ON-PREM / CUSTOMER DC (10 pts)</option>
                </select>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowEngagementModal(false)}
                  className="px-4 py-2 text-xs font-medium rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={engagementLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-md bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                >
                  {engagementLoading ? 'Saving...' : 'Register Engagement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Launch Assessment Modal */}
      {showAssessmentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 shadow-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCheck2 size={18} className="text-indigo-400" />
                <h3 className="text-base font-bold text-slate-100">
                  Launch Vendor Assessment
                </h3>
              </div>
              <button
                onClick={() => setShowAssessmentModal(false)}
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateAssessment} className="p-6 space-y-4">
              {assessmentError && (
                <div className="p-3 rounded-md bg-red-950/80 border border-red-800 text-xs text-red-300">
                  {assessmentError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Assessment Code <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. VASS-2026-01"
                  value={assessmentForm.assessment_code}
                  onChange={(e) =>
                    setAssessmentForm({
                      ...assessmentForm,
                      assessment_code: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 text-xs font-mono rounded-md bg-slate-950 border border-slate-800 text-slate-100 focus:outline-hidden focus:border-indigo-500 uppercase"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Assessment Title <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 2026 Annual Security Due Diligence"
                  value={assessmentForm.title}
                  onChange={(e) =>
                    setAssessmentForm({
                      ...assessmentForm,
                      title: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Assessment Type
                </label>
                <select
                  value={assessmentForm.assessment_type}
                  onChange={(e) =>
                    setAssessmentForm({
                      ...assessmentForm,
                      assessment_type: e.target.value as VendorAssessmentType,
                    })
                  }
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                >
                  <option value="INITIAL">INITIAL</option>
                  <option value="ANNUAL_REASSESSMENT">ANNUAL REASSESSMENT</option>
                  <option value="INCIDENT_TRIGGERED">INCIDENT TRIGGERED</option>
                  <option value="ENGAGEMENT_SPECIFIC">ENGAGEMENT SPECIFIC</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Valid Until Date (Optional)
                </label>
                <input
                  type="date"
                  value={assessmentForm.valid_until || ''}
                  onChange={(e) =>
                    setAssessmentForm({
                      ...assessmentForm,
                      valid_until: e.target.value || undefined,
                    })
                  }
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAssessmentModal(false)}
                  className="px-4 py-2 text-xs font-medium rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={assessmentLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-md bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                >
                  {assessmentLoading ? 'Launching...' : 'Launch Assessment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Link Evidence Modal */}
      {showEvidenceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 shadow-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FolderCheck size={18} className="text-indigo-400" />
                <h3 className="text-base font-bold text-slate-100">
                  Link Phase 3 Evidence Document
                </h3>
              </div>
              <button
                onClick={() => setShowEvidenceModal(false)}
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleLinkEvidence} className="p-6 space-y-4">
              {evidenceError && (
                <div className="p-3 rounded-md bg-red-950/80 border border-red-800 text-xs text-red-300">
                  {evidenceError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Document Type Classification
                </label>
                <select
                  value={evidenceForm.document_type}
                  onChange={(e) =>
                    setEvidenceForm({
                      ...evidenceForm,
                      document_type: e.target.value as VendorDocumentType,
                    })
                  }
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                >
                  <option value="SOC2_TYPE_II">SOC 2 Type II Report</option>
                  <option value="ISO_27001_CERT">ISO 27001 Certificate</option>
                  <option value="PCI_AOC">PCI-DSS Attestation of Compliance (AOC)</option>
                  <option value="PEN_TEST_REPORT">Penetration Test Executive Summary</option>
                  <option value="PRIVACY_POLICY">Data Privacy &amp; DPA Document</option>
                  <option value="BUSINESS_CONTINUITY_PLAN">Business Continuity &amp; DR Plan</option>
                  <option value="SECURITY_QUESTIONNAIRE">SIG / CAIQ Questionnaire</option>
                  <option value="OTHER">Other Attestation</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Select Evidence Item (Phase 3 Catalog) <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={evidenceForm.evidence_id}
                  onChange={(e) =>
                    setEvidenceForm({
                      ...evidenceForm,
                      evidence_id: Number(e.target.value),
                    })
                  }
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                >
                  <option value={0}>-- Select Evidence Item --</option>
                  {evidenceItems.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      #{ev.id} - {ev.title} ({ev.original_filename}) [{ev.status}]
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Effective Date
                  </label>
                  <input
                    type="date"
                    value={evidenceForm.effective_date || ''}
                    onChange={(e) =>
                      setEvidenceForm({
                        ...evidenceForm,
                        effective_date: e.target.value || undefined,
                      })
                    }
                    className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Expiration Date
                  </label>
                  <input
                    type="date"
                    value={evidenceForm.expiration_date || ''}
                    onChange={(e) =>
                      setEvidenceForm({
                        ...evidenceForm,
                        expiration_date: e.target.value || undefined,
                      })
                    }
                    className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100"
                  />
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowEvidenceModal(false)}
                  className="px-4 py-2 text-xs font-medium rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={evidenceLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-md bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                >
                  {evidenceLoading ? 'Linking...' : 'Link Evidence'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
