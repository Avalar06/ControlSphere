import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShieldAlert,
  ArrowLeft,
  AlertTriangle,
  Plus,
  Trash2,
  FileText,
  Activity,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../lib/api';
import { riskService } from '../lib/riskService';
import { findingService } from '../lib/findingService';
import type { Finding, OrganizationControl, RiskStatus } from '../types';

export const RiskDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const riskId = parseInt(id || '0', 10);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isAcceptModalOpen, setIsAcceptModalOpen] = useState(false);
  const [acceptJustification, setAcceptJustification] = useState('');
  const [acceptExpiry, setAcceptExpiry] = useState('');

  const [isLinkControlOpen, setIsLinkControlOpen] = useState(false);
  const [selectedControlId, setSelectedControlId] = useState<number | ''>('');

  const [isLinkFindingOpen, setIsLinkFindingOpen] = useState(false);
  const [selectedFindingId, setSelectedFindingId] = useState<number | ''>('');

  const [residualImpact, setResidualImpact] = useState<number>(2);
  const [residualLikelihood, setResidualLikelihood] = useState<number>(2);

  const { data: risk, isLoading } = useQuery({
    queryKey: ['risk', riskId],
    queryFn: () => riskService.getRisk(riskId),
    enabled: !!riskId,
  });

  const { data: controls = [] } = useQuery({
    queryKey: ['controls'],
    queryFn: async () => {
      const res = await api.get<OrganizationControl[]>('/api/v1/controls');
      return res.data;
    },
  });

  const { data: findings = [] } = useQuery({
    queryKey: ['findings'],
    queryFn: () => findingService.getFindings(),
  });

  const statusMutation = useMutation({
    mutationFn: ({ status, notes }: { status: RiskStatus; notes?: string }) =>
      riskService.updateStatus(riskId, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', riskId] });
      queryClient.invalidateQueries({ queryKey: ['risks'] });
      queryClient.invalidateQueries({ queryKey: ['riskStats'] });
    },
  });

  const acceptMutation = useMutation({
    mutationFn: () =>
      riskService.acceptRisk(riskId, {
        justification: acceptJustification,
        expiry_date: acceptExpiry || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', riskId] });
      queryClient.invalidateQueries({ queryKey: ['risks'] });
      queryClient.invalidateQueries({ queryKey: ['riskStats'] });
      setIsAcceptModalOpen(false);
    },
  });

  const residualMutation = useMutation({
    mutationFn: () =>
      riskService.updateRisk(riskId, {
        residual_impact: residualImpact,
        residual_likelihood: residualLikelihood,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', riskId] });
      queryClient.invalidateQueries({ queryKey: ['risks'] });
      queryClient.invalidateQueries({ queryKey: ['riskStats'] });
    },
  });

  const linkControlMutation = useMutation({
    mutationFn: (controlId: number) => riskService.linkControl(riskId, controlId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', riskId] });
      setIsLinkControlOpen(false);
      setSelectedControlId('');
    },
  });

  const unlinkControlMutation = useMutation({
    mutationFn: (controlId: number) => riskService.unlinkControl(riskId, controlId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', riskId] });
    },
  });

  const linkFindingMutation = useMutation({
    mutationFn: (findingId: number) => riskService.linkFinding(riskId, findingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', riskId] });
      setIsLinkFindingOpen(false);
      setSelectedFindingId('');
    },
  });

  const unlinkFindingMutation = useMutation({
    mutationFn: (findingId: number) => riskService.unlinkFinding(riskId, findingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', riskId] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-500">
        Loading risk details...
      </div>
    );
  }

  if (!risk) {
    return (
      <div className="text-center py-16">
        <h2 className="text-xl font-bold text-slate-200">Risk Not Found</h2>
        <button
          onClick={() => navigate('/risks')}
          className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg"
        >
          Back to Risks
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/risks"
            className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-indigo-400">RSK-{risk.id}</span>
              <span className="text-slate-500">•</span>
              <span className="text-xs text-slate-400">{risk.risk_category}</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-100 mt-1">{risk.title}</h1>
          </div>
        </div>

        {/* Workflow Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {risk.status === 'IDENTIFIED' && (
            <button
              onClick={() => statusMutation.mutate({ status: 'ASSESSED' })}
              disabled={statusMutation.isPending}
              className="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
            >
              Mark Assessed
            </button>
          )}

          {risk.status === 'ASSESSED' && (
            <button
              onClick={() => statusMutation.mutate({ status: 'TREATMENT_PLANNED' })}
              disabled={statusMutation.isPending}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
            >
              Plan Treatment
            </button>
          )}

          {risk.status === 'TREATMENT_PLANNED' && (
            <button
              onClick={() => statusMutation.mutate({ status: 'MITIGATING' })}
              disabled={statusMutation.isPending}
              className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
            >
              Begin Mitigating
            </button>
          )}

          {risk.status === 'MITIGATING' && (
            <button
              onClick={() => statusMutation.mutate({ status: 'MONITORING' })}
              disabled={statusMutation.isPending}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
            >
              Move to Monitoring
            </button>
          )}

          {(risk.status === 'MONITORING' || risk.status === 'ACCEPTED') && (
            <button
              onClick={() => statusMutation.mutate({ status: 'CLOSED' })}
              disabled={statusMutation.isPending}
              className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium rounded-lg transition-colors cursor-pointer"
            >
              Close Risk
            </button>
          )}

          {risk.status !== 'CLOSED' && risk.status !== 'ACCEPTED' && (
            <button
              onClick={() => setIsAcceptModalOpen(true)}
              className="px-3 py-1.5 bg-purple-700 hover:bg-purple-600 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
            >
              Formal Risk Acceptance
            </button>
          )}
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Details & Matrices */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
            <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-400" />
              Risk Overview &amp; Impact Statement
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
              {risk.description}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800 text-xs">
              <div>
                <span className="text-slate-500 block">Status</span>
                <span className="font-semibold text-slate-200 mt-0.5 block">{risk.status}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Source</span>
                <span className="font-semibold text-slate-200 mt-0.5 block">{risk.risk_source}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Appetite Status</span>
                <span className="font-semibold text-indigo-400 mt-0.5 block">
                  {risk.appetite_status.replace('_', ' ')}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Target Band</span>
                <span className="font-semibold text-slate-200 mt-0.5 block">{risk.target_risk_band}</span>
              </div>
            </div>
          </div>

          {/* Inherent vs Residual Evaluation Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Inherent Risk */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-200">Inherent Risk (Unmitigated)</h3>
                <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-950/60 text-red-400 border border-red-800/80">
                  {risk.inherent_band}
                </span>
              </div>

              <div className="flex items-baseline gap-3">
                <div className="text-3xl font-extrabold text-slate-100">{risk.inherent_score}</div>
                <div className="text-xs text-slate-400">/ 25 maximum score</div>
              </div>

              <div className="text-xs text-slate-400 space-y-1 pt-2 border-t border-slate-800/60">
                <div className="flex justify-between">
                  <span>Impact:</span>
                  <span className="font-semibold text-slate-200">{risk.inherent_impact} / 5</span>
                </div>
                <div className="flex justify-between">
                  <span>Likelihood:</span>
                  <span className="font-semibold text-slate-200">{risk.inherent_likelihood} / 5</span>
                </div>
              </div>
            </div>

            {/* Residual Risk */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-200">Residual Risk (Mitigated)</h3>
                {risk.residual_band && (
                  <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/80">
                    {risk.residual_band}
                  </span>
                )}
              </div>

              <div className="flex items-baseline gap-3">
                <div className="text-3xl font-extrabold text-slate-100">
                  {risk.residual_score ?? '--'}
                </div>
                <div className="text-xs text-slate-400">/ 25 maximum score</div>
              </div>

              <div className="text-xs text-slate-400 space-y-1 pt-2 border-t border-slate-800/60">
                <div className="flex justify-between">
                  <span>Residual Impact:</span>
                  <span className="font-semibold text-slate-200">
                    {risk.residual_impact ? `${risk.residual_impact} / 5` : 'Not Set'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Residual Likelihood:</span>
                  <span className="font-semibold text-slate-200">
                    {risk.residual_likelihood ? `${risk.residual_likelihood} / 5` : 'Not Set'}
                  </span>
                </div>
              </div>

              {/* Quick Residual Assessment Input */}
              {risk.status !== 'CLOSED' && (
                <div className="pt-2 border-t border-slate-800 flex items-center gap-2">
                  <select
                    value={residualImpact}
                    onChange={(e) => setResidualImpact(parseInt(e.target.value, 10))}
                    className="bg-slate-950 border border-slate-800 rounded text-xs p-1 text-slate-200"
                  >
                    <option value={1}>Imp 1</option>
                    <option value={2}>Imp 2</option>
                    <option value={3}>Imp 3</option>
                    <option value={4}>Imp 4</option>
                    <option value={5}>Imp 5</option>
                  </select>
                  <select
                    value={residualLikelihood}
                    onChange={(e) => setResidualLikelihood(parseInt(e.target.value, 10))}
                    className="bg-slate-950 border border-slate-800 rounded text-xs p-1 text-slate-200"
                  >
                    <option value={1}>Lik 1</option>
                    <option value={2}>Lik 2</option>
                    <option value={3}>Lik 3</option>
                    <option value={4}>Lik 4</option>
                    <option value={5}>Lik 5</option>
                  </select>
                  <button
                    onClick={() => residualMutation.mutate()}
                    disabled={residualMutation.isPending}
                    className="px-2 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs transition-colors cursor-pointer"
                  >
                    Update
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Linked Controls & Traceability */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Mitigating Controls ({risk.control_links?.length ?? 0})
              </h2>
              {risk.status !== 'CLOSED' && (
                <button
                  onClick={() => setIsLinkControlOpen(true)}
                  className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Link Control
                </button>
              )}
            </div>

            {(!risk.control_links || risk.control_links.length === 0) ? (
              <p className="text-xs text-slate-500 italic py-2">
                No organization controls linked to this risk yet.
              </p>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {risk.control_links.map((link) => (
                  <div key={link.id} className="py-2.5 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-mono text-indigo-400 font-medium mr-2">
                        {link.organization_control?.subcategory?.identifier}
                      </span>
                      <span className="text-slate-200">
                        {link.organization_control?.subcategory?.title}
                      </span>
                    </div>
                    {risk.status !== 'CLOSED' && (
                      <button
                        onClick={() => unlinkControlMutation.mutate(link.organization_control_id)}
                        className="text-slate-500 hover:text-red-400 transition-colors p-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Linked Findings */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Associated Findings ({risk.finding_links?.length ?? 0})
              </h2>
              {risk.status !== 'CLOSED' && (
                <button
                  onClick={() => setIsLinkFindingOpen(true)}
                  className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Link Finding
                </button>
              )}
            </div>

            {(!risk.finding_links || risk.finding_links.length === 0) ? (
              <p className="text-xs text-slate-500 italic py-2">
                No deficiency findings linked to this risk.
              </p>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {risk.finding_links.map((link) => (
                  <div key={link.id} className="py-2.5 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-mono text-amber-400 font-medium mr-2">
                        FND-{link.finding?.id}
                      </span>
                      <span className="text-slate-200">{link.finding?.title}</span>
                      <span className="ml-2 text-[11px] text-slate-500">
                        ({link.finding?.severity})
                      </span>
                    </div>
                    {risk.status !== 'CLOSED' && (
                      <button
                        onClick={() => unlinkFindingMutation.mutate(link.finding_id)}
                        className="text-slate-500 hover:text-red-400 transition-colors p-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Treatment Plan & Acceptance Metadata */}
        <div className="space-y-6">
          {/* Treatment Strategy Box */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-400" />
              Treatment Strategy
            </h2>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80 space-y-2">
              <div className="text-xs text-slate-400 flex justify-between">
                <span>Strategy:</span>
                <span className="font-semibold text-slate-200">{risk.treatment_strategy}</span>
              </div>
              {risk.treatment_due_date && (
                <div className="text-xs text-slate-400 flex justify-between">
                  <span>Target Due Date:</span>
                  <span
                    className={`font-semibold ${
                      risk.treatment_overdue_status === 'OVERDUE'
                        ? 'text-red-400'
                        : 'text-slate-200'
                    }`}
                  >
                    {risk.treatment_due_date}
                  </span>
                </div>
              )}
            </div>

            {risk.treatment_plan ? (
              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-medium">Treatment Plan:</span>
                <p className="text-xs text-slate-300 whitespace-pre-wrap p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                  {risk.treatment_plan}
                </p>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No formal treatment plan entered yet.</p>
            )}
          </div>

          {/* Formal Acceptance Card (If Accepted) */}
          {risk.status === 'ACCEPTED' && (
            <div className="bg-purple-950/30 border border-purple-800/60 rounded-xl p-5 space-y-3">
              <div className="flex items-center gap-2 text-purple-400 font-semibold text-sm">
                <ShieldAlert className="w-4 h-4" />
                Formal Risk Acceptance
              </div>
              <p className="text-xs text-purple-200 whitespace-pre-wrap">
                {risk.risk_acceptance_justification}
              </p>
              <div className="text-[11px] text-purple-300/80 pt-2 border-t border-purple-800/40 space-y-1">
                <div>Accepted By: {risk.risk_accepted_by?.full_name || 'Authorized Actor'}</div>
                <div>Accepted On: {risk.risk_accepted_at ? new Date(risk.risk_accepted_at).toLocaleDateString() : '--'}</div>
                {risk.risk_acceptance_expiry && (
                  <div>Acceptance Expiry: {risk.risk_acceptance_expiry}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Formal Risk Acceptance Modal */}
      {isAcceptModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-purple-400 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5" />
              Formal Risk Acceptance Workflow
            </h2>
            <p className="text-xs text-slate-400">
              Risk acceptance requires formal business justification, review date, and creates an authoritative audit log.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                acceptMutation.mutate();
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Business / Technical Justification *
                </label>
                <textarea
                  required
                  rows={4}
                  value={acceptJustification}
                  onChange={(e) => setAcceptJustification(e.target.value)}
                  placeholder="Document business rationale, compensating controls, or scheduled deprecation dates..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Acceptance Expiration Date (Optional)
                </label>
                <input
                  type="date"
                  value={acceptExpiry}
                  onChange={(e) => setAcceptExpiry(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsAcceptModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={acceptMutation.isPending || acceptJustification.length < 5}
                  className="px-4 py-2 bg-purple-700 hover:bg-purple-600 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                >
                  {acceptMutation.isPending ? 'Accepting...' : 'Confirm Acceptance'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Link Control Modal */}
      {isLinkControlOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              Link Mitigating Control
            </h2>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (selectedControlId) {
                  linkControlMutation.mutate(selectedControlId);
                }
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Select Organization Control
                </label>
                <select
                  required
                  value={selectedControlId}
                  onChange={(e) => setSelectedControlId(parseInt(e.target.value, 10))}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Choose a control...</option>
                  {controls.map((ctrl: OrganizationControl) => (
                    <option key={ctrl.id} value={ctrl.id}>
                      {ctrl.subcategory?.identifier} - {ctrl.subcategory?.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsLinkControlOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!selectedControlId || linkControlMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                >
                  {linkControlMutation.isPending ? 'Linking...' : 'Link Control'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Link Finding Modal */}
      {isLinkFindingOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              Link Deficiency Finding
            </h2>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (selectedFindingId) {
                  linkFindingMutation.mutate(selectedFindingId);
                }
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Select Finding
                </label>
                <select
                  required
                  value={selectedFindingId}
                  onChange={(e) => setSelectedFindingId(parseInt(e.target.value, 10))}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Choose a finding...</option>
                  {findings.map((fnd: Finding) => (
                    <option key={fnd.id} value={fnd.id}>
                      FND-{fnd.id}: {fnd.title} ({fnd.severity})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsLinkFindingOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!selectedFindingId || linkFindingMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                >
                  {linkFindingMutation.isPending ? 'Linking...' : 'Link Finding'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
