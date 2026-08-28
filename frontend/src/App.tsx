import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { UsersPage } from './pages/UsersPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { FrameworksPage } from './pages/FrameworksPage';
import { ControlsPage } from './pages/ControlsPage';
import { PoliciesPage } from './pages/PoliciesPage';
import { PolicyDetailPage } from './pages/PolicyDetailPage';
import { EvidencePage } from './pages/EvidencePage';
import { EvidenceRequirementsPage } from './pages/EvidenceRequirementsPage';
import { AssessmentsPage } from './pages/AssessmentsPage';
import { AssessmentDetailPage } from './pages/AssessmentDetailPage';
import { FindingsPage } from './pages/FindingsPage';
import { FindingDetailPage } from './pages/FindingDetailPage';
import { RisksPage } from './pages/RisksPage';
import { RiskDetailPage } from './pages/RiskDetailPage';
import { ExceptionsPage } from './pages/ExceptionsPage';
import { ExceptionDetailPage } from './pages/ExceptionDetailPage';
import { AuditsPage } from './pages/AuditsPage';
import { AuditDetailPage } from './pages/AuditDetailPage';
import { ContinuousMonitoringPage } from './pages/ContinuousMonitoringPage';
import { HarmonizationPage } from './pages/HarmonizationPage';
import { FrameworkPosturePage } from './pages/FrameworkPosturePage';
import { CommonControlDetailPage } from './pages/CommonControlDetailPage';
import { VendorsPage } from './pages/VendorsPage';
import { VendorDetailPage } from './pages/VendorDetailPage';
import { VendorAssessmentDetailPage } from './pages/VendorAssessmentDetailPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { IncidentDetailPage } from './pages/IncidentDetailPage';
import { RemediationsPage } from './pages/RemediationsPage';
import { RemediationDetailPage } from './pages/RemediationDetailPage';
import { QuantRiskPage } from './pages/QuantRiskPage';
import { QuantScenarioDetailPage } from './pages/QuantScenarioDetailPage';
import { ResiliencePage } from './pages/ResiliencePage';
import { BusinessProcessDetailPage } from './pages/BusinessProcessDetailPage';
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

              {/* Phase 2, 7 & 8: Continuous Monitoring, Harmonization, Frameworks, Controls & Policy Modules */}
              <Route path="/monitoring" element={<ContinuousMonitoringPage />} />
              <Route path="/harmonization" element={<HarmonizationPage />} />
              <Route path="/harmonization/frameworks/:id" element={<FrameworkPosturePage />} />
              <Route path="/harmonization/common-controls/:id" element={<CommonControlDetailPage />} />
              <Route path="/frameworks" element={<FrameworksPage />} />
              <Route path="/controls" element={<ControlsPage />} />
              <Route path="/policies" element={<PoliciesPage />} />
              <Route path="/policies/:id" element={<PolicyDetailPage />} />

              {/* Phase 3: Evidence Management & Assurance */}
              <Route path="/evidence" element={<EvidencePage />} />
              <Route path="/evidence-requirements" element={<EvidenceRequirementsPage />} />

              {/* Phase 4: Assessments, Findings & Remediation */}
              <Route path="/assessments" element={<AssessmentsPage />} />
              <Route path="/assessments/:id" element={<AssessmentDetailPage />} />
              <Route path="/findings" element={<FindingsPage />} />
              <Route path="/findings/:id" element={<FindingDetailPage />} />

              {/* Phase 5: Risk Management, Exceptions & Governance */}
              <Route path="/risks" element={<RisksPage />} />
              <Route path="/risks/:id" element={<RiskDetailPage />} />
              <Route path="/exceptions" element={<ExceptionsPage />} />
              <Route path="/exceptions/:id" element={<ExceptionDetailPage />} />

              {/* Phase 6: Audit Management & Assurance Readiness */}
              <Route path="/audits" element={<AuditsPage />} />
              <Route path="/audits/:id" element={<AuditDetailPage />} />

              {/* Phase 9: Third-Party & Vendor Risk Management (TPRM) */}
              <Route path="/vendors" element={<VendorsPage />} />
              <Route path="/vendors/:id" element={<VendorDetailPage />} />
              <Route path="/vendors/assessments/:assessmentId" element={<VendorAssessmentDetailPage />} />

              {/* Phase 10: Security Incident Management, Breach Governance & Regulatory Disclosure */}
              <Route path="/incidents" element={<IncidentsPage />} />
              <Route path="/incidents/:id" element={<IncidentDetailPage />} />

              {/* Phase 11: Governed Remediation Orchestration & Corrective Action Plans (ROC-V) */}
              <Route path="/remediations" element={<RemediationsPage />} />
              <Route path="/remediations/:id" element={<RemediationDetailPage />} />

              {/* Phase 12: Cyber Risk Quantification & Loss Modeling (QUANTUM-GRC) */}
              <Route path="/quant-risk" element={<QuantRiskPage />} />
              <Route path="/quant-risk/scenarios/:id" element={<QuantScenarioDetailPage />} />

              {/* Phase 13: Operational Resilience & Business Impact Analysis (RESILIENCE-GRC) */}
              <Route path="/resilience" element={<ResiliencePage />} />
              <Route path="/resilience/processes/:id" element={<BusinessProcessDetailPage />} />

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