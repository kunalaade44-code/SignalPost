export interface Fact {
  field: string;
  value: any;
  source_url: string;
  source_type: string;
  retrieved_at: string;
  evidence: string;
  match_signals: string[];
  confidence: number;
  explanation: string;
}

export interface RejectedFact {
  field: string;
  candidate_value: any;
  source_url: string;
  reason: string;
  confidence: number;
}

export interface Role {
  role: string;
  name: string;
  from_date?: string | null;
  resigned?: boolean;
}

export interface FinancialYear {
  year: number;
  revenue?: number | null;
  profit?: number | null;
  operating_profit?: number | null;
  net_profit?: number | null;
  assets?: number | null;
  equity?: number | null;
  currency: string;
  source_url: string;
}

export interface ContactInfo {
  email?: string | null;
  phone?: string | null;
  postal_address?: string | null;
  visiting_address?: string | null;
}

export interface RunMetadata {
  requests: number;
  cost_usd: number;
  duration_ms?: number | null;
  cached?: boolean;
}

export interface CompanyProfile {
  org_number: string;
  legal_name: string;
  status: string;
  org_form: string;
  registered_date?: string | null;
  nace_codes: string[];
  address?: string | null;
  municipality?: string | null;
  municipality_number?: string | null;
  employees?: number | null;
  vat_registered?: boolean | null;
  website?: string | null;
  contact: ContactInfo;
  roles: Role[];
  financials: FinancialYear[];
  description?: string | null;
  social_links: string[];
  facts: Fact[];
  rejected_facts: RejectedFact[];
  profile_updated_at: string;
  last_checked_at: string;
  history_ref?: string | null;
  is_tracked?: boolean;
  run_metadata: RunMetadata;
}

export interface HistoryRevision {
  id: number;
  revision_ref: string;
  changed_at: string;
  change_reason: string;
  field_name: string;
  old_value: any;
  new_value: any;
}

export interface BatchRunState {
  run_id: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  total_companies: number;
  processed_count: number;
  successful_count: number;
  cached_count: number;
  failed_count: number;
  progress_pct: number;
  current_orgnr?: string | null;
  duration_seconds?: number;
  results: Array<{
    org_number: string;
    legal_name: string;
    status: string;
    cached: boolean;
  }>;
}

export interface SystemStats {
  database: {
    total_profiles: number;
    active_profiles: number;
    bankrupt_profiles: number;
    total_verified_facts: number;
    total_audit_events: number;
  };
  limits: {
    max_requests: number;
    max_cost_usd: number;
    max_run_time_seconds: number;
  };
  recent_profiles: Array<{
    org_number: string;
    legal_name: string;
    status: string;
    org_form: string;
    employees?: number;
    facts_count: number;
    last_checked_at: string;
  }>;
}
