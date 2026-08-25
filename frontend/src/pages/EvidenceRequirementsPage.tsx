import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { evidenceService } from '../lib/evidenceService';
import { useAuth } from '../context/AuthContext';
import type { EvidenceRequirement, EvidenceType, OrganizationControl } from '../types';
import {
  ListFilter,
  Plus,
  Search,
  Filter,
  AlertCircle,
  FileText,
  Trash2,
  Edit2,
  X,
} from 'lucide-react';

export const EvidenceRequirementsPage: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [controlFilter, setControlFilter] = useState<string>('ALL');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingReq, setEditingReq] = useState<EvidenceRequirement | null>(null);

  // Form fields
  const [formControlId, setFormControlId] = useState<number | ''>('');
  const [formTitle, setFormTitle] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formType, setFormType] = useState<EvidenceType>('DOCUMENT');
  const [formIsRequired, setFormIsRequired] = useState(true);
  const [formGuidance, setFormGuidance] = useState('');
  const [formError, setFormError] = useState('');

  // Queries
  const { data: requirements = [], isLoading } = useQuery({
    queryKey: ['evidence-requirements', typeFilter, controlFilter, search],
    queryFn: () =>
      evidenceService.getRequirements({
        evidence_type: typeFilter === 'ALL' ? undefined : (typeFilter as EvidenceType),
        organization_control_id: controlFilter === 'ALL' ? undefined : Number(controlFilter),
        search: search || undefined,
      }),
  });

  const { data: controls = [] } = useQuery<OrganizationControl[]>({
    queryKey: ['controls-list-for-requirements'],
    queryFn: async () => {
      const res = await api.get<OrganizationControl[]>('/api/v1/controls');
      return res.data;
    },
  });


  // Mutations
  const createMutation = useMutation({
    mutationFn: evidenceService.createRequirement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidence-requirements'] });
      setIsModalOpen(false);
      resetForm();
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || 'Failed to create requirement.');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      evidenceService.updateRequirement(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidence-requirements'] });
      setIsModalOpen(false);
      resetForm();
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || 'Failed to update requirement.');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: evidenceService.deleteRequirement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidence-requirements'] });
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || 'Failed to delete requirement.');
    },
  });

  const resetForm = () => {
    setEditingReq(null);
    setFormControlId('');
    setFormTitle('');
    setFormDescription('');
    setFormType('DOCUMENT');
    setFormIsRequired(true);
    setFormGuidance('');
    setFormError('');
  };

  const openCreateModal = () => {
    resetForm();
    setIsModalOpen(true);
  };

  const openEditModal = (req: EvidenceRequirement) => {
    setEditingReq(req);
    setFormControlId(req.organization_control_id);
    setFormTitle(req.title);
    setFormDescription(req.description || '');
    setFormType(req.evidence_type);
    setFormIsRequired(req.is_required);
    setFormGuidance(req.guidance || '');
    setFormError('');
    setIsModalOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim()) {
      setFormError('Title is required.');
      return;
    }

    if (editingReq) {
      updateMutation.mutate({
        id: editingReq.id,
        data: {
          title: formTitle.trim(),
          description: formDescription.trim() || undefined,
          evidence_type: formType,
          is_required: formIsRequired,
          guidance: formGuidance.trim() || undefined,
        },
      });
    } else {
      if (!formControlId) {
        setFormError('Control selection is required.');
        return;
      }
      createMutation.mutate({
        organization_control_id: Number(formControlId),
        title: formTitle.trim(),
        description: formDescription.trim() || undefined,
        evidence_type: formType,
        is_required: formIsRequired,
        guidance: formGuidance.trim() || undefined,
      });
    }
  };

  const canManage = ['ADMIN', 'GRC_ANALYST'].includes(user?.role || '');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/60 p-6 rounded-2xl border border-slate-800 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
            <ListFilter className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Evidence Requirements
            </h1>
            <p className="text-sm text-slate-400">
              Define and enforce what specific artifacts and documentation each control requires.
            </p>
          </div>
        </div>

        {canManage && (
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl shadow-lg shadow-blue-500/20 transition-all duration-200"
          >
            <Plus className="w-4 h-4" />
            New Requirement
          </button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-slate-900/40 p-4 rounded-xl border border-slate-800">
        <div className="flex flex-1 items-center gap-3 w-full md:w-auto">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search title, guidance, or description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 px-3 py-2 focus:outline-none focus:border-blue-500"
            >
              <option value="ALL">All Types</option>
              <option value="DOCUMENT">Document</option>
              <option value="CONFIGURATION">Configuration</option>
              <option value="LOG_EXPORT">Log Export</option>
              <option value="SCREENSHOT">Screenshot</option>
              <option value="POLICY_DOCUMENT">Policy Document</option>
              <option value="AUDIT_REPORT">Audit Report</option>
              <option value="OTHER">Other</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={controlFilter}
            onChange={(e) => setControlFilter(e.target.value)}
            className="w-full md:w-64 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 px-3 py-2 focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Controls</option>
            {controls.map((c: OrganizationControl) => (
              <option key={c.id} value={c.id}>
                {c.subcategory?.identifier} — {c.subcategory?.title?.slice(0, 30)}...
              </option>
            ))}
          </select>

        </div>
      </div>

      {/* Requirements Table */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 overflow-hidden backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/80 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4 font-semibold">Requirement Title</th>
                <th className="py-3.5 px-4 font-semibold">Type</th>
                <th className="py-3.5 px-4 font-semibold">Obligation</th>
                <th className="py-3.5 px-4 font-semibold">Artifacts Status</th>
                <th className="py-3.5 px-4 font-semibold">Created By</th>
                {canManage && <th className="py-3.5 px-4 font-semibold text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    Loading evidence requirements...
                  </td>
                </tr>
              ) : requirements.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-30 text-slate-400" />
                    No evidence requirements found. Click "New Requirement" to define one.
                  </td>
                </tr>
              ) : (
                requirements.map((req) => (
                  <tr key={req.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4">
                      <div>
                        <p className="font-semibold text-white">{req.title}</p>
                        {req.description && (
                          <p className="text-xs text-slate-400 line-clamp-1">{req.description}</p>
                        )}
                        {req.guidance && (
                          <p className="text-[11px] text-indigo-400/90 mt-0.5">
                            💡 Guidance: {req.guidance}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                        {req.evidence_type}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {req.is_required ? (
                        <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                          Mandatory
                        </span>
                      ) : (
                        <span className="text-xs text-slate-500">Optional</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2 text-xs">
                        <span
                          className={`font-semibold ${
                            req.accepted_items_count > 0 ? 'text-emerald-400' : 'text-slate-400'
                          }`}
                        >
                          {req.accepted_items_count} Accepted
                        </span>
                        <span className="text-slate-600">/</span>
                        <span className="text-slate-400">{req.items_count} Submitted</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-400">
                      {req.created_by?.full_name || 'System'}
                    </td>
                    {canManage && (
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => openEditModal(req)}
                            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                            title="Edit Requirement"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => {
                              if (
                                window.confirm(
                                  `Delete evidence requirement "${req.title}"?`
                                )
                              ) {
                                deleteMutation.mutate(req.id);
                              }
                            }}
                            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                            title="Delete Requirement"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex justify-between items-center pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white">
                {editingReq ? 'Edit Evidence Requirement' : 'Define Evidence Requirement'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="flex items-center gap-2 p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-xs">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              {!editingReq && (
                <div>
                  <label className="block font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                    Target Control *
                  </label>
                  <select
                    value={formControlId}
                    onChange={(e) =>
                      setFormControlId(e.target.value ? Number(e.target.value) : '')
                    }
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="">Select an organization control...</option>
                    {controls.map((c: OrganizationControl) => (
                      <option key={c.id} value={c.id}>
                        {c.subcategory?.identifier} — {c.subcategory?.title}
                      </option>
                    ))}
                  </select>

                </div>
              )}

              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Requirement Title *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Identity Provider Conditional Access Policy Export"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                    Evidence Type
                  </label>
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value as EvidenceType)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="DOCUMENT">Document</option>
                    <option value="CONFIGURATION">Configuration</option>
                    <option value="LOG_EXPORT">Log Export</option>
                    <option value="SCREENSHOT">Screenshot</option>
                    <option value="POLICY_DOCUMENT">Policy Document</option>
                    <option value="AUDIT_REPORT">Audit Report</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div className="flex flex-col justify-center pt-5">
                  <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-300">
                    <input
                      type="checkbox"
                      checked={formIsRequired}
                      onChange={(e) => setFormIsRequired(e.target.checked)}
                      className="rounded border-slate-800 text-blue-600 focus:ring-blue-500"
                    />
                    Mandatory Requirement
                  </label>
                </div>
              </div>

              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Description
                </label>
                <textarea
                  rows={2}
                  placeholder="Explain the purpose of this evidence requirement..."
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Auditor Guidance
                </label>
                <textarea
                  rows={2}
                  placeholder="Instructions for submitters on what settings or data must be visible..."
                  value={formGuidance}
                  onChange={(e) => setFormGuidance(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white bg-slate-800/60 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="px-5 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 rounded-xl shadow-lg shadow-blue-500/20"
                >
                  {editingReq ? 'Save Changes' : 'Create Requirement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
