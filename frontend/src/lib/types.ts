export interface SourceRef {
  dataset: string;
  record_id: string;
  retrieved_at: string | null;
  url: string | null;
  kind: string;
}

export interface Weights {
  distance: number;
  recency: number;
  living_area: number;
  beds: number;
  baths: number;
  lot_size: number;
  age: number;
  style: number;
  condition: number;
  features: number;
}

export interface Criteria {
  max_distance_miles: number;
  lookback_months: number;
  max_results: number;
  min_comps: number;
  allowed_validity: string[];
  min_price: number;
  same_property_type: boolean;
  exclude_multi_parcel: boolean;
  living_area_tolerance_pct: number | null;
  weights: Weights;
}

export interface FieldMapRow {
  workbook: string;
  status: string;
  source: string;
  note: string;
}

export interface Meta {
  target_zips: string[];
  ai_enabled: boolean;
  ai_model: string;
  ai_provider: "openai" | "anthropic" | null;
  today: string;
  data: {
    last_refresh: null | {
      id: number;
      provider: string;
      zips: string;
      started_at: string;
      finished_at: string;
      counts: Record<string, unknown>;
    };
    parcels: number;
    sales: number;
    latest_sale_date: string | null;
  };
  provider: {
    key: string;
    label: string;
    attribution: string;
    terms_url: string;
    terms_summary: string;
    datasets: { key: string; title: string; url: string }[];
  };
  default_criteria: Criteria;
  validity_options: { default: string[]; optional: string[] };
  field_map: FieldMapRow[];
}

export interface SearchResult {
  pin: string;
  address: string;
  city: string;
  zip: string;
  lat: number | null;
  lon: number | null;
  property_type: string | null;
  land_use: string | null;
  subdivision?: string | null;
  block?: string | null;
  lot?: string | null;
  street?: string | null;
}

export interface AreaOption {
  name: string;
  count: number;
}

export interface Property {
  pin: string;
  address: string | null;
  city: string | null;
  zip: string | null;
  lat: number | null;
  lon: number | null;
  property_type: string;
  land_use: string | null;
  subdivision: string | null;
  style: string | null;
  year_built: number | null;
  effective_year: number | null;
  year_remodeled: number | null;
  beds: number | null;
  full_baths: number | null;
  half_baths: number | null;
  baths_label: string | null;
  above_grade_sf: number | null;
  rec_room_sf: number | null;
  fireplaces: number | null;
  basement: string | null;
  garage: boolean | null;
  garage_evidence: string | null;
  condition: string | null;
  grade: string | null;
  exterior_wall: string | null;
  lot_sf: number | null;
  lot_acres: number | null;
  dwelling_count: number;
  assessed_total: number | null;
  assessed_tax_year: number | null;
  total_finished_sf: number | null;
  total_finished_source: string | null;
  sources: SourceRef[];
  notes: string[];
}

export interface Sale {
  sale_id: number;
  pin: string;
  sale_date: string;
  price: number | null;
  validity: string | null;
  deed_book: string | null;
  deed_page: string | null;
  deed_ref: string;
  multi_parcel: boolean;
  in_latest_source: boolean;
  retrieved_at: string | null;
}

export interface Factor {
  key: string;
  label: string;
  weight: number;
  score: number | null;
  subject_value: string | null;
  comp_value: string | null;
  detail: string;
}

export interface Comp {
  sale_id: number;
  rank: number;
  score: number;
  selected: boolean;
  address: string;
  pin: string;
  zip: string | null;
  lat: number | null;
  lon: number | null;
  distance_miles: number | null;
  months_before: number;
  sale: Sale;
  property: Property;
  ppsf_above_grade: number | null;
  total_finished_sf: number | null;
  total_finished_source: string | null;
  ppsf_total_finished: number | null;
  factors: Factor[];
  reason: string;
  strengths: string[];
  differences: string[];
  missing: string[];
  warnings: string[];
  source: SourceRef;
}

