import React, { useEffect, useState } from 'react';
import { UserPlus, Users, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import type { Role, User } from '../types';
import { Card, CardHeader } from '../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

export const UsersPage: React.FC = () => {
  const { organization, hasPermission } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<Role>('GRC_ANALYST');
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchUsers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await api.get<User[]>('/api/v1/users');
      setUsers(data);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load organization users.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      await api.post('/api/v1/users', {
        email,
        full_name: fullName,
        password,
        role,
        is_active: true,
      });
      setIsModalOpen(false);
      setEmail('');
      setFullName('');
      setPassword('');
      setRole('GRC_ANALYST');
      await fetchUsers();
    } catch (err: any) {
      console.error(err);
      setFormError(err.response?.data?.detail || 'Failed to create user.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getRoleVariant = (role: Role) => {
    switch (role) {
      case 'ADMIN':
        return 'purple';
      case 'GRC_ANALYST':
        return 'info';
      case 'AUDITOR':
        return 'warning';
      case 'VIEWER':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Users className="text-indigo-400" size={20} />
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">Organization User Management</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Manage users and assign GRC security roles strictly for <span className="text-slate-200 font-medium">{organization?.name}</span>.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" onClick={fetchUsers} isLoading={isLoading}>
            <RefreshCw size={13} />
            Refresh
          </Button>

          {hasPermission('user:create') && (
            <Button size="sm" variant="primary" onClick={() => setIsModalOpen(true)}>
              <UserPlus size={14} />
              Add User
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

      {/* Users Table */}
      <Card>
        <CardHeader
          title={`Active Organization Users (${users.length})`}
          subtitle="All users listed belong strictly to your tenant context."
        />

        {isLoading ? (
          <LoadingSpinner text="Fetching organization members..." />
        ) : users.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">
            No users found in this organization.
          </div>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>User</TableHeaderCell>
                <TableHeaderCell>Security Role</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell>Tenant Scope</TableHeaderCell>
                <TableHeaderCell>Member Since</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>
                    <div className="font-semibold text-slate-100 text-xs">{u.full_name}</div>
                    <div className="text-[11px] text-slate-400 font-mono">{u.email}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={getRoleVariant(u.role)}>{u.role}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5 text-xs text-emerald-400">
                      <CheckCircle2 size={13} />
                      <span>{u.is_active ? 'Active' : 'Disabled'}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs text-slate-400 font-mono">Org #{u.organization_id}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs text-slate-400">
                      {new Date(u.created_at).toLocaleDateString()}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Create User Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Provision New Organization User"
      >
        {formError && (
          <div className="mb-4 p-3 rounded bg-rose-950/60 border border-rose-800/70 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle size={14} className="shrink-0" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleCreateUser} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Jordan Mitchell"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="jordan@apexfinancial.com"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Temporary Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Security Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="GRC_ANALYST">GRC_ANALYST (Assessments, Evidence, Risks)</option>
              <option value="AUDITOR">AUDITOR (Read-only Audit &amp; Evidence Review)</option>
              <option value="VIEWER">VIEWER (Read-only Executive Access)</option>
              <option value="ADMIN">ADMIN (Full Tenant Management)</option>
            </select>
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
              isLoading={isSubmitting}
            >
              Create Account
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};