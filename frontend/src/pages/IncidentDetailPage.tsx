import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertOctagon,
  ArrowLeft,
  Building2,
  Edit3,
  FileCheck2,
  History,
  Lock,
  Plus,
  RefreshCw,
  Scale,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  UserCheck,
  Zap,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { incidentService } from '../lib/incidentService';
import { api } from '../lib/api';
import type {
  IncidentCloseRequest,
  IncidentControlLinkCreate,
  IncidentControlRelationship,
  IncidentDetailRead,
  IncidentMaterialityUpdate,
  IncidentRegulatoryDisclosure,
  IncidentRegulatoryDisclosureCreate,
  IncidentRegulatoryExemptionRequest,
  IncidentRegulatoryNotificationRequest,
  IncidentStatus,
  IncidentTimelineEventCreate,
  IncidentUpdate,
  IncidentVendorLinkCreate,
  OrganizationControl,
  Regulator,
  RootCauseClassification,
  TimelineEventType,
  User,
  Vendor,
  VendorEngagement,
} from '../types';

export const IncidentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, hasRole } = useAuth();

  const incidentId = parseInt(id || '0', 10);
  const canManage = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');
  const canClose = hasRole('ADMIN', 'MANAGER');
  const canDisclose = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');

  const [loading, setLoading] = useState(true);
  const [incident, setIncident] = useState<IncidentDetailRead | null>(null);
  const [activeTab, setActiveTab] = useState<
    'overview' | 'timeline' | 'controls' | 'vendors' | 'disclosures' | 'closure'
  >('overview');

  // Tenant Reference Data
  const [users, setUsers] = useState<User[]>([]);
  const [controls, setControls] = useState<OrganizationControl[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [engagements, setEngagements] = useState<VendorEngagement[]>([]);

  // Modals & Action States
  const [showTransitionModal, setShowTransitionModal] = useState(false);
  const [targetStatus, setTargetStatus] = useState<IncidentStatus>('TRIAGED');
  const [transitionNotes, setTransitionNotes] = useState('');
  const [transitionLoading, setTransitionLoading] = useState(false);
  const [transitionError, setTransitionError] = useState<string | null>(null);

  // Edit Metadata Modal
  const [showEditModal, setShowEditModal] = useState(false);
  const [editForm, setEditForm] = useState<IncidentUpdate>({});
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Materiality Modal
  const [showMaterialityModal, setShowMaterialityModal] = useState(false);
  const [materialityForm, setMaterialityForm] = useState<IncidentMaterialityUpdate>({
    is_material: true,
    materiality_notes: '',
  });
  const [materialityLoading, setMaterialityLoading] = useState(false);
  const [materialityError, setMaterialityError] = useState<string | null>(null);

  // Four-Eyes Close Modal
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [closeForm, setCloseForm] = useState<IncidentCloseRequest>({
    closure_notes: '',
    lessons_learned: '',
    root_cause_classification: 'CONTROL_FAILURE',
    root_cause_narrative: '',
  });
  const [closeLoading, setCloseLoading] = useState(false);
  const [closeError, setCloseError] = useState<string | null>(null);

  // Timeline Event Modal
  const [showTimelineModal, setShowTimelineModal] = useState(false);
  const [timelineForm, setTimelineForm] = useState<IncidentTimelineEventCreate>({
    event_type: 'CONTAINMENT_ACTION',
    event_occurred_at: new Date().toISOString().slice(0, 16),
    description: '',
    source: 'MANUAL_ENTRY',
  });
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState<string | null>(null);

  // Link Control Modal
  const [showControlModal, setShowControlModal] = useState(false);
  const [controlForm, setControlForm] = useState<IncidentControlLinkCreate>({
    organization_control_id: 0,
    relationship_type: 'FAILED_CONTROL',
    notes: '',
  });
  const [controlLoading, setControlLoading] = useState(false);
  const [controlError, setControlError] = useState<string | null>(null);

  // Link Vendor Modal
  const [showVendorModal, setShowVendorModal] = useState(false);
  const [vendorForm, setVendorForm] = useState<IncidentVendorLinkCreate>({
    vendor_id: 0,
    vendor_engagement_id: undefined,
    is_vendor_originated: true,
    notes: '',
  });
  const [vendorLoading, setVendorLoading] = useState(false);
  const [vendorError, setVendorError] = useState<string | null>(null);

  // Initialize Disclosure Modal
  const [showDisclosureModal, setShowDisclosureModal] = useState(false);
  const [disclosureForm, setDisclosureForm] = useState<IncidentRegulatoryDisclosureCreate>({
    regulator: 'GDPR_DPA',
    trigger_type: 'INCIDENT_DETECTION',
    triggered_at: new Date().toISOString().slice(0, 16),
  });
  const [disclosureLoading, setDisclosureLoading] = useState(false);
  const [disclosureError, setDisclosureError] = useState<string | null>(null);

  // Record Notification Modal
  const [selectedDisclosureForNotify, setSelectedDisclosureForNotify] =
    useState<IncidentRegulatoryDisclosure | null>(null);
  const [notifyForm, setNotifyForm] = useState<IncidentRegulatoryNotificationRequest>({
    notification_reference_code: '',
    disclosure_notes: '',
  });
  const [notifyLoading, setNotifyLoading] = useState(false);
  const [notifyError, setNotifyError] = useState<string | null>(null);

  // Record Exemption Modal
  const [selectedDisclosureForExempt, setSelectedDisclosureForExempt] =
    useState<IncidentRegulatoryDisclosure | null>(null);
  const [exemptForm, setExemptForm] = useState<IncidentRegulatoryExemptionRequest>({
    exemption_reason: '',
  });
  const [exemptLoading, setExemptLoading] = useState(false);
  const [exemptError, setExemptError] = useState<string | null>(null);

  const fetchIncidentDetail = async () => {
    if (!incidentId) return;
    setLoading(true);
    try {
      const [detailData, usersData, controlsData, vendorsData] = await Promise.all([
        incidentService.getIncidentDetail(incidentId),
        api.get<User[]>('/users').then((r) => r.data).catch(() => []),
        api.get<OrganizationControl[]>('/controls').then((r) => r.data).catch(() => []),
        api.get<Vendor[]>('/vendors').then((r) => r.data).catch(() => []),
      ]);
      setIncident(detailData);
      setUsers(usersData);
      setControls(controlsData);
      setVendors(vendorsData);

      // Populate edit form defaults
      setEditForm({
        title: detailData.title,
        description: detailData.description,
        severity: detailData.severity,
        category: detailData.category,
        business_owner_id: detailData.business_owner_id,
        affected_record_count: detailData.affected_record_count,
        affected_systems_summary: detailData.affected_systems_summary,
        financial_impact_estimate: detailData.financial_impact_estimate,
        root_cause_classification: detailData.root_cause_classification,
        root_cause_narrative: detailData.root_cause_narrative,
        lessons_learned: detailData.lessons_learned,
      });

      // Default target status
      if (detailData.status === 'DECLARED') setTargetStatus('TRIAGED');
      else if (detailData.status === 'TRIAGED') setTargetStatus('CONTAINED');
      else if (detailData.status === 'CONTAINED') setTargetStatus('ERADICATED');
      else if (detailData.status === 'ERADICATED') setTargetStatus('RECOVERED');
      else if (detailData.status === 'RECOVERED') setTargetStatus('POST_MORTEM');
      else if (detailData.status === 'POST_MORTEM') setTargetStatus('POST_MORTEM');
    } catch (err) {
      console.error('Failed to load incident detail', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidentDetail();
  }, [incidentId]);

  // Load engagements when vendor selection changes in modal
  const handleVendorSelect = async (vendorId: number) => {
    setVendorForm({ ...vendorForm, vendor_id: vendorId, vendor_engagement_id: undefined });
    if (!vendorId) {
      setEngagements([]);
      return;
    }
    try {
      const res = await api.get<VendorEngagement[]>(`/vendors/${vendorId}/engagements`);
      setEngagements(res.data);
    } catch {
      setEngagements([]);
    }
  };

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    setTransitionLoading(true);
    setTransitionError(null);
    try {
      await incidentService.transitionLifecycle(incidentId, {
        target_status: targetStatus,
        notes: transitionNotes.trim() || undefined,
      });
      setShowTransitionModal(false);
      setTransitionNotes('');
      await fetchIncidentDetail();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setTransitionError(typeof detail === 'string' ? detail : 'Failed to transition lifecycle.');
    } finally {
      setTransitionLoading(false);
    }
  };

  const handleUpdateMetadata = async (e: React.FormEvent) => {
    e.preventDefault();
    setEditLoading(true);
    setEditError(null);
    try {
      await incidentService.updateIncident(incidentId, {
        ...editForm,
        affected_record_count: Number(editForm.affected_record_count) || 0,
        financial_impact_estimate: Number(editForm.financial_impact_estimate) || 0,
      });
      setShowEditModal(false);
      await fetchIncidentDetail();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setEditError(typeof detail === 'string' ? detail : 'Failed to update metadata.');
    } finally {
      setEditLoading(false);
    }
  };

  const handleSetMateriality = async (e: React.FormEvent) => {
    e.preventDefault();
    setMaterialityLoading(true);
    setMaterialityError(null);
    try {
      await incidentService.setMateriality(incidentId, materialityForm);
      setShowMaterialityModal(false);
      await fetchIncidentDetail();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setMaterialityError(
        typeof detail === 'string' ? detail : 'Failed to update materiality determination.'
      );
    } finally {
      setMaterialityLoading(false);
    }
  };

  const handleFourEyesClose = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!closeForm.closure_notes || closeForm.closure_notes.trim().length < 10) {
      setCloseError('Mandatory closure notes must be at least 10 characters.');
      return;
    }
    setCloseLoading(true);
    setCloseError(null);
    try {
      await incidentService.closeIncident(incidentId, {
        closure_notes: closeForm.closure_notes.trim(),
        lessons_learned: closeForm.lessons_learned?.trim() || undefined,
        root_cause_classification: closeForm.root_cause_classification,
        root_cause_narrative: closeForm.root_cause_narrative?.trim() || undefined,
      });
      setShowCloseModal(false);
      await fetchIncidentDetail();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setCloseError(typeof detail === 'string' ? detail : 'Failed to close incident.');
    } finally {
      setCloseLoading(false);
    }
  };

  const handleAppendTimeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!timelineForm.description.trim()) {
      setTimelineError('Event description is required.');
      return;
    }
    setTimelineLoading(true);
    setTimelineError(null);
    try {
      const occurredIso = new Date(timelineForm.event_occurred_at).toISOString();
      await incidentService.appendTimelineEvent(incidentId, {
        ...timelineForm,
        event_occurred_at: occurredIso,
      });
      setShowTimelineModal(false);
      setTimelineForm({
        event_type: 'CONTAINMENT_ACTION',
        event_occurred_at: new Date().toISOString().slice(0, 16),
        description: '',
        source: 'MANUAL_ENTRY',
      });
      await fetchIncidentDetail();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setTimelineError(typeof detail === 'string' ? detail : 'Failed to append timeline event.');
    } finally {
      setTimelineLoading(false);
    }
  };

  const handleLinkControl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!controlForm.organization_control_id) {
      setControlError('Please select a control to link.');
      return;
    }
    setControlLoading(true);
    setControlError(null);
    try {
      await incidentService.linkControl(incidentId, controlForm);
      setShowControlModal(false);
      setControlForm({ organization_control_id: 0, relationship_type: 'FAILED_CONTROL', notes: '' });
      await fetchIncidentDetail();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setControlError(typeof detail === 'string' ? detail : 'Failed to link control.');
    } finally {
      setControlLoading(false);
    }
  };

  const handleUnlinkControl = async (linkId: number) => {
    if (!confirm('Are you sure you want to unlink this control?')) return;
    try {
      await incidentService.unlinkControl(incidentId, linkId);
      await fetchIncidentDetail();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to unlink control.');
    }
  };

  const handleLinkVendor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vendorForm.vendor_id) {
      setVendorError('Please select a vendor to link.');
      return;
    }
    setVendorLoading(true);
    setVendorError(null);
    try {
      await incidentService.linkVendor(incidentId, vendorForm);
      setShowVendorModal(false);
      setVendorForm({ vendor_id: 0, vendor_engagement_id: undefined, is_vendor_originated: true, notes: '' });
      await fetchIncidentDetail();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setVendorError(typeof detail === 'string' ? detail : 'Failed to link vendor.');
    } finally {
      setVendorLoading(false);
    }
  };

  const handleUnlinkVendor = async (linkId: number) => {
    if (!confirm('Are you sure you want to unlink this vendor?')) return;
    try {
      await incidentService.unlinkVendor(incidentId, linkId);
      await fetchIncidentDetail();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to unlink vendor.');
    }
  };

  const handleInitializeDisclosure = async (e: React.FormEvent) => {
    e.preventDefault();
    setDisclosureLoading(true);
    setDisclosureError(null);
    try {
      const trigIso = new Date(disclosureForm.triggered_at).toISOString();
      await incidentService.evaluateDisclosure(incidentId, {
        ...disclosureForm,
        triggered_at: trigIso,
      });
      setShowDisclosureModal(false);
      await fetchIncidentDetail();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setDisclosureError(typeof detail === 'string' ? detail : 'Failed to evaluate disclosure.');
    } finally {
      setDisclosureLoading(false);
    }
  };

  const handleNotifyDisclosure = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDisclosureForNotify) return;
    if (!notifyForm.notification_reference_code.trim()) {
      setNotifyError('Notification reference code is required.');
      return;
    }
    setNotifyLoading(true);
    setNotifyError(null);
    try {
      await incidentService.notifyDisclosure(selectedDisclosureForNotify.id, notifyForm);
      setSelectedDisclosureForNotify(null);
      setNotifyForm({ notification_reference_code: '', disclosure_notes: '' });
      await fetchIncidentDetail();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setNotifyError(typeof detail === 'string' ? detail : 'Failed to record notification.');
    } finally {
      setNotifyLoading(false);
    }
  };

  const handleExemptDisclosure = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDisclosureForExempt) return;
    if (!exemptForm.exemption_reason || exemptForm.exemption_reason.trim().length < 10) {
      setExemptError('Mandatory legal justification must be at least 10 characters.');
      return;
    }
    setExemptLoading(true);
    setExemptError(null);
    try {
      await incidentService.exemptDisclosure(selectedDisclosureForExempt.id, exemptForm);
      setSelectedDisclosureForExempt(null);
      setExemptForm({ exemption_reason: '' });
      await fetchIncidentDetail();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setExemptError(typeof detail === 'string' ? detail : 'Failed to record exemption.');
    } finally {
      setExemptLoading(false);
    }
  };

  if (loading || !incident) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 animate-spin text-red-600 mb-4" />
        <p className="text-gray-500">Loading incident command workspace...</p>
      </div>
    );
  }

  const isClosed = incident.status === 'CLOSED';
  const commanderUser = users.find((u) => u.id === incident.incident_commander_id);
  const businessOwnerUser = users.find((u) => u.id === incident.business_owner_id);
  const closedByUser = users.find((u) => u.id === incident.closed_by_id);

  // Lifecycle Steps Mapping
  const lifecycleSteps: IncidentStatus[] = [
    'DECLARED',
    'TRIAGED',
    'CONTAINED',
    'ERADICATED',
    'RECOVERED',
    'POST_MORTEM',
    'CLOSED',
  ];

  const currentStepIndex = lifecycleSteps.indexOf(incident.status);

  return (
    <div className="space-y-6 pb-16">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/incidents')}
            className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-red-600 dark:text-red-400">
                {incident.incident_code}
              </span>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                {incident.title}
              </h1>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Declared {new Date(incident.declared_at).toLocaleString()} • Incident Commander:{' '}
              <span className="font-semibold text-gray-800 dark:text-gray-200">
                {commanderUser?.full_name || commanderUser?.email || `User #${incident.incident_commander_id}`}
              </span>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {!isClosed && canManage && (
            <>
              <button
                onClick={() => setShowTransitionModal(true)}
                className="inline-flex items-center px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
              >
                <Zap className="w-3.5 h-3.5 mr-1.5" />
                Progress Lifecycle
              </button>
              <button
                onClick={() => {
                  setMaterialityForm({
                    is_material: !incident.is_material,
                    materiality_notes: '',
                  });
                  setShowMaterialityModal(true);
                }}
                className="inline-flex items-center px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
              >
                <AlertOctagon className="w-3.5 h-3.5 mr-1.5" />
                SEC Materiality
              </button>
              {incident.status === 'POST_MORTEM' && canClose && (
                <button
                  onClick={() => setShowCloseModal(true)}
                  className="inline-flex items-center px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
                >
                  <Lock className="w-3.5 h-3.5 mr-1.5" />
                  Four-Eyes Close
                </button>
              )}
            </>
          )}

          <button
            onClick={fetchIncidentDetail}
            className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Terminal Immutability Notice if CLOSED */}
      {isClosed && (
        <div className="bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 rounded-xl p-4 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-bold text-emerald-900 dark:text-emerald-200">
              Closed Security Incident — Immutable Record
            </h4>
            <p className="text-xs text-emerald-800 dark:text-emerald-300 mt-0.5">
              This incident was formally closed under four-eyes separation of duties review by{' '}
              <span className="font-semibold">
                {closedByUser?.full_name || closedByUser?.email || `User #${incident.closed_by_id}`}
              </span>{' '}
              on {new Date(incident.closed_at || '').toLocaleString()}. All metadata, linkages, and timeline events are permanently immutable.
            </p>
          </div>
        </div>
      )}

      {/* Visual Lifecycle Stepper */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="text-xs uppercase font-bold text-gray-500 dark:text-gray-400">
            Lifecycle Progress (Server-Authoritative)
          </div>
          <div className="text-xs font-semibold text-gray-600 dark:text-gray-300">
            Active Phase: <span className="font-bold text-red-600 dark:text-red-400">{incident.status}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {lifecycleSteps.map((step, index) => {
            const isPassed = index < currentStepIndex || isClosed;
            const isCurrent = step === incident.status;
            return (
              <div
                key={step}
                className={`p-3 rounded-lg border text-center transition ${
                  isCurrent
                    ? 'bg-red-50 dark:bg-red-950/40 border-red-500 text-red-700 dark:text-red-300 ring-2 ring-red-500/20 font-bold'
                    : isPassed
                    ? 'bg-gray-50 dark:bg-gray-750 border-emerald-300 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 font-medium'
                    : 'bg-gray-50 dark:bg-gray-800/40 border-gray-200 dark:border-gray-700 text-gray-400'
                }`}
              >
                <div className="text-xs font-mono">{index + 1}. {step}</div>
                <div className="text-[10px] mt-1 text-gray-400">
                  {step === 'DECLARED' && new Date(incident.declared_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  {step === 'CONTAINED' && incident.contained_at && new Date(incident.contained_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  {step === 'ERADICATED' && incident.eradicated_at && new Date(incident.eradicated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  {step === 'RECOVERED' && incident.recovered_at && new Date(incident.recovered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  {step === 'CLOSED' && incident.closed_at && new Date(incident.closed_at).toLocaleDateString()}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-6 overflow-x-auto">
          {[
            { id: 'overview', label: 'Overview & Telemetry', icon: Shield },
            { id: 'timeline', label: `Response Timeline (${incident.timeline_events.length})`, icon: History },
            { id: 'controls', label: `Controls & Root Cause (${incident.control_links.length})`, icon: FileCheck2 },
            { id: 'vendors', label: `Vendors & Supply Chain (${incident.vendor_links.length})`, icon: Building2 },
            { id: 'disclosures', label: `Regulatory Disclosures (${incident.disclosures.length})`, icon: Scale },
            { id: 'closure', label: 'Governance & Closure', icon: UserCheck },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-3 px-1 border-b-2 font-medium text-sm inline-flex items-center gap-2 whitespace-nowrap transition ${
                  active
                    ? 'border-red-600 text-red-600 dark:text-red-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* ── TAB 1: OVERVIEW & SERVER TELEMETRY ──────────────────────────────── */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Server-Authoritative Telemetry Header Box */}
          <div className="bg-gradient-to-r from-gray-900 to-gray-800 text-white rounded-2xl p-6 shadow-md">
            <div className="flex items-center justify-between pb-4 border-b border-gray-700">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-red-400" />
                <h3 className="font-bold text-base">
                  Authoritative Incident Posture & Telemetry
                </h3>
              </div>
              <span className="px-2 py-0.5 text-xs bg-gray-700 rounded font-mono text-gray-300">
                Server Derived
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 mt-4">
              <div>
                <div className="text-xs text-gray-400 uppercase">TTC (Time to Contain)</div>
                <div className="text-2xl font-bold text-white mt-1">
                  {incident.ttc_hours !== null && incident.ttc_hours !== undefined
                    ? `${incident.ttc_hours} hrs`
                    : 'Pending Containment'}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400 uppercase">MTTR (Time to Recover)</div>
                <div className="text-2xl font-bold text-emerald-400 mt-1">
                  {incident.mttr_hours !== null && incident.mttr_hours !== undefined
                    ? `${incident.mttr_hours} hrs`
                    : 'Pending Recovery'}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400 uppercase">Incident Age</div>
                <div className="text-2xl font-bold text-blue-400 mt-1">
                  {incident.incident_age_hours !== null && incident.incident_age_hours !== undefined
                    ? `${incident.incident_age_hours} hrs`
                    : '—'}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400 uppercase">SEC Item 1.05 Materiality</div>
                <div className="text-2xl font-bold mt-1">
                  {incident.is_material ? (
                    <span className="text-purple-400">Material Breach</span>
                  ) : (
                    <span className="text-gray-400">Non-Material</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Core Metadata Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase">
                    Incident Narrative & Scope
                  </h3>
                  {!isClosed && canManage && (
                    <button
                      onClick={() => setShowEditModal(true)}
                      className="inline-flex items-center text-xs font-semibold text-red-600 dark:text-red-400 hover:underline"
                    >
                      <Edit3 className="w-3.5 h-3.5 mr-1" />
                      Edit Details
                    </button>
                  )}
                </div>

                <div className="space-y-4 text-sm">
                  <div>
                    <label className="text-xs text-gray-400 uppercase font-semibold">Technical Narrative</label>
                    <p className="text-gray-800 dark:text-gray-200 mt-1 whitespace-pre-wrap leading-relaxed">
                      {incident.description}
                    </p>
                  </div>

                  {incident.affected_systems_summary && (
                    <div>
                      <label className="text-xs text-gray-400 uppercase font-semibold">Affected Systems</label>
                      <p className="text-gray-800 dark:text-gray-200 mt-1">
                        {incident.affected_systems_summary}
                      </p>
                    </div>
                  )}

                  {incident.root_cause_narrative && (
                    <div className="p-3 bg-gray-50 dark:bg-gray-750 rounded-lg">
                      <label className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                        Root Cause Narrative
                      </label>
                      <p className="text-gray-800 dark:text-gray-200 mt-1">
                        {incident.root_cause_narrative}
                      </p>
                    </div>
                  )}

                  {incident.lessons_learned && (
                    <div className="p-3 bg-blue-50 dark:bg-blue-950/40 rounded-lg">
                      <label className="text-xs font-bold text-blue-800 dark:text-blue-300 uppercase">
                        Lessons Learned & Hardening Directives
                      </label>
                      <p className="text-blue-900 dark:text-blue-200 mt-1">
                        {incident.lessons_learned}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Side Key Properties */}
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm space-y-4">
                <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase">
                  Incident Attributes
                </h3>

                <div className="space-y-3 text-xs">
                  <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700">
                    <span className="text-gray-500">Severity</span>
                    <span className="font-semibold text-gray-900 dark:text-white">{incident.severity}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700">
                    <span className="text-gray-500">Category</span>
                    <span className="font-mono text-gray-900 dark:text-white">{incident.category}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700">
                    <span className="text-gray-500">Affected Records</span>
                    <span className="font-mono text-gray-900 dark:text-white">
                      {incident.affected_record_count.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700">
                    <span className="text-gray-500">Est. Financial Impact</span>
                    <span className="font-mono font-bold text-gray-900 dark:text-white">
                      ${incident.financial_impact_estimate.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700">
                    <span className="text-gray-500">Business Owner</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {businessOwnerUser?.full_name || 'Unassigned'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-gray-500">Root Cause Class</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {incident.root_cause_classification || 'Under Investigation'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: RESPONSE TIMELINE (APPEND-ONLY) ─────────────────────────── */}
      {activeTab === 'timeline' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-gray-900 dark:text-white">
                Chronological Forensic Timeline
              </h3>
              <p className="text-xs text-gray-500">
                Immutable ledger. Events are strictly append-only to preserve forensic evidentiary integrity.
              </p>
            </div>
            {!isClosed && canManage && (
              <button
                onClick={() => setShowTimelineModal(true)}
                className="inline-flex items-center px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
              >
                <Plus className="w-3.5 h-3.5 mr-1" />
                Append Forensic Note
              </button>
            )}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
            <div className="relative border-l-2 border-red-500/40 ml-4 space-y-6 pb-2">
              {incident.timeline_events.map((event) => {
                const actorUser = users.find((u) => u.id === event.actor_id);
                return (
                  <div key={event.id} className="relative pl-6">
                    <div className="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-red-600 ring-4 ring-white dark:ring-gray-800" />
                    <div className="bg-gray-50 dark:bg-gray-750 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">
                            {event.event_type}
                          </span>
                          <span className="text-xs font-semibold text-gray-900 dark:text-white">
                            {actorUser?.full_name || actorUser?.email || `Actor #${event.actor_id}`}
                          </span>
                          <span className="text-[10px] text-gray-400 uppercase font-mono">
                            • {event.source}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                          {new Date(event.event_occurred_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-800 dark:text-gray-200 mt-2 whitespace-pre-wrap">
                        {event.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 3: CONTROLS & ROOT CAUSE LINKAGE ───────────────────────────── */}
      {activeTab === 'controls' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-gray-900 dark:text-white">
                Linked Organization Controls & Deficiencies
              </h3>
              <p className="text-xs text-gray-500">
                Map failing or deficient controls directly to reactive security incidents.
              </p>
            </div>
            {!isClosed && canManage && (
              <button
                onClick={() => setShowControlModal(true)}
                className="inline-flex items-center px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
              >
                <Plus className="w-3.5 h-3.5 mr-1" />
                Link Control
              </button>
            )}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
              <thead className="bg-gray-50 dark:bg-gray-900/60 text-xs uppercase font-semibold text-gray-700 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-4">Control ID</th>
                  <th className="px-6 py-4">Relationship Type</th>
                  <th className="px-6 py-4">Notes</th>
                  <th className="px-6 py-4">Linked At</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {incident.control_links.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                      No controls currently linked to this incident.
                    </td>
                  </tr>
                ) : (
                  incident.control_links.map((link) => (
                    <tr key={link.id} className="hover:bg-gray-50 dark:hover:bg-gray-750/50">
                      <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">
                        Control #{link.organization_control_id}
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-0.5 text-xs font-semibold rounded bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">
                          {link.relationship_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs">{link.notes || '—'}</td>
                      <td className="px-6 py-4 text-xs text-gray-500">
                        {new Date(link.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {!isClosed && canManage && (
                          <button
                            onClick={() => handleUnlinkControl(link.id)}
                            className="text-gray-400 hover:text-red-600 transition"
                          >
                            <Trash2 className="w-4 h-4" />
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

      {/* ── TAB 4: VENDORS / SUPPLY CHAIN LINKAGE ───────────────────────────── */}
      {activeTab === 'vendors' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-gray-900 dark:text-white">
                Linked Third-Party Vendors & Engagements
              </h3>
              <p className="text-xs text-gray-500">
                Track supply-chain origination and vendor security incident exposure.
              </p>
            </div>
            {!isClosed && canManage && (
              <button
                onClick={() => setShowVendorModal(true)}
                className="inline-flex items-center px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
              >
                <Plus className="w-3.5 h-3.5 mr-1" />
                Link Vendor
              </button>
            )}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
              <thead className="bg-gray-50 dark:bg-gray-900/60 text-xs uppercase font-semibold text-gray-700 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-4">Vendor ID</th>
                  <th className="px-6 py-4">Engagement ID</th>
                  <th className="px-6 py-4">Originated From Vendor</th>
                  <th className="px-6 py-4">Notes</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {incident.vendor_links.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                      No vendors currently linked to this incident.
                    </td>
                  </tr>
                ) : (
                  incident.vendor_links.map((link) => {
                    const vnd = vendors.find((v) => v.id === link.vendor_id);
                    return (
                      <tr key={link.id} className="hover:bg-gray-50 dark:hover:bg-gray-750/50">
                        <td className="px-6 py-4 font-semibold text-gray-900 dark:text-white">
                          {vnd?.legal_name || `Vendor #${link.vendor_id}`} ({vnd?.vendor_code || 'VND'})
                        </td>
                        <td className="px-6 py-4 font-mono text-xs">
                          {link.vendor_engagement_id ? `Engagement #${link.vendor_engagement_id}` : 'General / Direct'}
                        </td>
                        <td className="px-6 py-4">
                          {link.is_vendor_originated ? (
                            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300">
                              Yes — Supply Chain
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">No</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-xs">{link.notes || '—'}</td>
                        <td className="px-6 py-4 text-right">
                          {!isClosed && canManage && (
                            <button
                              onClick={() => handleUnlinkVendor(link.id)}
                              className="text-gray-400 hover:text-red-600 transition"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── TAB 5: STATUTORY REGULATORY DISCLOSURES ─────────────────────────── */}
      {activeTab === 'disclosures' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-gray-900 dark:text-white">
                Statutory Breach Disclosure Obligations & Countdown
              </h3>
              <p className="text-xs text-gray-500">
                Authoritative server-computed deadlines (GDPR 72h, SEC 4-Business-Days, HHS 60d, PCI 24h, NYDFS 72h).
              </p>
            </div>
            {!isClosed && canDisclose && (
              <button
                onClick={() => setShowDisclosureModal(true)}
                className="inline-flex items-center px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
              >
                <Plus className="w-3.5 h-3.5 mr-1" />
                Initialize Disclosure Clock
              </button>
            )}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
              <thead className="bg-gray-50 dark:bg-gray-900/60 text-xs uppercase font-semibold text-gray-700 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-4">Regulator</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Statutory Deadline</th>
                  <th className="px-6 py-4">Trigger Vector</th>
                  <th className="px-6 py-4">Audit Version</th>
                  <th className="px-6 py-4">Notification Ref / Exemption</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {incident.disclosures.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                      No statutory disclosures currently active for this incident.
                    </td>
                  </tr>
                ) : (
                  incident.disclosures.map((disc) => {
                    const isOverdue =
                      disc.status === 'OVERDUE' ||
                      (disc.status === 'PENDING' && new Date(disc.deadline_at) < new Date());
                    return (
                      <tr key={disc.id} className="hover:bg-gray-50 dark:hover:bg-gray-750/50">
                        <td className="px-6 py-4 font-bold text-gray-900 dark:text-white">
                          {disc.regulator}
                        </td>
                        <td className="px-6 py-4">
                          {disc.status === 'NOTIFIED' ? (
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                              NOTIFIED
                            </span>
                          ) : disc.status === 'NOT_APPLICABLE' ? (
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                              EXEMPT
                            </span>
                          ) : isOverdue ? (
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300 animate-pulse">
                              OVERDUE
                            </span>
                          ) : (
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300">
                              PENDING DUE
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 font-mono text-xs font-semibold">
                          {new Date(disc.deadline_at).toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-xs font-mono text-gray-500">
                          {disc.trigger_type}
                        </td>
                        <td className="px-6 py-4 text-xs font-mono text-gray-400">
                          v{disc.rule_version} ({disc.calculation_version})
                        </td>
                        <td className="px-6 py-4 text-xs">
                          {disc.notification_reference_code ? (
                            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                              Ref: {disc.notification_reference_code}
                            </span>
                          ) : disc.exemption_reason ? (
                            <span className="italic text-gray-500 truncate max-w-xs block">
                              Exempt: {disc.exemption_reason}
                            </span>
                          ) : (
                            <span className="text-gray-400">Awaiting action</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right space-x-2">
                          {!isClosed && canDisclose && disc.status === 'PENDING' && (
                            <>
                              <button
                                onClick={() => setSelectedDisclosureForNotify(disc)}
                                className="text-xs font-bold text-emerald-600 hover:underline"
                              >
                                Notify
                              </button>
                              <button
                                onClick={() => setSelectedDisclosureForExempt(disc)}
                                className="text-xs font-bold text-gray-500 hover:underline"
                              >
                                Exempt
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── TAB 6: GOVERNANCE & FOUR-EYES CLOSURE ───────────────────────────── */}
      {activeTab === 'closure' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-gray-900 dark:text-white uppercase flex items-center gap-2">
              <Lock className="w-5 h-5 text-indigo-600" />
              Four-Eyes Incident Closure Governance
            </h3>

            <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
              In accordance with enterprise risk governance and forensic auditability invariants, an incident cannot be closed by its assigned Incident Commander. Independent management sign-off (Manager or Admin role) and completion of the <span className="font-semibold text-red-600">POST_MORTEM</span> phase are strictly required before permanent closure.
            </p>

            <div className="p-4 bg-gray-50 dark:bg-gray-750 rounded-xl border border-gray-200 dark:border-gray-700 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Incident Commander:</span>
                <span className="font-bold text-gray-900 dark:text-white">
                  {commanderUser?.full_name || commanderUser?.email || `User #${incident.incident_commander_id}`}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Current Phase:</span>
                <span className="font-bold text-gray-900 dark:text-white">{incident.status}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Current Authenticated User:</span>
                <span className="font-bold text-indigo-600 dark:text-indigo-400">
                  {user?.full_name || user?.email} ({user?.role})
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Four-Eyes Separation Check:</span>
                {user?.id === incident.incident_commander_id ? (
                  <span className="text-red-600 font-bold">
                    VIOLATION — You are the Incident Commander (Cannot close own incident)
                  </span>
                ) : (
                  <span className="text-emerald-600 font-bold">
                    VALID — Independent reviewer identified
                  </span>
                )}
              </div>
            </div>

            {incident.closure_notes && (
              <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 rounded-xl border border-emerald-300 dark:border-emerald-800 space-y-2">
                <div className="text-xs font-bold uppercase text-emerald-800 dark:text-emerald-300">
                  Authoritative Closure Justification
                </div>
                <p className="text-sm text-emerald-900 dark:text-emerald-200 whitespace-pre-wrap">
                  {incident.closure_notes}
                </p>
              </div>
            )}

            {!isClosed && incident.status === 'POST_MORTEM' && canClose && (
              <div className="pt-2">
                <button
                  onClick={() => setShowCloseModal(true)}
                  disabled={user?.id === incident.incident_commander_id}
                  className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold shadow-sm transition disabled:opacity-50"
                >
                  Execute Four-Eyes Incident Closure
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── MODAL: PROGRESS LIFECYCLE ────────────────────────────────────────── */}
      {showTransitionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">
              Progress Incident Lifecycle
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Current state: <span className="font-bold text-red-600">{incident.status}</span>
            </p>

            {transitionError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                {transitionError}
              </div>
            )}

            <form onSubmit={handleTransition} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Target State *
                </label>
                <select
                  value={targetStatus}
                  onChange={(e) => setTargetStatus(e.target.value as IncidentStatus)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                >
                  <option value="TRIAGED">TRIAGED</option>
                  <option value="CONTAINED">CONTAINED</option>
                  <option value="ERADICATED">ERADICATED</option>
                  <option value="RECOVERED">RECOVERED</option>
                  <option value="POST_MORTEM">POST_MORTEM</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Operational Notes
                </label>
                <textarea
                  rows={3}
                  placeholder="Reason / operational context for status transition..."
                  value={transitionNotes}
                  onChange={(e) => setTransitionNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTransitionModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={transitionLoading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {transitionLoading ? 'Updating...' : 'Confirm Transition'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: FOUR-EYES CLOSURE ────────────────────────────────────────── */}
      {showCloseModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
              <Lock className="w-5 h-5 text-emerald-600" />
              Four-Eyes Incident Closure Execution
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Requires independent management review. Once closed, this record becomes permanently immutable.
            </p>

            {closeError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                {closeError}
              </div>
            )}

            <form onSubmit={handleFourEyesClose} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Root Cause Classification *
                </label>
                <select
                  value={closeForm.root_cause_classification}
                  onChange={(e) =>
                    setCloseForm({
                      ...closeForm,
                      root_cause_classification: e.target.value as RootCauseClassification,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                >
                  <option value="CONTROL_FAILURE">CONTROL_FAILURE</option>
                  <option value="HUMAN_ERROR">HUMAN_ERROR</option>
                  <option value="ZERO_DAY">ZERO_DAY</option>
                  <option value="THIRD_PARTY_FAILURE">THIRD_PARTY_FAILURE</option>
                  <option value="CONFIGURATION_DRIFT">CONFIGURATION_DRIFT</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Closure Notes & Management Review * (Min 10 chars)
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Provide comprehensive executive management closure rationale and verification notes..."
                  value={closeForm.closure_notes}
                  onChange={(e) => setCloseForm({ ...closeForm, closure_notes: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Lessons Learned
                </label>
                <textarea
                  rows={2}
                  placeholder="Preventative recommendations and policy adjustments..."
                  value={closeForm.lessons_learned || ''}
                  onChange={(e) => setCloseForm({ ...closeForm, lessons_learned: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCloseModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={closeLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {closeLoading ? 'Closing...' : 'Confirm Closure'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: APPEND TIMELINE EVENT ────────────────────────────────────── */}
      {showTimelineModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">
              Append Forensic Timeline Event
            </h3>

            {timelineError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                {timelineError}
              </div>
            )}

            <form onSubmit={handleAppendTimeline} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Event Type *
                </label>
                <select
                  value={timelineForm.event_type}
                  onChange={(e) =>
                    setTimelineForm({
                      ...timelineForm,
                      event_type: e.target.value as TimelineEventType,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                >
                  <option value="CONTAINMENT_ACTION">CONTAINMENT_ACTION</option>
                  <option value="ERADICATION_STEP">ERADICATION_STEP</option>
                  <option value="EVIDENCE_COLLECTED">EVIDENCE_COLLECTED</option>
                  <option value="REGULATOR_NOTIFIED">REGULATOR_NOTIFIED</option>
                  <option value="COMMAND_TRANSFER">COMMAND_TRANSFER</option>
                  <option value="POST_MORTEM_NOTE">POST_MORTEM_NOTE</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Event Occurred Timestamp *
                </label>
                <input
                  type="datetime-local"
                  required
                  value={timelineForm.event_occurred_at}
                  onChange={(e) =>
                    setTimelineForm({ ...timelineForm, event_occurred_at: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Forensic Description *
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Record forensic actions taken, commands executed, or IOCs collected..."
                  value={timelineForm.description}
                  onChange={(e) => setTimelineForm({ ...timelineForm, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTimelineModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={timelineLoading}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {timelineLoading ? 'Appending...' : 'Append Entry'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: LINK CONTROL ─────────────────────────────────────────────── */}
      {showControlModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">
              Link Deficient Organization Control
            </h3>

            {controlError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                {controlError}
              </div>
            )}

            <form onSubmit={handleLinkControl} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Select Control *
                </label>
                <select
                  value={controlForm.organization_control_id}
                  onChange={(e) =>
                    setControlForm({
                      ...controlForm,
                      organization_control_id: parseInt(e.target.value, 10) || 0,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                >
                  <option value={0}>Select a control...</option>
                  {controls.map((c) => (
                    <option key={c.id} value={c.id}>
                      Control #{c.id} (Subcategory #{c.subcategory_id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Relationship Type *
                </label>
                <select
                  value={controlForm.relationship_type}
                  onChange={(e) =>
                    setControlForm({
                      ...controlForm,
                      relationship_type: e.target.value as IncidentControlRelationship,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                >
                  <option value="FAILED_CONTROL">FAILED_CONTROL</option>
                  <option value="DEFICIENT_CONTROL">DEFICIENT_CONTROL</option>
                  <option value="CIRCUMVENTED_CONTROL">CIRCUMVENTED_CONTROL</option>
                  <option value="DETECTING_CONTROL">DETECTING_CONTROL</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Linkage Notes
                </label>
                <textarea
                  rows={2}
                  placeholder="Control failure explanation / circumvented rule..."
                  value={controlForm.notes || ''}
                  onChange={(e) => setControlForm({ ...controlForm, notes: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowControlModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={controlLoading}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {controlLoading ? 'Linking...' : 'Link Control'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: LINK VENDOR ──────────────────────────────────────────────── */}
      {showVendorModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">
              Link Third-Party Vendor
            </h3>

            {vendorError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                {vendorError}
              </div>
            )}

            <form onSubmit={handleLinkVendor} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Select Vendor *
                </label>
                <select
                  value={vendorForm.vendor_id}
                  onChange={(e) => handleVendorSelect(parseInt(e.target.value, 10) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                >
                  <option value={0}>Select a vendor...</option>
                  {vendors.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.legal_name} ({v.vendor_code})
                    </option>
                  ))}
                </select>
              </div>

              {engagements.length > 0 && (
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Select Specific Engagement (Optional)
                  </label>
                  <select
                    value={vendorForm.vendor_engagement_id || ''}
                    onChange={(e) =>
                      setVendorForm({
                        ...vendorForm,
                        vendor_engagement_id: e.target.value
                          ? parseInt(e.target.value, 10)
                          : undefined,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                  >
                    <option value="">All Engagements / Direct Vendor Level</option>
                    {engagements.map((eng) => (
                      <option key={eng.id} value={eng.id}>
                        {eng.engagement_name} ({eng.engagement_code})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_vendor_originated"
                  checked={vendorForm.is_vendor_originated}
                  onChange={(e) =>
                    setVendorForm({ ...vendorForm, is_vendor_originated: e.target.checked })
                  }
                  className="rounded border-gray-300 text-red-600 focus:ring-red-500"
                />
                <label
                  htmlFor="is_vendor_originated"
                  className="text-xs font-medium text-gray-700 dark:text-gray-300"
                >
                  Incident originated via vendor infrastructure (Supply-chain breach)
                </label>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Notes
                </label>
                <textarea
                  rows={2}
                  placeholder="Integration token, API compromise, or vendor advisory ref..."
                  value={vendorForm.notes || ''}
                  onChange={(e) => setVendorForm({ ...vendorForm, notes: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowVendorModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={vendorLoading}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {vendorLoading ? 'Linking...' : 'Link Vendor'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: INITIALIZE DISCLOSURE ───────────────────────────────────── */}
      {showDisclosureModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">
              Initialize Statutory Disclosure Clock
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Server automatically evaluates statutory rules and business-day calendars.
            </p>

            {disclosureError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                {disclosureError}
              </div>
            )}

            <form onSubmit={handleInitializeDisclosure} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Regulator Authority *
                </label>
                <select
                  value={disclosureForm.regulator}
                  onChange={(e) =>
                    setDisclosureForm({
                      ...disclosureForm,
                      regulator: e.target.value as Regulator,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                >
                  <option value="GDPR_DPA">GDPR Article 33 (72h)</option>
                  <option value="SEC_8K">SEC Item 1.05 Form 8-K (4 Business Days)</option>
                  <option value="NYDFS">NYDFS 23 NYCRR 500.17 (72h)</option>
                  <option value="PCI_SSC">PCI-DSS Requirement 12.10.5 (24h)</option>
                  <option value="HHS_OCR">HIPAA Breach Notification Rule (60 Days)</option>
                  <option value="STATE_AG">US State Attorney General Baseline (30 Days)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Trigger Vector *
                </label>
                <select
                  value={disclosureForm.trigger_type}
                  onChange={(e) =>
                    setDisclosureForm({
                      ...disclosureForm,
                      trigger_type: e.target.value as any,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                >
                  <option value="INCIDENT_DETECTION">INCIDENT_DETECTION</option>
                  <option value="MATERIALITY_DETERMINATION">MATERIALITY_DETERMINATION</option>
                  <option value="PHI_THRESHOLD_BREACH">PHI_THRESHOLD_BREACH</option>
                  <option value="CDE_COMPROMISE">CDE_COMPROMISE</option>
                  <option value="LEGAL_DIRECTIVE">LEGAL_DIRECTIVE</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Trigger Timestamp *
                </label>
                <input
                  type="datetime-local"
                  required
                  value={disclosureForm.triggered_at}
                  onChange={(e) =>
                    setDisclosureForm({ ...disclosureForm, triggered_at: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDisclosureModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={disclosureLoading}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {disclosureLoading ? 'Evaluating...' : 'Initialize Clock'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: RECORD NOTIFICATION ──────────────────────────────────────── */}
      {selectedDisclosureForNotify && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">
              Record {selectedDisclosureForNotify.regulator} Notification
            </h3>

            {notifyError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                {notifyError}
              </div>
            )}

            <form onSubmit={handleNotifyDisclosure} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Regulator Notification Reference Code *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. DPA-IRE-2026-9812 / SEC-8K-ACC-0001"
                  value={notifyForm.notification_reference_code}
                  onChange={(e) =>
                    setNotifyForm({ ...notifyForm, notification_reference_code: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Disclosure Notes & Portal Reference
                </label>
                <textarea
                  rows={3}
                  placeholder="Online portal confirmation, recipient officer, or filing transmission notes..."
                  value={notifyForm.disclosure_notes || ''}
                  onChange={(e) =>
                    setNotifyForm({ ...notifyForm, disclosure_notes: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedDisclosureForNotify(null)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={notifyLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {notifyLoading ? 'Recording...' : 'Confirm Notification'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: RECORD EXEMPTION ─────────────────────────────────────────── */}
      {selectedDisclosureForExempt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">
              Record {selectedDisclosureForExempt.regulator} Legal Exemption
            </h3>

            {exemptError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                {exemptError}
              </div>
            )}

            <form onSubmit={handleExemptDisclosure} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Mandatory Legal Exemption Justification * (Min 10 chars)
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Record formal legal counsel rationale for exemption (e.g. encrypted data safe harbor, no customer PII affected)..."
                  value={exemptForm.exemption_reason}
                  onChange={(e) => setExemptForm({ exemption_reason: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedDisclosureForExempt(null)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={exemptLoading}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-800 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {exemptLoading ? 'Recording...' : 'Confirm Exemption'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: EDIT METADATA ────────────────────────────────────────────── */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700 max-h-[90vh] overflow-y-auto">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">
              Update Incident Metadata & Narrative
            </h3>

            {editError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                {editError}
              </div>
            )}

            <form onSubmit={handleUpdateMetadata} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Title
                </label>
                <input
                  type="text"
                  value={editForm.title || ''}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Narrative / Synopsis
                </label>
                <textarea
                  rows={3}
                  value={editForm.description || ''}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Affected Systems Summary
                </label>
                <input
                  type="text"
                  value={editForm.affected_systems_summary || ''}
                  onChange={(e) =>
                    setEditForm({ ...editForm, affected_systems_summary: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Affected Records
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={editForm.affected_record_count || 0}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        affected_record_count: Math.max(0, parseInt(e.target.value, 10) || 0),
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Est. Financial Impact ($)
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={editForm.financial_impact_estimate || 0}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        financial_impact_estimate: Math.max(0, parseFloat(e.target.value) || 0),
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Root Cause Narrative
                </label>
                <textarea
                  rows={2}
                  value={editForm.root_cause_narrative || ''}
                  onChange={(e) =>
                    setEditForm({ ...editForm, root_cause_narrative: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editLoading}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {editLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: MATERIALITY DETERMINATION ────────────────────────────────── */}
      {showMaterialityModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
              <AlertOctagon className="w-5 h-5 text-purple-600" />
              SEC Item 1.05 Materiality Determination
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Determining an incident as material triggers the statutory 4-business-day SEC Form 8-K disclosure clock.
            </p>

            {materialityError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                {materialityError}
              </div>
            )}

            <form onSubmit={handleSetMateriality} className="space-y-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_material_toggle"
                  checked={materialityForm.is_material}
                  onChange={(e) =>
                    setMaterialityForm({ ...materialityForm, is_material: e.target.checked })
                  }
                  className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                />
                <label
                  htmlFor="is_material_toggle"
                  className="text-xs font-bold text-gray-900 dark:text-white"
                >
                  Affirm Material Cybersecurity Incident Status
                </label>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Materiality Rationale & Legal Counsel Notes
                </label>
                <textarea
                  rows={3}
                  placeholder="Record qualitative and quantitative impact determination factors..."
                  value={materialityForm.materiality_notes || ''}
                  onChange={(e) =>
                    setMaterialityForm({ ...materialityForm, materiality_notes: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowMaterialityModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={materialityLoading}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {materialityLoading ? 'Saving...' : 'Confirm Determination'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
