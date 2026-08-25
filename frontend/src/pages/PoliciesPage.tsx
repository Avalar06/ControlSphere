import React, { useEffect, useState } from 'react';
import { BookOpen, Plus, Search, RefreshCw, AlertCircle, History, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import type { Policy, PolicyStatus, PolicyType, User } from '../types';
import { Card, CardHeader } from '../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

export const PoliciesPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
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

  useEffect(() => {
    fetchPolicies();
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
      await fetchPolicies();
    } catch (err: any) {
      console.error(err);
      setFormError(err.response?.data?.detail || 'Failed to create policy.');
    } finally {
      setIsCreating(false);
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

  const filteredPolicies = policies.filter((pol) => {
    if (selectedStatus !== 'ALL' && pol.status !== selectedStatus) {
      return false;
    }
    if (selectedType !== 'ALL' && pol.policy_type !== selectedType) {
      return false;
    }
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      const matchTitle = pol.title.toLowerCase().includes(term);
      const matchDesc = pol.description?.toLowerCase().includes(term);
      if (!matchTitle && !matchDesc) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="text-indigo-400" size={20} />
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">Security Policy Governance</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Version-controlled organizational policies mapped directly to framework controls and regulatory requirements.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" onClick={fetchPolicies} isLoading={isLoading}>
            <RefreshCw size={13} />
            Refresh
          </Button>

          {hasPermission('policy:manage') && (
            <Button size="sm" variant="primary" onClick={() => setIsModalOpen(true)}>
              <Plus size={14} />
              New Policy
            </Button>
          )}
        </div>
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
              placeholder="Search policies by title or description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            {/* Status Filter */}
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

            {/* Type Filter */}
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
          subtitle="Click on any policy to view version history, markdown content, and mapped control outcomes."
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
                <TableHeaderCell>Version</TableHeaderCell>
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
                        <span>View</span>
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
    </div>
  );
};