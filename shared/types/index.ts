// Auto-generated from Pydantic models
// Do not edit manually
// Run 'pnpm generate:types' to regenerate

export type ReceiptStatus = "pending" | "processing" | "completed" | "failed";

export type PlanType = "free" | "pro" | "business" | "enterprise";

export type RuleType = "threshold" | "keyword" | "category" | "time" | "pattern" | "ml" | "python" | "llm";

export type EvaluationStatus = "created" | "running" | "completed" | "error";

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface Location {
  city?: string | null;
  state?: string | null;
  zipcode?: string | null;
}

export interface LineItem {
  description?: string | null;
  product_code?: string | null;
  category?: string | null;
  item_price?: string | null;
  sale_price?: string | null;
  quantity?: string | null;
  total?: string | null;
}

export interface ReceiptDetails {
  merchant?: string | null;
  location?: Location;
  time?: string | null;
  items?: LineItem[];
  subtotal?: string | null;
  tax?: string | null;
  total?: string | null;
  handwritten_notes?: string[];
}

export interface AuditDecision {
  not_travel_related: boolean;
  amount_over_limit: boolean;
  math_error: boolean;
  handwritten_x: boolean;
  reasoning: string;
  needs_audit: boolean;
}

export interface ProcessingResult {
  receipt_details: ReceiptDetails;
  audit_decision: AuditDecision;
  processing_time_ms: number;
  costs: Record<string, any>;
  processing_successful?: boolean;
  error_message?: string | null;
}

export interface EvaluationRecord {
  receipt_image_path: string;
  correct_receipt_details: ReceiptDetails;
  predicted_receipt_details: ReceiptDetails;
  correct_audit_decision: AuditDecision;
  predicted_audit_decision: AuditDecision;
}

export interface User {
  id: number;
  clerk_id: string;
  email: string;
  name: string;
  plan: PlanType;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  clerk_id: string;
  email: string;
  name: string;
  plan?: PlanType;
}

export interface UserUpdate {
  name?: string | null;
  plan?: PlanType | null;
}

export interface Receipt {
  id: number;
  filename: string;
  status: ReceiptStatus;
  extracted_data?: Record<string, any> | null;
  audit_decision?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  task_id?: string | null;
  processing_duration_ms?: number | null;
  job_id?: string | null;
}

export interface ReceiptResponse {
  id: number;
  filename: string;
  status: ReceiptStatus;
  extracted_data?: Record<string, any> | null;
  audit_decision?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  task_id?: string | null;
  task_started_at?: string | null;
  task_completed_at?: string | null;
  task_error?: string | null;
  task_retry_count?: number;
  processing_duration_ms?: number | null;
  extraction_progress?: number;
  audit_progress?: number;
}

export interface ReceiptUpdate {
  filename?: string | null;
  status?: ReceiptStatus | null;
  extracted_data?: Record<string, any> | null;
  audit_decision?: Record<string, any> | null;
  updated_at?: string | null;
}

export interface ReceiptListResponse {
  receipts: ReceiptRead[];
}

export interface AuditRuleBase {
  name: string;
  type: RuleType;
  config: Record<string, any>;
  active?: boolean;
}

export interface AuditRuleCreate {
  name: string;
  type: RuleType;
  config: Record<string, any>;
  active?: boolean;
}

export interface AuditRuleNLCreate {
  name: string;
  description: string;
  threshold?: number;
}

export interface AuditRuleUpdate {
  name?: string | null;
  config?: Record<string, any> | null;
  active?: boolean | null;
}

export interface AuditRule {
  name: string;
  type: RuleType;
  config: Record<string, any>;
  active?: boolean;
  id: number;
  created_at: string;
  updated_at: string;
}

export interface PromptTemplateBase {
  name: string;
  type: string;
  content: string;
}

export interface PromptTemplateCreate {
  name: string;
  type: string;
  content: string;
}

export interface PromptTemplateUpdate {
  name?: string | null;
  content?: string | null;
}

export interface PromptTemplate {
  name: string;
  type: string;
  content: string;
  id: number;
  created_at: string;
  updated_at: string;
}

export interface EvaluationCreate {
  model_name: string;
  receipt_ids: number[];
}

export interface EvaluationSummary {
  id: number;
  model_name: string;
  status: EvaluationStatus;
  summary_metrics?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface EvaluationUpdate {
  name?: string | null;
  notes?: string | null;
}

export interface CostAnalysisCreate {
  evaluation_id: number;
  false_positive_rate: number;
  false_negative_rate: number;
  per_receipt_cost: number;
  audit_cost_per_receipt: number;
  missed_audit_penalty: number;
}

export interface CostAnalysis {
  id: number;
  evaluation_id: number;
  parameters: Record<string, any>;
  result: Record<string, any>;
  created_at: string;
}

export interface Audit {
  receipt_id: number;
  decision: Record<string, any>;
  created_at: string;
}

export interface Job {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  payload?: Record<string, any> | null;
  result?: Record<string, any> | null;
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  receipt_id?: number | null;
}
