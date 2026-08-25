import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, AlertCircle, Building } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@apexfinancial.com');
  const [password, setPassword] = useState('AdminPassword123!');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      console.error(err);
      setError(
        err.response?.data?.detail || 'Authentication failed. Please verify your credentials.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
  };

  return (
    <div className="min-h-screen w-screen bg-[#070b13] flex flex-col justify-center items-center p-4 relative overflow-hidden">
      {/* Subtle background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-indigo-900/10 blur-[120px] rounded-full pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex h-12 w-12 rounded-xl bg-indigo-600 items-center justify-center text-white shadow-lg shadow-indigo-600/30 mb-4 font-bold text-xl">
            CS
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">ControlSphere</h1>
          <p className="text-xs text-slate-400 mt-1">
            Enterprise Cybersecurity Governance, Risk &amp; Compliance Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-6 shadow-2xl backdrop-blur-md">
          <div className="flex items-center gap-2 mb-5 pb-3 border-b border-slate-800">
            <Lock size={16} className="text-indigo-400" />
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Authorized Tenant Access
            </h2>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-md bg-rose-950/60 border border-rose-800/70 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle size={15} className="shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Corporate Email Address
              </label>
              <div className="relative">
                <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="analyst@apexfinancial.com"
                  className="w-full bg-slate-950 border border-slate-800 rounded-md pl-9 pr-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-600"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Authentication Password
              </label>
              <div className="relative">
                <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••••••"
                  className="w-full bg-slate-950 border border-slate-800 rounded-md pl-9 pr-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-600"
                />
              </div>
            </div>

            <Button
              type="submit"
              isLoading={isLoading}
              variant="primary"
              className="w-full mt-2"
            >
              Sign In to Organization
            </Button>
          </form>

          {/* Quick Demo Switcher */}
          <div className="mt-6 pt-4 border-t border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Demo Tenant Accounts
              </span>
              <span className="text-[10px] text-indigo-400 font-mono">1-Click Fill</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('admin@apexfinancial.com', 'AdminPassword123!')}
                className="p-2 text-left rounded bg-slate-950/80 border border-slate-800 hover:border-indigo-500/50 hover:bg-indigo-950/20 text-xs transition-colors cursor-pointer"
              >
                <div className="font-semibold text-slate-200 text-[11px]">Apex Admin</div>
                <div className="text-[10px] text-indigo-400">ADMIN (Full)</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('analyst@apexfinancial.com', 'AnalystPassword123!')}
                className="p-2 text-left rounded bg-slate-950/80 border border-slate-800 hover:border-indigo-500/50 hover:bg-indigo-950/20 text-xs transition-colors cursor-pointer"
              >
                <div className="font-semibold text-slate-200 text-[11px]">Apex Analyst</div>
                <div className="text-[10px] text-sky-400">GRC_ANALYST</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('auditor@apexfinancial.com', 'AuditorPassword123!')}
                className="p-2 text-left rounded bg-slate-950/80 border border-slate-800 hover:border-indigo-500/50 hover:bg-indigo-950/20 text-xs transition-colors cursor-pointer"
              >
                <div className="font-semibold text-slate-200 text-[11px]">Apex Auditor</div>
                <div className="text-[10px] text-amber-400">AUDITOR</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('viewer@apexfinancial.com', 'ViewerPassword123!')}
                className="p-2 text-left rounded bg-slate-950/80 border border-slate-800 hover:border-indigo-500/50 hover:bg-indigo-950/20 text-xs transition-colors cursor-pointer"
              >
                <div className="font-semibold text-slate-200 text-[11px]">Apex Viewer</div>
                <div className="text-[10px] text-slate-400">VIEWER (Read)</div>
              </button>
            </div>

            {/* Tenant Isolation Test login */}
            <div className="mt-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('admin@meridianhealth.com', 'MeridianAdmin123!')}
                className="w-full p-1.5 text-left rounded bg-slate-950/50 border border-slate-800/80 hover:border-slate-700 text-xs transition-colors flex items-center justify-between cursor-pointer"
              >
                <div className="flex items-center gap-1.5">
                  <Building size={12} className="text-slate-500" />
                  <span className="text-[10px] text-slate-300">Meridian Health (Tenant 2 Admin)</span>
                </div>
                <span className="text-[9px] font-mono text-slate-500">Cross-Tenant Test</span>
              </button>
            </div>
          </div>
        </div>

        {/* Security Notice */}
        <div className="mt-6 text-center text-[11px] text-slate-500">
          Enforcing server-side RBAC, strict tenant isolation, &amp; immutable audit logging.
        </div>
      </div>
    </div>
  );
};