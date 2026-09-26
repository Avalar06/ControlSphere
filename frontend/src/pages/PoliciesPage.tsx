import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Plus,
  Search,
  AlertCircle,
  History,
  ArrowRight,
  Users,
  FileCheck2,
  Lock,
  Play,
  StopCircle,
  FileBadge,
  Clock,
  XCircle,
  ShieldAlert,
  ListChecks,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import type {
  Policy,
  PolicyStatus,
  PolicyType,
  PolicyTelemetry,
  User,
  PolicyAttestationCampaign,
  PolicyCampaignStatus,
  CampaignTargetType,
  UserAttestationRecord,
  SecurityException,
} from '../types';
import { Card, CardHeader } from '../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

export const PoliciesPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const [activeTab, setActiveTab] = useState<'POLICIES' | 'CAMPAIGNS'>('POLICIES');

  // Policy & Telemetry State
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [telemetry, setTelemetry] = useState<PolicyTelemetry | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Policy Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedType, setSelectedType] = useState<string>('ALL');

  // Create Policy Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [policyType, setPolicyType] = useState<PolicyType>('INFORMATION_SECURITY');
  const [initialContent, setInitialContent] = useState('');
  const [ownerId, setOwnerId] = useState<string>('');
  const [isCreating, setIsCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Campaigns State
  const [campaigns, setCampaigns] = useState<PolicyAttestationCampaign[]>([]);
  const [campaignSearch, setCampaignSearch] = useState('');
  const [campaignStatusFilter, setCampaignStatusFilter] = useState<string>('ALL');
  const [isCampaignModalOpen, setIsCampaignModalOpen] = useState(false);
  const [campaignFormError, setCampaignFormError] = useState<string | null>(null);
  const [isCreatingCampaign, setIsCreatingCampaign] = useState(false);

  // Campaign Roster & Exemption Modal State
  const [selectedRosterCampaign, setSelectedRosterCampaign] = useState<PolicyAttestationCampaign | null>(null);
  const [campaignRecords, setCampaignRecords] = useState<UserAttestationRecord[]>([]);
  const [isRosterLoading, setIsRosterLoading] = useState(false);
  const [exceptions, setExceptions] = useState<SecurityException[]>([]);
  const [exemptRecordTarget, setExemptRecordTarget] = useState<UserAttestationRecord | null>(null);
  const [exemptExceptionId, setExemptExceptionId] = useState<string>('');
  const [exemptReason, setExemptReason] = useState<string>('');
  const [isSubmittingExemption, setIsSubmittingExemption] = useState(false);

  // Campaign Form State
  const [campCode, setCampCode] = useState('');
  const [campTitle, setCampTitle] = useState('');
  const [campDescription, setCampDescription] = useState('');
  const [campPolicyId, setCampPolicyId] = useState<string>('');
  const [campVersionId, setCampVersionId] = useState<string>('');
  const [campTargetType, setCampTargetType] = useState<CampaignTargetType>('ALL_USERS');
  const [campTargetRole, setCampTargetRole] = useState<string>('');
  const [campDueDate, setCampDueDate] = useState<string>('');
  const [campGracePeriod, setCampGracePeriod] = useState<number>(0);

  const fetchTelemetry = async () => {
    try {
      const { data } = await api.get<PolicyTelemetry>('/api/v1/policies/telemetry');
      setTelemetry(data);
    } catch {
      // Telemetry is non-blocking
    }
  };

  const fetchPolicies = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Policy[]>('/api/v1/policies');
      setPolicies(data);

      const { data: userList } = await api.get<User[]>('/api/v1/users');
      setUsers(userList);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load organization policies.');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCampaigns = async () => {
    try {
      const { data } = await api.get<PolicyAttestationCampaign[]>('/api/v1/policies/campaigns');
      setCampaigns(data);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load attestation campaigns.');
    }
  };

  useEffect(() => {
    fetchPolicies();
    fetchCampaigns();
    fetchTelemetry();
  }, []);

  const handleCreatePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsCreating(true);

    try {
      await api.post('/api/v1/policies', {
        title,
        description,
        policy_type: policyType,
        initial_content: initialContent,
        owner_id: ownerId ? parseInt(ownerId, 10) : null,
      });

      setIsModalOpen(false);
      setTitle('');
      setDescription('');
      setInitialContent('');
      setOwnerId('');
      setSuccessMessage('Policy draft successfully authored.');
      await fetchPolicies();
      await fetchTelemetry();
    } catch (err: any) {
      console.error(err);
      setFormError(err.response?.data?.detail || 'Failed to create policy.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    setCampaignFormError(null);
    setIsCreatingCampaign(true);

    try {
      const selectedPol = policies.find((p) => p.id === parseInt(campPolicyId, 10));
      const verId = campVersionId
        ? parseInt(campVersionId, 10)
        : selectedPol?.current_version?.id || (selectedPol?.versions && selectedPol.versions[0]?.id);

      if (!verId) {
        setCampaignFormError('The selected policy has no available version.');
        setIsCreatingCampaign(false);
        return;
      }

      await api.post('/api/v1/policies/campaigns', {
        campaign_code: campCode,
        title: campTitle,
        description: campDescription,
        policy_id: parseInt(campPolicyId, 10),
        version_id: verId,
        target_type: campTargetType,
        target_role: campTargetType === 'ROLE_BASED' ? campTargetRole : null,
        due_date: campDueDate,
        grace_period_days: campGracePeriod,
      });

      setIsCampaignModalOpen(false);
      setCampCode('');
      setCampTitle('');
      setCampDescription('');
      setCampPolicyId('');
      setCampVersionId('');
      setCampDueDate('');
      setCampGracePeriod(0);
      setSuccessMessage('Attestation campaign created in DRAFT status.');
      await fetchCampaigns();
      await fetchTelemetry();
    } catch (err: any) {
      console.error(err);
      setCampaignFormError(err.response?.data?.detail || 'Failed to create campaign.');
    } finally {
      setIsCreatingCampaign(false);
    }
  };

  const handleLaunchCampaign = async (campaignId: number) => {
    setError(null);
    try {
      await api.post(`/api/v1/policies/campaigns/${campaignId}/launch`);
      setSuccessMessage('Campaign launched. Target roster generated and pending attestations activated.');
      await fetchCampaigns();
      await fetchTelemetry();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to launch campaign.');
    }
  };

  const handleCloseCampaign = async (campaignId: number) => {
    setError(null);
    try {
      await api.post(`/api/v1/policies/campaigns/${campaignId}/close`);
      setSuccessMessage('Campaign formally closed.');
      await fetchCampaigns();
      await fetchTelemetry();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to close campaign.');
    }
  };

  const handleCancelCampaign = async (campaignId: number) => {
    setError(null);
    try {
      await api.post(`/api/v1/policies/campaigns/${campaignId}/cancel`, {
        reason: 'Cancelled by campaign administrator',
      });
      setSuccessMessage('Campaign cancelled.');
      await fetchCampaigns();
      await fetchTelemetry();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to cancel campaign.');
    }
  };

  const handleEvaluateOverdue = async (campaignId: number) => {
    setError(null);
    try {
      const { data } = await api.post<PolicyAttestationCampaign>(
        `/api/v1/policies/campaigns/${campaignId}/evaluate-overdue`
      );
      setSuccessMessage(
        `Overdue evaluation complete for ${data.campaign_code}: ${data.overdue_count || 0} overdue record(s).`
      );
      await fetchCampaigns();
      await fetchTelemetry();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to evaluate overdue records.');
    }
  };

  const handleOpenRoster = async (campaign: PolicyAttestationCampaign) => {
    setSelectedRosterCampaign(campaign);
    setIsRosterLoading(true);
    setExemptRecordTarget(null);
    try {
      const { data } = await api.get<UserAttestationRecord[]>(
        `/api/v1/policies/campaigns/${campaign.id}/records`
      );
      setCampaignRecords(data);
      const { data: excData } = await api.get<SecurityException[]>('/api/v1/exceptions');
      setExceptions(excData);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load campaign roster.');
    } finally {
      setIsRosterLoading(false);
    }
  };

  const handleSubmitExemption = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRosterCampaign || !exemptRecordTarget || !exemptExceptionId) return;
    setIsSubmittingExemption(true);
    try {
      await api.post(
        `/api/v1/policies/campaigns/${selectedRosterCampaign.id}/records/${exemptRecordTarget.id}/exempt`,
        {
          exemption_exception_id: parseInt(exemptExceptionId, 10),
          exemption_reason: exemptReason,
        }
      );
      setExemptRecordTarget(null);
      setExemptExceptionId('');
      setExemptReason('');
      await handleOpenRoster(selectedRosterCampaign);
      await fetchCampaigns();
      await fetchTelemetry();
      setSuccessMessage('Policy attestation exemption recorded and linked to approved POLICY_WAIVER exception.');
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to exempt attestation record.');
    } finally {
      setIsSubmittingExemption(false);
    }
  };

  const handleGenerateEvidence = async (campaignId: number) => {
    setError(null);
    try {
      const { data } = await api.post(`/api/v1/policies/campaigns/${campaignId}/evidence`);
      setSuccessMessage(`Audit evidence manifest generated (SHA-256: ${data.sha256_hash.substring(0, 16)}...). Created in UPLOADED status.`);
      await fetchCampaigns();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to generate evidence manifest.');
    }
  };

  const getStatusBadge = (status: PolicyStatus) => {
    switch (status) {
      case 'PUBLISHED':
        return <Badge variant="success">PUBLISHED</Badge>;
      case 'APPROVED':
        return <Badge variant="purple">APPROVED</Badge>;
      case 'UNDER_REVIEW':
        return <Badge variant="warning">UNDER REVIEW</Badge>;
      case 'ARCHIVED':
        return <Badge variant="default">ARCHIVED</Badge>;
      case 'DRAFT':
      default:
        return <Badge variant="info">DRAFT</Badge>;
    }
  };

  const getCampaignStatusBadge = (status: PolicyCampaignStatus) => {
    switch (status) {
      case 'ACTIVE':
        return <Badge variant="success">ACTIVE</Badge>;
      case 'COMPLETED':
        return <Badge variant="purple">COMPLETED</Badge>;
      case 'PAUSED':
        return <Badge variant="warning">PAUSED</Badge>;
      case 'CANCELLED':
        return <Badge variant="danger">CANCELLED</Badge>;
      case 'DRAFT':
      default:
        return <Badge variant="info">DRAFT</Badge>;
    }
  };

  const filteredPolicies = policies.filter((p) => {
    const matchesSearch =
      p.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesStatus = selectedStatus === 'ALL' || p.status === selectedStatus;
    const matchesType = selectedType === 'ALL' || p.policy_type === selectedType;
    return matchesSearch && matchesStatus && matchesType;
  });

  const filteredCampaigns = campaigns.filter((c) => {
    const matchesSearch =
      c.title.toLowerCase().includes(campaignSearch.toLowerCase()) ||
      c.campaign_code.toLowerCase().includes(campaignSearch.toLowerCase());
    const matchesStatus = campaignStatusFilter === 'ALL' || c.status === campaignStatusFilter;
    return matchesSearch && matchesStatus;
  });

  const selectedPolicyObj = policies.find((p) => p.id === parseInt(campPolicyId, 10));

  return (
    <div className="space-y-6">
      {/* Header & Primary Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <BookOpen className="text-indigo-400" size={22} />
            <span>Enterprise Policy & Workforce Attestation Governance</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative lifecycle governance, Four-Eyes cryptographic approvals, workforce distribution campaigns, and tamper-evident evidence manifests.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeTab === 'POLICIES' && hasPermission('policy:manage') && (
            <Button size="sm" variant="primary" onClick={() => setIsModalOpen(true)}>
              <Plus size={14} />
              Author Policy
            </Button>
          )}

          {activeTab === 'CAMPAIGNS' && hasPermission('policy:campaign_manage') && (
            <Button size="sm" variant="primary" onClick={() => setIsCampaignModalOpen(true)}>
              <Plus size={14} />
              Launch Campaign
            </Button>
          )}
        </div>
      </div>

      {/* Executive Telemetry Banner */}
      {telemetry && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <Card>
            <div className="p-3">
              <span className="text-[10px] text-slate-400 font-medium uppercase">Published Policies</span>
              <div className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
                {telemetry.published_policies} / {telemetry.total_policies}
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-3">
              <span className="text-[10px] text-slate-400 font-medium uppercase">Overdue Reviews</span>
              <div className={`text-lg font-bold font-mono mt-0.5 ${telemetry.overdue_review_policies > 0 ? 'text-rose-400' : 'text-slate-200'}`}>
                {telemetry.overdue_review_policies}
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-3">
              <span className="text-[10px] text-slate-400 font-medium uppercase">Active Campaigns</span>
              <div className="text-lg font-bold font-mono text-indigo-400 mt-0.5">
                {telemetry.active_campaigns}
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-3">
              <span className="text-[10px] text-slate-400 font-medium uppercase">Attestation Rate</span>
              <div className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
                {telemetry.overall_attestation_rate_pct}%
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-3">
              <span className="text-[10px] text-slate-400 font-medium uppercase">Exempted Waivers</span>
              <div className="text-lg font-bold font-mono text-purple-400 mt-0.5">
                {telemetry.exempted_records}
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-3">
              <span className="text-[10px] text-slate-400 font-medium uppercase">Overdue Records</span>
              <div className={`text-lg font-bold font-mono mt-0.5 ${telemetry.overdue_records > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
                {telemetry.overdue_records}
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Tab Switcher */}
      <div className="flex border-b border-slate-800 gap-6 text-xs font-medium">
        <button
          onClick={() => setActiveTab('POLICIES')}
          className={`pb-3 transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === 'POLICIES'
              ? 'border-indigo-500 text-indigo-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BookOpen size={14} />
          <span>Policies Repository ({policies.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('CAMPAIGNS')}
          className={`pb-3 transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === 'CAMPAIGNS'
              ? 'border-indigo-500 text-indigo-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users size={14} />
          <span>Attestation Campaigns ({campaigns.length})</span>
        </button>
      </div>

      {successMessage && (
        <div className="p-3 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
          <FileCheck2 size={15} />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800/70 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle size={16} className="shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* TAB 1: POLICIES REPOSITORY */}
      {activeTab === 'POLICIES' && (
        <>
          {/* Filter Toolbar */}
          <Card>
            <div className="p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
              <div className="relative w-full md:w-80">
                <Search className="absolute left-3 top-2.5 text-slate-500" size={14} />
                <input
                  type="text"
                  placeholder="Search policies by title or description..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="PUBLISHED">Published</option>
                  <option value="APPROVED">Approved</option>
                  <option value="UNDER_REVIEW">Under Review</option>
                  <option value="DRAFT">Draft</option>
                  <option value="ARCHIVED">Archived</option>
                </select>

                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">All Types</option>
                  <option value="ACCESS_CONTROL">Access Control</option>
                  <option value="INFORMATION_SECURITY">Information Security</option>
                  <option value="DATA_PROTECTION">Data Protection</option>
                  <option value="INCIDENT_RESPONSE">Incident Response</option>
                  <option value="RISK_MANAGEMENT">Risk Management</option>
                  <option value="BUSINESS_CONTINUITY">Business Continuity</option>
                  <option value="VENDOR_MANAGEMENT">Vendor Management</option>
                  <option value="ACCEPTABLE_USE">Acceptable Use</option>
                </select>
              </div>
            </div>
          </Card>

          {/* Policies Table */}
          <Card>
            <CardHeader
              title={`Policy Repository (${filteredPolicies.length})`}
              subtitle="Click on any policy to view version history, SHA-256 hashes, review workflows, and mapped control outcomes."
            />

            {isLoading ? (
              <LoadingSpinner text="Loading policies..." />
            ) : filteredPolicies.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                No policies found in this repository.
              </div>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>Policy Title</TableHeaderCell>
                    <TableHeaderCell>Domain Type</TableHeaderCell>
                    <TableHeaderCell>Status</TableHeaderCell>
                    <TableHeaderCell>Active Version</TableHeaderCell>
                    <TableHeaderCell>Content Hash</TableHeaderCell>
                    <TableHeaderCell>Owner</TableHeaderCell>
                    <TableHeaderCell>Controls</TableHeaderCell>
                    <TableHeaderCell>Action</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredPolicies.map((pol) => (
                    <TableRow key={pol.id}>
                      <TableCell>
                        <Link
                          to={`/policies/${pol.id}`}
                          className="font-semibold text-slate-100 text-xs hover:text-indigo-400 transition-colors"
                        >
                          {pol.title}
                        </Link>
                        {pol.description && (
                          <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                            {pol.description}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="text-[11px] font-mono text-slate-300">
                          {pol.policy_type.replace('_', ' ')}
                        </span>
                      </TableCell>
                      <TableCell>{getStatusBadge(pol.status)}</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1 text-xs font-mono text-indigo-300">
                          <History size={12} />
                          v{pol.current_version?.version_number || pol.total_versions || 1}
                        </span>
                      </TableCell>
                      <TableCell>
                        {pol.current_version?.content_hash_sha256 ? (
                          <span
                            className="text-[10px] font-mono text-emerald-400 bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded"
                            title={pol.current_version.content_hash_sha256}
                          >
                            {pol.current_version.content_hash_sha256.substring(0, 8)}...
                          </span>
                        ) : (
                          <span className="text-[11px] text-slate-500 italic">Uncommitted</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {pol.owner ? (
                          <span className="text-xs text-slate-300">{pol.owner.full_name}</span>
                        ) : (
                          <span className="text-xs text-slate-600 italic">Unassigned</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-mono text-emerald-400">
                          {pol.mapped_subcategories ? pol.mapped_subcategories.length : 0} controls
                        </span>
                      </TableCell>
                      <TableCell>
                        <Link to={`/policies/${pol.id}`}>
                          <Button size="xs" variant="secondary">
                            <span>Manage</span>
                            <ArrowRight size={12} />
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        </>
      )}

      {/* TAB 2: WORKFORCE ATTESTATION CAMPAIGNS */}
      {activeTab === 'CAMPAIGNS' && (
        <>
          {/* Campaign Stats Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <div className="p-4">
                <span className="text-[11px] text-slate-400 font-medium uppercase">Total Campaigns</span>
                <div className="text-xl font-bold font-mono text-slate-100 mt-1">{campaigns.length}</div>
              </div>
            </Card>
            <Card>
              <div className="p-4">
                <span className="text-[11px] text-slate-400 font-medium uppercase">Active Campaigns</span>
                <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                  {campaigns.filter((c) => c.status === 'ACTIVE').length}
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4">
                <span className="text-[11px] text-slate-400 font-medium uppercase">Total Targeted</span>
                <div className="text-xl font-bold font-mono text-slate-100 mt-1">
                  {campaigns.reduce((acc, c) => acc + (c.total_targeted_count || 0), 0)}
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4">
                <span className="text-[11px] text-slate-400 font-medium uppercase">Satisfied (Attested + Waived)</span>
                <div className="text-xl font-bold font-mono text-indigo-400 mt-1">
                  {campaigns.reduce((acc, c) => acc + (c.completed_count || 0), 0)}
                </div>
              </div>
            </Card>
          </div>

          {/* Campaign Filters */}
          <Card>
            <div className="p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
              <div className="relative w-full md:w-80">
                <Search className="absolute left-3 top-2.5 text-slate-500" size={14} />
                <input
                  type="text"
                  placeholder="Search campaigns by code or title..."
                  value={campaignSearch}
                  onChange={(e) => setCampaignSearch(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={campaignStatusFilter}
                  onChange={(e) => setCampaignStatusFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="ACTIVE">Active</option>
                  <option value="DRAFT">Draft</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="PAUSED">Paused</option>
                  <option value="CANCELLED">Cancelled</option>
                </select>
              </div>
            </div>
          </Card>

          {/* Campaigns Table */}
          <Card>
            <CardHeader
              title={`Workforce Campaigns (${filteredCampaigns.length})`}
              subtitle="Tamper-evident workforce distribution campaigns bound to immutable policy version SHA-256 hashes."
            />

            {filteredCampaigns.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                No attestation campaigns found. Click "Launch Campaign" to create one.
              </div>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>Campaign</TableHeaderCell>
                    <TableHeaderCell>Bound Policy Version</TableHeaderCell>
                    <TableHeaderCell>Target Scope</TableHeaderCell>
                    <TableHeaderCell>Status</TableHeaderCell>
                    <TableHeaderCell>Attestation Progress</TableHeaderCell>
                    <TableHeaderCell>Due Date</TableHeaderCell>
                    <TableHeaderCell>Actions</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredCampaigns.map((camp) => {
                    const compRate = camp.total_targeted_count > 0
                      ? Math.round((camp.completed_count / camp.total_targeted_count) * 100)
                      : 0;

                    return (
                      <TableRow key={camp.id}>
                        <TableCell>
                          <div className="font-mono text-indigo-300 text-xs font-bold">{camp.campaign_code}</div>
                          <div className="text-xs text-slate-200 font-medium">{camp.title}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-xs text-slate-300">{camp.policy_title || camp.policy?.title || `Policy #${camp.policy_id}`}</div>
                          <div className="inline-flex items-center gap-1 font-mono text-[10px] text-emerald-400 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                            <Lock size={9} />
                            v{camp.policy_version_number || camp.version?.version_number || camp.version_id} ({camp.policy_version_hash.substring(0, 8)}...)
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="text-xs font-mono text-slate-300">
                            {camp.target_type === 'ALL_USERS' ? 'All Organization Users' : `${camp.target_type} (${camp.target_role || 'Custom'})`}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1.5">
                            {getCampaignStatusBadge(camp.status)}
                            {(camp.overdue_count || 0) > 0 && (
                              <Badge variant="danger">{camp.overdue_count} Overdue</Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="w-36 space-y-1">
                            <div className="flex justify-between text-[11px] font-mono text-slate-400">
                              <span>{camp.completed_count} / {camp.total_targeted_count}</span>
                              <span className="text-slate-200 font-semibold">{compRate}%</span>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                              <div
                                className={`h-1.5 rounded-full transition-all duration-300 ${
                                  compRate >= 100 ? 'bg-emerald-500' : 'bg-indigo-500'
                                }`}
                                style={{ width: `${Math.min(compRate, 100)}%` }}
                              />
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="text-xs text-slate-300 font-mono">
                            {new Date(camp.due_date).toLocaleDateString()}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {camp.status === 'DRAFT' && hasPermission('policy:campaign_manage') && (
                              <Button
                                size="xs"
                                variant="success"
                                onClick={() => handleLaunchCampaign(camp.id)}
                                title="Launch Campaign & Activate Rosters"
                              >
                                <Play size={11} />
                                Launch
                              </Button>
                            )}

                            {camp.status !== 'DRAFT' && (
                              <Button
                                size="xs"
                                variant="outline"
                                onClick={() => handleOpenRoster(camp)}
                                title="Inspect Campaign Roster & Waivers"
                              >
                                <ListChecks size={11} />
                                Roster
                              </Button>
                            )}

                            {camp.status === 'ACTIVE' && hasPermission('policy:campaign_manage') && (
                              <Button
                                size="xs"
                                variant="outline"
                                onClick={() => handleEvaluateOverdue(camp.id)}
                                title="Evaluate Overdue Records & Escalate"
                              >
                                <Clock size={11} />
                                Sweep Overdue
                              </Button>
                            )}

                            {camp.status === 'ACTIVE' && hasPermission('policy:approve') && (
                              <Button
                                size="xs"
                                variant="warning"
                                onClick={() => handleCloseCampaign(camp.id)}
                                title="Formally Close Campaign"
                              >
                                <StopCircle size={11} />
                                Close
                              </Button>
                            )}

                            {(camp.status === 'DRAFT' || camp.status === 'ACTIVE') && hasPermission('policy:campaign_manage') && (
                              <Button
                                size="xs"
                                variant="danger"
                                onClick={() => handleCancelCampaign(camp.id)}
                                title="Cancel Campaign"
                              >
                                <XCircle size={11} />
                                Cancel
                              </Button>
                            )}

                            {hasPermission('policy:campaign_manage') && (
                              <Button
                                size="xs"
                                variant="secondary"
                                onClick={() => handleGenerateEvidence(camp.id)}
                                title="Generate Audit Evidence Manifest (Phase 3)"
                              >
                                <FileBadge size={11} />
                                Evidence
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </Card>
        </>
      )}

      {/* Campaign Roster & Policy Waiver Exemption Modal */}
      <Modal
        isOpen={!!selectedRosterCampaign}
        onClose={() => {
          setSelectedRosterCampaign(null);
          setExemptRecordTarget(null);
        }}
        title={`Campaign Roster: ${selectedRosterCampaign?.campaign_code || ''}`}
      >
        {isRosterLoading ? (
          <LoadingSpinner text="Loading campaign attestation roster..." />
        ) : (
          <div className="space-y-4">
            <div className="max-h-72 overflow-y-auto border border-slate-800 rounded">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>User ID</TableHeaderCell>
                    <TableHeaderCell>Status</TableHeaderCell>
                    <TableHeaderCell>Receipt / Waiver</TableHeaderCell>
                    <TableHeaderCell>Action</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {campaignRecords.map((rec) => {
                    const matchedUser = users.find((u) => u.id === rec.user_id);
                    return (
                      <TableRow key={rec.id}>
                        <TableCell>
                          <div className="text-xs text-slate-200 font-medium">
                            {matchedUser ? matchedUser.full_name : `User #${rec.user_id}`}
                          </div>
                          {matchedUser && (
                            <div className="text-[10px] font-mono text-slate-400">{matchedUser.email}</div>
                          )}
                        </TableCell>
                        <TableCell>
                          {rec.status === 'ATTESTED' && <Badge variant="success">ATTESTED</Badge>}
                          {rec.status === 'EXEMPTED' && <Badge variant="purple">EXEMPTED</Badge>}
                          {rec.status === 'OVERDUE' && <Badge variant="danger">OVERDUE</Badge>}
                          {rec.status === 'PENDING' && <Badge variant="info">PENDING</Badge>}
                        </TableCell>
                        <TableCell>
                          {rec.attestation_receipt_hash ? (
                            <span className="text-[10px] font-mono text-emerald-400">
                              {rec.attestation_receipt_hash.substring(0, 12)}...
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-500 italic">Awaiting</span>
                          )}
                          {rec.exemption_exception_id && (
                            <div className="text-[10px] text-purple-300 font-mono">
                              Waiver Exc #{rec.exemption_exception_id}
                            </div>
                          )}
                        </TableCell>
                        <TableCell>
                          {(rec.status === 'PENDING' || rec.status === 'OVERDUE') &&
                            selectedRosterCampaign?.status === 'ACTIVE' &&
                            hasPermission('policy:approve') && (
                              <Button
                                size="xs"
                                variant="outline"
                                onClick={() => setExemptRecordTarget(rec)}
                              >
                                <ShieldAlert size={11} />
                                Exempt
                              </Button>
                            )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            {exemptRecordTarget && (
              <form onSubmit={handleSubmitExemption} className="p-3 bg-slate-950 border border-indigo-800/70 rounded space-y-3">
                <div className="text-xs font-semibold text-indigo-300">
                  Grant Policy Waiver Exemption for User #{exemptRecordTarget.user_id}
                </div>
                <div>
                  <label className="block text-[11px] text-slate-300 mb-1">
                    Approved Phase 5 POLICY_EXCEPTION SecurityException
                  </label>
                  <select
                    required
                    value={exemptExceptionId}
                    onChange={(e) => setExemptExceptionId(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200"
                  >
                    <option value="">-- Select Approved Policy Exception --</option>
                    {exceptions.map((exc) => (
                      <option key={exc.id} value={exc.id}>
                        #{exc.id} — {exc.title} ({exc.exception_type} / {exc.effective_status || exc.status})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] text-slate-300 mb-1">
                    Formal Exemption Justification (min 10 chars)
                  </label>
                  <textarea
                    required
                    minLength={10}
                    rows={2}
                    value={exemptReason}
                    onChange={(e) => setExemptReason(e.target.value)}
                    placeholder="Document the approved waiver rationale..."
                    className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    size="xs"
                    variant="outline"
                    onClick={() => setExemptRecordTarget(null)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    size="xs"
                    variant="primary"
                    isLoading={isSubmittingExemption}
                  >
                    Confirm Exemption
                  </Button>
                </div>
              </form>
            )}
          </div>
        )}
      </Modal>

      {/* Create Policy Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Author New Security Policy"
      >
        {formError && (
          <div className="mb-4 p-3 rounded bg-rose-950/60 border border-rose-800/70 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle size={14} className="shrink-0" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleCreatePolicy} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Policy Title</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Cryptography & Key Management Policy"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Policy Domain</label>
              <select
                value={policyType}
                onChange={(e) => setPolicyType(e.target.value as PolicyType)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="ACCESS_CONTROL">Access Control</option>
                <option value="INFORMATION_SECURITY">Information Security</option>
                <option value="DATA_PROTECTION">Data Protection</option>
                <option value="INCIDENT_RESPONSE">Incident Response</option>
                <option value="RISK_MANAGEMENT">Risk Management</option>
                <option value="BUSINESS_CONTINUITY">Business Continuity</option>
                <option value="VENDOR_MANAGEMENT">Vendor Management</option>
                <option value="ACCEPTABLE_USE">Acceptable Use</option>
                <option value="CRYPTOGRAPHY">Cryptography</option>
                <option value="CHANGE_MANAGEMENT">Change Management</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Policy Owner</label>
              <select
                value={ownerId}
                onChange={(e) => setOwnerId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="">Current User</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.role})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Brief Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="High-level purpose and organizational scope..."
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Initial Draft Content (Markdown supported)
            </label>
            <textarea
              required
              rows={6}
              value={initialContent}
              onChange={(e) => setInitialContent(e.target.value)}
              placeholder="# Policy Title&#10;&#10;## 1. Purpose&#10;Mandatory standards for..."
              className="w-full font-mono bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isCreating}
            >
              Create Draft Policy
            </Button>
          </div>
        </form>
      </Modal>

      {/* Launch Campaign Modal */}
      <Modal
        isOpen={isCampaignModalOpen}
        onClose={() => setIsCampaignModalOpen(false)}
        title="Create Workforce Attestation Campaign"
      >
        {campaignFormError && (
          <div className="mb-4 p-3 rounded bg-rose-950/60 border border-rose-800/70 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle size={14} className="shrink-0" />
            <span>{campaignFormError}</span>
          </div>
        )}

        <form onSubmit={handleCreateCampaign} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Campaign Code</label>
              <input
                type="text"
                required
                value={campCode}
                onChange={(e) => setCampCode(e.target.value)}
                placeholder="e.g. CAMP-ANNUAL-2026"
                className="w-full font-mono bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Campaign Title</label>
              <input
                type="text"
                required
                value={campTitle}
                onChange={(e) => setCampTitle(e.target.value)}
                placeholder="e.g. 2026 Annual Security Attestation"
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Target Policy</label>
            <select
              required
              value={campPolicyId}
              onChange={(e) => {
                setCampPolicyId(e.target.value);
                setCampVersionId('');
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">-- Choose Policy --</option>
              {policies.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title} ({p.status})
                </option>
              ))}
            </select>
          </div>

          {selectedPolicyObj && selectedPolicyObj.versions && selectedPolicyObj.versions.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Select Version to Bind Cryptographically
              </label>
              <select
                required
                value={campVersionId}
                onChange={(e) => setCampVersionId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              >
                <option value="">-- Choose Version --</option>
                {selectedPolicyObj.versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version_number} ({v.status}) — SHA256:{v.content_hash_sha256?.substring(0, 10)}...
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Target Scope</label>
              <select
                value={campTargetType}
                onChange={(e) => setCampTargetType(e.target.value as CampaignTargetType)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL_USERS">All Active Users</option>
                <option value="ROLE_BASED">Role-Based Cohort</option>
                <option value="CUSTOM_GROUP">Custom Group</option>
              </select>
            </div>

            {campTargetType === 'ROLE_BASED' && (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Target Role</label>
                <select
                  required
                  value={campTargetRole}
                  onChange={(e) => setCampTargetRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">-- Select Target Role --</option>
                  <option value="ADMIN">ADMIN</option>
                  <option value="MANAGER">MANAGER</option>
                  <option value="GRC_ANALYST">GRC_ANALYST</option>
                  <option value="SECURITY_ANALYST">SECURITY_ANALYST</option>
                  <option value="AUDITOR">AUDITOR</option>
                  <option value="VIEWER">VIEWER</option>
                </select>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Due Date</label>
              <input
                type="date"
                required
                value={campDueDate}
                onChange={(e) => setCampDueDate(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Grace Period (Days)</label>
              <input
                type="number"
                min="0"
                value={campGracePeriod}
                onChange={(e) => setCampGracePeriod(parseInt(e.target.value, 10) || 0)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Description / Campaign Purpose</label>
            <textarea
              rows={3}
              value={campDescription}
              onChange={(e) => setCampDescription(e.target.value)}
              placeholder="State the regulatory driver or annual compliance requirement..."
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsCampaignModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isCreatingCampaign}
            >
              Create Campaign
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};