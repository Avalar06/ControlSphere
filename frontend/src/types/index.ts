export type Role = 'ADMIN' | 'GRC_ANALYST' | 'SECURITY_ANALYST' | 'AUDITOR' | 'MANAGER' | 'VIEWER';

export interface Organization {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  organization_id: number;
  created_at: string;
  updated_at: string;
  organization?: Organization;
  permissions?: string[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  organization_id: number;
  actor_id: number | null;
  actor_email: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  status: string;
  ip_address: string | null;
  user_agent: string | null;
  details: Record<string, any> | null;
}

export interface HealthStatus {
  status: string;
  app: string;
  version: string;
  environment: string;
  database?: string;
}