import React, { useEffect, useState } from 'react';
import {
  Shield,
  Search,
  RefreshCw,
  AlertCircle,
  FileCheck2,
  BookOpen,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import type { ImplementationStatus, OrganizationControl, Priority, User } from '../types';
import { Card, CardHeader } from '../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

export const ControlsPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const [controls, setControls] = useState<OrganizationControl[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFunction, setSelectedFunction] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedPriority, setSelectedPriority] = useState<string>('ALL');

  // Selected Control for Inspection/Edit
  const [selectedControl, setSelectedControl] = useState<OrganizationControl | null>(null);
  const [editStatus, setEditStatus] = useState<ImplementationStatus>('NOT_STARTED');
  const [editPriority, setEditPriority] = useState<Priority>('MEDIUM');
  const [editOwnerId, setEditOwnerId] = useState<string>('');
  const [editTargetDate, setEditTargetDate] = useState('');
  const [editReviewDate, setEditReviewDate] = useState('');
  const [editStatement, setEditStatement] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fetchControls = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await api.get<OrganizationControl[]>('/api/v1/controls');
      setControls(data);

      const { data: userList } = await api.get<User[]>('/api/v1/users');
      setUsers(userList);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load organization controls.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchControls();
  }, []);

  const openControlDetail = (ctrl: OrganizationControl) => {
    setSelectedControl(ctrl);
    setEditStatus(ctrl.status);
    setEditPriority(ctrl.priority);
    setEditOwnerId(ctrl.owner_id ? String(ctrl.owner_id) : '');
    setEditTargetDate(ctrl.target_date || '');
    setEditReviewDate(ctrl.review_date || '');
    setEditStatement(ctrl.implementation_statement || '');
    setEditNotes(ctrl.notes || '');
    setSaveSuccess(false);
  };

  const handleSaveControl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedControl) return;

    setIsSaving(true);
    try {
      const payload: any = {
        status: editStatus,
        priority: editPriority,
        owner_id: editOwnerId ? parseInt(editOwnerId, 10) : null,
        target_date: editTargetDate || null,
        review_date: editReviewDate || null,
        implementation_statement: editStatement || null,
        notes: editNotes || null,
      };

      const { data: updated } = await api.patch<OrganizationControl>(
        `/api/v1/controls/${selectedControl.id}`,
        payload
      );

      // Update local state
      setControls((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setSelectedControl(updated);
      setSaveSuccess(true);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to update control.');
    } finally {
      setIsSaving(false);
    }
  };

  const getStatusBadge = (status: ImplementationStatus) => {
    switch (status) {
      case 'IMPLEMENTED':
        return <Badge variant="success">IMPLEMENTED</Badge>;
      case 'PARTIALLY_IMPLEMENTED':
        return <Badge variant="warning">PARTIAL</Badge>;
      case 'IN_PROGRESS':
        return <Badge variant="info">IN PROGRESS</Badge>;
      case 'NEEDS_REVIEW':
        return <Badge variant="purple">NEEDS REVIEW</Badge>;
      case 'NOT_APPLICABLE':
        return <Badge variant="default">N/A</Badge>;
      case 'NOT_STARTED':
      default:
        return <Badge variant="danger">NOT STARTED</Badge>;
    }
  };

  const getPriorityBadge = (priority: Priority) => {
    switch (priority) {
      case 'CRITICAL':
        return <Badge variant="danger">CRITICAL</Badge>;
      case 'HIGH':
        return <Badge variant="warning">HIGH</Badge>;
      case 'MEDIUM':
        return <Badge variant="info">MED</Badge>;
      case 'LOW':
      default:
        return <Badge variant="default">LOW</Badge>;
    }
  };

  // Filter controls in frontend
  const filteredControls = controls.filter((ctrl) => {
    if (selectedFunction !== 'ALL' && ctrl.function_identifier !== selectedFunction) {
      return false;
    }
    if (selectedStatus !== 'ALL' && ctrl.status !== selectedStatus) {
      return false;
    }
    if (selectedPriority !== 'ALL' && ctrl.priority !== selectedPriority) {
      return false;
    }
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      const subcat = ctrl.subcategory;
      const matchId = subcat?.identifier.toLowerCase().includes(term);
      const matchTitle = subcat?.title.toLowerCase().includes(term);
      const matchDesc = subcat?.description.toLowerCase().includes(term);
      const matchCat = ctrl.category_name?.toLowerCase().includes(term);
      if (!matchId && !matchTitle && !matchDesc && !matchCat) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="text-indigo-400" size={20} />
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">Security Controls Matrix</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            NIST CSF 2.0 Subcategories and organization-scoped implementation assessments.
          </p>
        </div>

        <Button size="sm" variant="secondary" onClick={fetchControls} isLoading={isLoading}>
          <RefreshCw size={13} />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800/70 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle size={16} className="shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter Toolbar */}
      <Card>
        <div className="p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
          <div className="relative w-full md:w-80">
            <Search className="absolute left-3 top-2.5 text-slate-500" size={14} />
            <input
              type="text"
              placeholder="Search by ID (e.g. PR.AA-01) or keyword..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            {/* Function Filter */}
            <select
              value={selectedFunction}
              onChange={(e) => setSelectedFunction(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Functions</option>
              <option value="GV">Govern (GV)</option>
              <option value="ID">Identify (ID)</option>
              <option value="PR">Protect (PR)</option>
              <option value="DE">Detect (DE)</option>
              <option value="RS">Respond (RS)</option>
              <option value="RC">Recover (RC)</option>
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="IMPLEMENTED">Implemented</option>
              <option value="PARTIALLY_IMPLEMENTED">Partially Implemented</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="NOT_STARTED">Not Started</option>
              <option value="NEEDS_REVIEW">Needs Review</option>
              <option value="NOT_APPLICABLE">Not Applicable</option>
            </select>

            {/* Priority Filter */}
            <select
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Priorities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Controls Table */}
      <Card>
        <CardHeader
          title={`Controls Inventory (${filteredControls.length} outcomes)`}
          subtitle="Click on any control row to inspect details or assess implementation status."
        />

        {isLoading ? (
          <LoadingSpinner text="Loading controls..." />
        ) : filteredControls.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">
            No controls match the selected filters.
          </div>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Control Identifier</TableHeaderCell>
                <TableHeaderCell>Function / Category</TableHeaderCell>
                <TableHeaderCell>Implementation Status</TableHeaderCell>
                <TableHeaderCell>Priority</TableHeaderCell>
                <TableHeaderCell>Assigned Owner</TableHeaderCell>
                <TableHeaderCell>Policies</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredControls.map((ctrl) => (
                <TableRow
                  key={ctrl.id}
                  onClick={() => openControlDetail(ctrl)}
                  className="cursor-pointer hover:bg-slate-900/60 transition-colors"
                >
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-300">
                        {ctrl.subcategory?.identifier}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-300 font-medium line-clamp-1 mt-0.5">
                      {ctrl.subcategory?.title}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-xs text-slate-200 font-medium">
                      {ctrl.function_name}
                    </div>
                    <div className="text-[11px] text-slate-400">
                      {ctrl.category_identifier} · {ctrl.category_name}
                    </div>
                  </TableCell>
                  <TableCell>{getStatusBadge(ctrl.status)}</TableCell>
                  <TableCell>{getPriorityBadge(ctrl.priority)}</TableCell>
                  <TableCell>
                    {ctrl.owner ? (
                      <span className="text-xs text-slate-300">{ctrl.owner.full_name}</span>
                    ) : (
                      <span className="text-xs text-slate-600 italic">Unassigned</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {ctrl.mapped_policies_count && ctrl.mapped_policies_count > 0 ? (
                      <span className="inline-flex items-center gap-1 text-xs text-emerald-400 font-mono">
                        <BookOpen size={12} />
                        <span>{ctrl.mapped_policies_count}</span>
                      </span>
                    ) : (
                      <span className="text-xs text-slate-600 font-mono">0</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Control Assessment & Detail Modal */}
      {selectedControl && (
        <Modal
          isOpen={!!selectedControl}
          onClose={() => setSelectedControl(null)}
          title={`Control Assessment — ${selectedControl.subcategory?.identifier}`}
        >
          <div className="space-y-5">
            {/* Outcome Overview */}
            <div className="p-3.5 rounded bg-slate-950 border border-slate-800/90 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200">
                  {selectedControl.subcategory?.title}
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 text-indigo-300 border border-indigo-900/50">
                  {selectedControl.function_name} ({selectedControl.category_identifier})
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                {selectedControl.subcategory?.description}
              </p>
            </div>

            {saveSuccess && (
              <div className="p-3 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
                <FileCheck2 size={15} />
                <span>Control assessment updated successfully. Audit log created.</span>
              </div>
            )}

            <form onSubmit={handleSaveControl} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Status */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Implementation Status
                  </label>
                  <select
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value as ImplementationStatus)}
                    disabled={!hasPermission('control:assess')}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-60"
                  >
                    <option value="NOT_STARTED">NOT_STARTED</option>
                    <option value="IN_PROGRESS">IN_PROGRESS</option>
                    <option value="PARTIALLY_IMPLEMENTED">PARTIALLY_IMPLEMENTED</option>
                    <option value="IMPLEMENTED">IMPLEMENTED</option>
                    <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
                    <option value="NOT_APPLICABLE">NOT_APPLICABLE</option>
                  </select>
                </div>

                {/* Priority */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Priority</label>
                  <select
                    value={editPriority}
                    onChange={(e) => setEditPriority(e.target.value as Priority)}
                    disabled={!hasPermission('control:assess')}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-60"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>

                {/* Owner */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Assigned Owner
                  </label>
                  <select
                    value={editOwnerId}
                    onChange={(e) => setEditOwnerId(e.target.value)}
                    disabled={!hasPermission('control:assess')}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-60"
                  >
                    <option value="">Unassigned</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name} ({u.role})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Target Date */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Target Completion Date
                  </label>
                  <input
                    type="date"
                    value={editTargetDate}
                    onChange={(e) => setEditTargetDate(e.target.value)}
                    disabled={!hasPermission('control:assess')}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-60"
                  />
                </div>
              </div>

              {/* Implementation Statement */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Implementation Statement / Narrative
                </label>
                <textarea
                  rows={3}
                  value={editStatement}
                  onChange={(e) => setEditStatement(e.target.value)}
                  placeholder="Describe how your organization satisfies or enforces this control outcome..."
                  disabled={!hasPermission('control:assess')}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-60"
                />
              </div>

              {/* Internal Notes */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Assessor Notes &amp; Observations
                </label>
                <textarea
                  rows={2}
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Internal audit observations, blockers, or evidence references..."
                  disabled={!hasPermission('control:assess')}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-60"
                />
              </div>

              <div className="pt-3 flex justify-between items-center border-t border-slate-800">
                <span className="text-[11px] text-slate-500">
                  Last updated: {new Date(selectedControl.updated_at).toLocaleString()}
                </span>

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedControl(null)}
                  >
                    Close
                  </Button>

                  {hasPermission('control:assess') && (
                    <Button type="submit" variant="primary" size="sm" isLoading={isSaving}>
                      Save Assessment
                    </Button>
                  )}
                </div>
              </div>
            </form>
          </div>
        </Modal>
      )}
    </div>
  );
};