export interface Adjustment {
  label: string;
  amount: number;
  /** Garage/ADU area, shown as "SF" next to the amount (workbook column T). */
  sf?: number | null;
  note?: string | null;
  source?: string;
}

export interface BasisResult {
  basis: "above_grade" | "total_finished";
  label: string;
  available: boolean;
  reason_unavailable: string | null;
  subject_area: number | null;
  subject_area_source: string | null;
  comps: { sale_id: number; label: string; price: number; area: number; ppsf: number }[];
  comps_missing_area: string[];
  n: number;
  ppsf: { mean?: number; median?: number; high?: number; low?: number };
  indicated: { mean?: number; median?: number; high?: number; low?: number };
  estimate: number | null;
  range_low: number | null;
  range_high: number | null;
  base_value: number | null;
  appreciation_amount: number;
  adjustments_total: number;
  lines: string[];
  warnings: string[];
}

export interface Valuation {
  bases: { above_grade: BasisResult; total_finished: BasisResult };
  primary_basis: "above_grade" | "total_finished" | null;
  estimate: number | null;
  range_low: number | null;
  range_high: number | null;
  adjustments: Adjustment[];
  adjustments_total: number;
  appreciation_pct: number;
  point_statistic: "mean" | "median";
  warnings: string[];
}

export interface FunnelStep {
  key: string;
  label: string;
  removed: number;
  remaining: number;
  detail: string | null;
}

export interface Hint {
  change: string;
  eligible: number;
  added: number;
  patch: Partial<Criteria>;
}

export interface Analysis {
  subject: Property;
  subject_label: string;
  valuation_date: string;
  criteria: Criteria;
  search: {
    window_start: string;
    pool_count: number;
    funnel: FunnelStep[];
    eligible_count: number;
    later_sales_excluded: number;
    limited: boolean;
    insufficient: boolean;
    limit_explanation: string | null;
    hints: Hint[];
  };
  selection_mode: "auto" | "manual";
  selected_sale_ids: number[];
  comps: Comp[];
  valuation: Valuation;
  sale_history: Sale[];
  latest_transfer: Sale | null;
  last_market_sale: Sale | null;
  change_since_last_sale: null | {
    label: string;
    amount: number;
    pct: number;
    last_sale_price: number;
    last_sale_date: string;
  };
  condition_evidence: { recorded: string[]; needs_inspection: string[]; note: string };
  warnings: string[];
  sources: SourceRef[];
  timing_ms: number;
}

export interface CMARequest {
  subject_pin: string;
  valuation_date: string;
  criteria: Criteria;
  selected_sale_ids: number[] | null;
  adjustments: Adjustment[];
  appreciation_pct: number;
  point_statistic: "mean" | "median";
  primary_basis: "auto" | "above_grade" | "total_finished";
}

export interface Branding {
  company: string;
  agent_name: string;
  agent_title: string;
  phone: string;
  email: string;
  website: string;
  license_line: string;
  primary_color: string;
  logo_data_url: string | null;
  footer_note: string;
}

export interface ReportModel {
  title: string;
  prepared_for: string;
  prepared_on: string;
  valuation_date: string;
  branding: Branding;
  subject_rows: [string, string, string][];
  estimate: {
    estimate: string;
    range: string;
    basis: string;
    statistic: string;
    change: Analysis["change_since_last_sale"];
  };
  method_lines: string[];
  other_methods: { label: string; available: boolean; estimate: string | null; reason: string | null }[];
  adjustments: Adjustment[];
  comps: Record<string, string | number>[];
  map_png_b64: string | null;
  narrative: string;
  condition_evidence: Analysis["condition_evidence"];
  limitations: string[];
  sources: (SourceRef & { what: string })[];
  data_note: string;
  terms: { summary: string; url: string };
  disclaimer: string;
  fingerprint: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  tool_calls?: { tool: string; input: Record<string, unknown>; error: boolean }[];
}
