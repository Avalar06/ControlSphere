import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { UsersPage } from './pages/UsersPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { PlaceholderModulePage } from './pages/PlaceholderModulePage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected Application Shell */}
            <Route element={<AppLayout />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/users" element={<UsersPage />} />
              <Route path="/audit-logs" element={<AuditLogsPage />} />

              {/* Module Placeholders with Roadmap info */}
              <Route
                path="/frameworks"
                element={
                  <PlaceholderModulePage
                    title="Framework Management"
                    phase="Phase 2"
                    workflowStep="Framework Definition"
                    description="Browse and manage structured compliance frameworks (NIST CSF 2.0, ISO 27001, SOC 2)."
                    upcomingFeatures={[
                      'Structured NIST Cybersecurity Framework 2.0 hierarchy (Functions, Categories, Subcategories)',
                      'Cross-framework domain mappings and applicability scoping',
                      'Organizational framework target profiles',
                    ]}
                  />
                }
              />

              <Route
                path="/controls"
                element={
                  <PlaceholderModulePage
                    title="Controls Library"
                    phase="Phase 2"
                    workflowStep="Control Implementation"
                    description="Central security controls inventory with owners, maturity tracking, and evidence requirements."
                    upcomingFeatures={[
                      'Detailed control cards with implementation guidance',
                      'Control status tracking (Compliant, Partially Compliant, Non-Compliant, Not Applicable)',
                      'Direct linkage to evidence requirements and risks',
                    ]}
                  />
                }
              />

              <Route
                path="/evidence"
                element={
                  <PlaceholderModulePage
                    title="Evidence Library & Assurance"
                    phase="Phase 3"
                    workflowStep="Evidence Collection"
                    description="Secure evidence repository with integrity verification, automated expiration alerts, and reviews."
                    upcomingFeatures={[
                      'MIME-validated, virus-checked secure file uploads (PDF, XLSX, CSV, Logs, Screenshots)',
                      'Evidence review workflows (Accept, Reject, Request Additional)',
                      'Integrity hashing and tamper-evident audit records',
                    ]}
                  />
                }
              />

              <Route
                path="/assessments"
                element={
                  <PlaceholderModulePage
                    title="Control Assessments"
                    phase="Phase 4"
                    workflowStep="Assessment & Findings"
                    description="Rigorous control assessment workflow preserving immutable assessment history and gap findings."
                    upcomingFeatures={[
                      'Assessor evaluation workflow linked to verified evidence',
                      'Deficiency finding generation with severity scoring (Low, Medium, High, Critical)',
                      'Automated gap analysis linked to risk register',
                    ]}
                  />
                }
              />

              <Route
                path="/risks"
                element={
                  <PlaceholderModulePage
                    title="Cybersecurity Risk Register"
                    phase="Phase 5"
                    workflowStep="Risk Management"
                    description="Deterministic risk calculation engine evaluating inherent risk, control effectiveness, and residual risk."
                    upcomingFeatures={[
                      'Deterministic backend risk engine (Likelihood x Impact, 1x1 to 5x5)',
                      'Inherent risk vs. Residual risk calculation matrix',
                      'Interactive Risk Heatmap and Treatment Plans (Mitigate, Transfer, Accept, Avoid)',
                    ]}
                  />
                }
              />

              <Route
                path="/audits"
                element={
                  <PlaceholderModulePage
                    title="Audit Workspace & Readiness"
                    phase="Phase 7"
                    workflowStep="Audit Readiness"
                    description="Audit project management and deterministic audit readiness scoring engine."
                    upcomingFeatures={[
                      'Deterministic Audit Readiness Score (e.g. 72%) with explainable blockers breakdown',
                      'What is preventing us from reaching 90%? actionable gap list',
                      'Comprehensive auditor workspace with exportable audit packages',
                    ]}
                  />
                }
              />

              <Route
                path="/policies"
                element={
                  <PlaceholderModulePage
                    title="Information Security Policies"
                    phase="Phase 2"
                    workflowStep="Governance"
                    description="Versioned policy repository mapped directly to controls and compliance frameworks."
                    upcomingFeatures={[
                      'Pre-built security policy templates (Access Control, Password, Incident Response, Backup)',
                      'Policy lifecycle and review dates',
                      'Control-to-policy compliance mapping',
                    ]}
                  />
                }
              />

              <Route
                path="/ai-analyst"
                element={
                  <PlaceholderModulePage
                    title="AI GRC Analyst"
                    phase="Phase 9"
                    workflowStep="AI Governance & Assistance"
                    description="AI-assisted compliance reasoning with strict human-in-the-loop governance."
                    upcomingFeatures={[
                      'Assistive evidence analysis and gap recommendations (AI never dictates authoritative status)',
                      'Plain-language control explanation and remediation suggestions',
                      'Transparent confidence scoring, reasoning logs, and audit trails',
                    ]}
                  />
                }
              />

              <Route
                path="/settings"
                element={
                  <PlaceholderModulePage
                    title="Platform Settings"
                    phase="Phase 1"
                    workflowStep="Tenant Configuration"
                    description="Tenant configuration, security policies, and integrations."
                    upcomingFeatures={[
                      'Organization profile and branding',
                      'Password policy and session timeout settings',
                      'Storage provider configuration (Local FS / S3-compatible)',
                    ]}
                  />
                }
              />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};
export default App;
