import React, { useState, useEffect } from 'react';
import {
  Link2,
  Key,
  ShieldCheck,
  RefreshCw,
  Lock,
} from 'lucide-react';
import { integrationService } from '../lib/integrationService';
import type {
  IntegrationProvider,
  IntegrationConnection,
  IntegrationAuthType,
} from '../types';

export const IntegrationCenterPage: React.FC = () => {
  const [providers, setProviders] = useState<IntegrationProvider[]>([]);
  const [connections, setConnections] = useState<IntegrationConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [testingId, setTestingId] = useState<number | null>(null);

  // Credential configuration modal
  const [selectedConnection, setSelectedConnection] = useState<IntegrationConnection | null>(null);
  const [authType, setAuthType] = useState<IntegrationAuthType>('API_KEY');
  const [credentialFields, setCredentialFields] = useState<Record<string, string>>({
    api_key: '',
    role_arn: '',
    external_id: '',
    token: '',
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [provRes, connRes] = await Promise.all([
        integrationService.listProviders(),
        integrationService.listConnections(),
      ]);
      setProviders(provRes);
      setConnections(connRes);
    } catch (err) {
      console.error('Failed to load integration center data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleTestConnection = async (id: number) => {
    setTestingId(id);
    try {
      await integrationService.testConnection(id);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Connection test failed or SSRF protection triggered.');
    } finally {
      setTestingId(null);
    }
  };

  const handleSaveCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedConnection) return;

    try {
      const filteredCreds: Record<string, string> = {};
      Object.entries(credentialFields).forEach(([k, v]) => {
        if (v.trim()) filteredCreds[k] = v.trim();
      });

      await integrationService.setCredentials(selectedConnection.id, {
        auth_type: authType,
        credentials: filteredCreds,
      });

      setSelectedConnection(null);
      setCredentialFields({ api_key: '', role_arn: '', external_id: '', token: '' });
      fetchData();
    } catch (err) {
      console.error('Failed to save encrypted credentials', err);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
      case 'HEALTHY':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'UNAUTHENTICATED':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'ERROR':
      case 'INACTIVE':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Link2 className="h-7 w-7 text-primary-500" />
            Enterprise Integrations & Connectors
          </h1>
          <p className="text-sm text-slate-400">
            Automated telemetry ingestion connectors with AES-256 encrypted credential storage and SSRF defense-in-depth.
          </p>
        </div>
      </div>

      {/* Connection List */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-blue-400" />
            Active Integration Connections ({connections.length})
          </h2>
        </div>

        {connections.length === 0 ? (
          <div className="text-xs text-slate-500">No integration connections configured yet.</div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {connections.map((c) => (
              <div key={c.id} className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-primary-400">{c.connection_code}</span>
                  <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${getStatusBadge(c.last_health_status || c.status)}`}>
                    {c.last_health_status || c.status}
                  </span>
                </div>

                <div className="text-sm font-semibold text-white">{c.name}</div>
                {c.base_url && (
                  <div className="text-xs font-mono text-slate-500 truncate">{c.base_url}</div>
                )}

                <div className="space-y-1">
                  <div className="text-[11px] text-slate-400">Granted Scopes:</div>
                  <div className="flex flex-wrap gap-1">
                    {c.granted_scopes.map((sc, idx) => (
                      <span key={idx} className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-300">
                        {sc}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                  <button
                    onClick={() => {
                      setSelectedConnection(c);
                    }}
                    className="flex items-center gap-1 text-xs font-semibold text-slate-300 hover:text-white"
                  >
                    <Key className="h-3.5 w-3.5 text-amber-400" />
                    {c.is_credential_configured ? 'Rotate Secret' : 'Configure Secret'}
                  </button>

                  <button
                    onClick={() => handleTestConnection(c.id)}
                    disabled={testingId === c.id}
                    className="flex items-center gap-1 rounded bg-slate-800 px-2.5 py-1 text-xs font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                  >
                    <RefreshCw className={`h-3 w-3 ${testingId === c.id ? 'animate-spin' : ''}`} />
                    Test
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Available System Providers */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="text-lg font-bold text-white mb-4">Supported System Providers ({providers.length})</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {providers.map((p) => (
            <div key={p.id} className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-white">{p.provider_type}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
                  {p.auth_type}
                </span>
              </div>
              <div className="text-sm font-semibold text-slate-200">{p.name}</div>
              <div className="text-xs text-slate-400">{p.description}</div>
              <div className="pt-2 text-[10px] text-slate-500 font-mono">
                Allowlist: {p.allowed_domains.join(', ')}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Secret Configuration Modal */}
      {selectedConnection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
              <Lock className="h-5 w-5 text-amber-500" />
              Configure Fernet-Encrypted Secret
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Credentials are encrypted at rest with AES-256 and never returned in API responses.
            </p>

            <form onSubmit={handleSaveCredentials} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Auth Type</label>
                <select
                  value={authType}
                  onChange={(e) => setAuthType(e.target.value as IntegrationAuthType)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:outline-none"
                >
                  <option value="API_KEY">API_KEY</option>
                  <option value="STS_ROLE">STS_ROLE (AWS IAM)</option>
                  <option value="BEARER_TOKEN">BEARER_TOKEN</option>
                  <option value="OAUTH2">OAUTH2</option>
                </select>
              </div>

              {authType === 'STS_ROLE' ? (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Role ARN</label>
                    <input
                      type="text"
                      placeholder="arn:aws:iam::123456789012:role/ControlSphereCollector"
                      value={credentialFields.role_arn}
                      onChange={(e) => setCredentialFields({ ...credentialFields, role_arn: e.target.value })}
                      className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">External ID</label>
                    <input
                      type="password"
                      placeholder="••••••••••••"
                      value={credentialFields.external_id}
                      onChange={(e) => setCredentialFields({ ...credentialFields, external_id: e.target.value })}
                      className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:outline-none"
                    />
                  </div>
                </>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Secret Key / Token</label>
                  <input
                    type="password"
                    placeholder="••••••••••••"
                    value={credentialFields.api_key || credentialFields.token}
                    onChange={(e) => setCredentialFields({ ...credentialFields, api_key: e.target.value, token: e.target.value })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedConnection(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-primary-600 px-4 py-2 text-xs font-medium text-white hover:bg-primary-500"
                >
                  Encrypt & Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
