import { api } from './api';
import type {
  FinancialRiskAppetite,
  FinancialRiskAppetiteApproveRequest,
  FinancialRiskAppetiteCreate,
  QuantOverviewResponse,
  QuantitativeRiskScenario,
  QuantitativeRiskScenarioCreate,
  QuantitativeRiskScenarioUpdate,
  QuantitativeSimulationRequest,
  QuantitativeSimulationRun,
  RosiAnalysis,
  RosiAnalysisCreate,
  ScenarioStatus,
  ThreatActorCategory,
} from '../types';

export const quantRiskService = {
  // ─── 0. Portfolio Overview & Posture ──────────────────────────────────────

  getOverview: async (): Promise<QuantOverviewResponse> => {
    const response = await api.get<QuantOverviewResponse>('/quant-risk/overview');
    return response.data;
  },

  // ─── 1. Quantitative Risk Scenarios ────────────────────────────────────────

  createScenario: async (
    data: QuantitativeRiskScenarioCreate
  ): Promise<QuantitativeRiskScenario> => {
    const response = await api.post<QuantitativeRiskScenario>('/quant-risk/scenarios', data);
    return response.data;
  },

  listScenarios: async (params?: {
    status?: ScenarioStatus;
    threat_category?: ThreatActorCategory;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<QuantitativeRiskScenario[]> => {
    const response = await api.get<QuantitativeRiskScenario[]>('/quant-risk/scenarios', {
      params,
    });
    return response.data;
  },

  getScenario: async (id: number): Promise<QuantitativeRiskScenario> => {
    const response = await api.get<QuantitativeRiskScenario>(`/quant-risk/scenarios/${id}`);
    return response.data;
  },

  updateScenario: async (
    id: number,
    data: QuantitativeRiskScenarioUpdate
  ): Promise<QuantitativeRiskScenario> => {
    const response = await api.put<QuantitativeRiskScenario>(`/quant-risk/scenarios/${id}`, data);
    return response.data;
  },

  activateScenario: async (id: number): Promise<QuantitativeRiskScenario> => {
    const response = await api.post<QuantitativeRiskScenario>(`/quant-risk/scenarios/${id}/activate`);
    return response.data;
  },

  freezeScenario: async (id: number): Promise<QuantitativeRiskScenario> => {
    const response = await api.post<QuantitativeRiskScenario>(`/quant-risk/scenarios/${id}/freeze`);
    return response.data;
  },

  archiveScenario: async (id: number): Promise<QuantitativeRiskScenario> => {
    const response = await api.post<QuantitativeRiskScenario>(`/quant-risk/scenarios/${id}/archive`);
    return response.data;
  },

  // ─── 2. Empirical Monte Carlo Simulation ───────────────────────────────────

  executeSimulation: async (
    scenarioId: number,
    data?: QuantitativeSimulationRequest
  ): Promise<QuantitativeSimulationRun> => {
    const response = await api.post<QuantitativeSimulationRun>(
      `/quant-risk/scenarios/${scenarioId}/simulate`,
      data || {}
    );
    return response.data;
  },

  listScenarioSimulations: async (
    scenarioId: number,
    params?: { skip?: number; limit?: number }
  ): Promise<QuantitativeSimulationRun[]> => {
    const response = await api.get<QuantitativeSimulationRun[]>(
      `/quant-risk/scenarios/${scenarioId}/simulations`,
      { params }
    );
    return response.data;
  },

  getSimulation: async (runId: number): Promise<QuantitativeSimulationRun> => {
    const response = await api.get<QuantitativeSimulationRun>(`/quant-risk/simulations/${runId}`);
    return response.data;
  },

  // ─── 3. Return on Security Investment (ROSI) ───────────────────────────────

  calculateRosi: async (
    scenarioId: number,
    data: RosiAnalysisCreate
  ): Promise<RosiAnalysis> => {
    const response = await api.post<RosiAnalysis>(
      `/quant-risk/scenarios/${scenarioId}/rosi`,
      data
    );
    return response.data;
  },

  listScenarioRosi: async (
    scenarioId: number,
    params?: { skip?: number; limit?: number }
  ): Promise<RosiAnalysis[]> => {
    const response = await api.get<RosiAnalysis[]>(
      `/quant-risk/scenarios/${scenarioId}/rosi`,
      { params }
    );
    return response.data;
  },

  getRosiAnalysis: async (analysisId: number): Promise<RosiAnalysis> => {
    const response = await api.get<RosiAnalysis>(`/quant-risk/rosi/${analysisId}`);
    return response.data;
  },

  // ─── 4. Financial Risk Appetite & Governance ─────────────────────────────

  createRiskAppetite: async (
    data: FinancialRiskAppetiteCreate
  ): Promise<FinancialRiskAppetite> => {
    const response = await api.post<FinancialRiskAppetite>('/quant-risk/appetites', data);
    return response.data;
  },

  listRiskAppetites: async (params?: {
    skip?: number;
    limit?: number;
  }): Promise<FinancialRiskAppetite[]> => {
    const response = await api.get<FinancialRiskAppetite[]>('/quant-risk/appetites', {
      params,
    });
    return response.data;
  },

  getCurrentAppetite: async (): Promise<FinancialRiskAppetite | null> => {
    const response = await api.get<FinancialRiskAppetite | null>('/quant-risk/appetites/current');
    return response.data;
  },

  getRiskAppetite: async (id: number): Promise<FinancialRiskAppetite> => {
    const response = await api.get<FinancialRiskAppetite>(`/quant-risk/appetites/${id}`);
    return response.data;
  },

  approveRiskAppetite: async (
    id: number,
    data?: FinancialRiskAppetiteApproveRequest
  ): Promise<FinancialRiskAppetite> => {
    const response = await api.post<FinancialRiskAppetite>(
      `/quant-risk/appetites/${id}/approve`,
      data || {}
    );
    return response.data;
  },
};