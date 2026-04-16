/* ── Backend API types ── */

export interface HealthResponse {
  status: string;
  timestamp: string;
  api_key_configured: boolean;
}

export interface AuthorInfo {
  name: string;
  affiliation: string;
  location: string;
  email: string;
}

export interface EquationInfo {
  id: string;
  label: string;
  notation: string;
  latex?: string;
  description?: string;
}

export interface DiagramInfo {
  id: string;
  label: string;
  caption: string;
  file: File | string;
  width?: number;
  height?: number;
}

export interface TableInfo {
  id: string;
  label: string;
  caption: string;
  headers: string[];
  rows: string[][];
}

export interface ResearchStructure {
  title: string;
  authors: AuthorInfo[];
  keywords: string[];
  research_topic: string;
  problem_statement: string;
  proposed_solution: string;
  objective: string;
  methodology: string;
  dataset?: string;
  experiments?: string;
  equations: EquationInfo[];
  diagrams: DiagramInfo[];
  tables?: TableInfo[];
  notes?: string;
}

export interface GenerateRequest {
  topic: string;
  notes?: string;
  diagrams: DiagramInfo[];
  equations: EquationInfo[];
  tables?: TableInfo[];
  authors: AuthorInfo[];
  max_references: number;
  model_name: string;
  research_structure?: ResearchStructure;
}

export interface GenerateResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface TaskStatus {
  task_id: string;
  status: string;
  step?: PipelineStage;
  progress: number;
  stages: Record<string, string>;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  result?: Record<string, any>;
  // Legacy fields for backward compatibility
  message?: string;
  paper_content?: string;
  authors?: AuthorInfo[];
  validation_result?: ValidationResult;
  ieee_report?: IEEEReport;
  enhancement_scores?: EnhancementScores;
  pdf_path?: string;
  [key: string]: any; // Allow additional properties
}

/* ── Validation types ── */

export interface ContentMetrics {
  word_count: number;
  sentence_count: number;
  avg_sentence_length: number;
  unique_words: number;
  vocabulary_richness: number;
  flesch_kincaid_grade: number;
}

export interface StructureMetrics {
  has_introduction: boolean;
  has_conclusion: boolean;
  has_sections: boolean;
  section_count: number;
  has_citations: boolean;
}

export interface QualityMetrics {
  grammar_errors: number;
  spelling_errors: number;
  repetition_ratio: number;
  topic_relevance_score: number;
}

export interface ValidationResult {
  overall_quality_score: number;
  quality_level: string;
  is_valid: boolean;
  content_metrics: ContentMetrics;
  structure_metrics: StructureMetrics;
  quality_metrics: QualityMetrics;
  validation_warnings: string[];
  validation_errors: string[];
}

/* ── IEEE Report types ── */

export interface IEEECleanupAction {
  action: string;
  section: string;
  detail: string;
}

export interface IEEEReport {
  is_ieee_ready: boolean;
  total_actions: number;
  keyword_relevance_score: number;
  novelty_detected: boolean;
  novelty_section: string | null;
  duplicates_removed: number;
  abstracts_consolidated: boolean;
  numbering_applied: boolean;
  references_merged: boolean;
  reference_count: number;
  weak_sections_rewritten: string[];
  citation_reference_consistent: boolean;
  orphan_citations: string[];
  unused_references: string[];
  actions: IEEECleanupAction[];
}

/* ── Enhancement Pipeline types ── */

export interface NoveltyAnalysis {
  novelty_score: number;
  identified_gaps: string[];
  proposed_contributions: string[];
  problem_gap: string;
  proposed_innovation: string;
  technical_improvement: string;
  expected_impact: string;
  enhanced: boolean;
  actions_taken: string[];
}

export interface QualityReport {
  sections_expanded: string[];
  sections_improved_vocabulary: string[];
  sections_improved_transitions: string[];
  repetition_fixes: number;
  total_words_added: number;
  initial_avg_ttr: number;
  final_avg_ttr: number;
  quality_improvement_score: number;
  actions_taken: string[];
}

export interface CitationReport {
  total_citations_found: number;
  total_references: number;
  orphan_citations: string[];
  unused_references: number[];
  citations_renumbered: number;
  references_removed: number;
  references_renumbered: number;
  citation_reference_consistent: boolean;
  format_fixes: number;
  actions_taken: string[];
}

export interface ReviewDimension {
  name: string;
  score: number;
  feedback: string;
  suggestions: string[];
}

export interface EnhancementReviewReport {
  dimensions: ReviewDimension[];
  overall_score: number;
  decision: "accept" | "minor_revision" | "major_revision" | "reject";
  weak_sections: string[];
  sections_regenerated: string[];
  reviewer_comments: string;
  passes_completed: number;
  actions_taken: string[];
}

export interface PostProcessorReport {
  duplicate_abstracts_removed: number;
  keywords_consolidated: boolean;
  sections_renumbered: number;
  reference_blocks_merged: number;
  raw_urls_removed: number;
  heading_fixes: number;
  total_actions: number;
  ieee_section_order_applied: boolean;
}

export interface EnhancementScores {
  novelty_score: number;
  ieee_compliance_score: number;
  reviewer_score: number;
  overall_quality_score: number;
  enhancement_time_seconds: number;
  stages_completed: string[];
  total_actions: number;
  novelty_analysis?: NoveltyAnalysis;
  quality_report?: QualityReport;
  citation_report?: CitationReport;
  review_report?: EnhancementReviewReport;
  post_processor_report?: PostProcessorReport;
}

/* ── New agent output types ── */

export interface SectionValidation {
  passed: boolean;
  score: number;
  issues: string[];
  warnings: string[];
}

export interface ValidationReport {
  overall_passed: boolean;
  overall_score: number;
  sections: Record<string, SectionValidation>;
  ieee_issues: string[];
  sections_to_regenerate: string[];
  summary: string;
}

export interface ReviewReport {
  overall_quality: "excellent" | "good" | "acceptable" | "needs_revision";
  score: number;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  language_issues: string[];
  contribution_clarity: "clear" | "unclear" | "missing";
  ready_for_submission: boolean;
  skipped?: boolean;
}

export interface PaperResult {
  abstract: string;
  introduction: string;
  related_work: string;
  methodology: string;
  implementation: string;
  results_discussion: string;
  conclusion: string;
  keywords: string[];
  latex_source: string;
  pdf_path: string | null;
  docx_path: string | null;
  tex_path: string | null;
  validation_report: ValidationReport;
  validation_passed: boolean;
  validation_score: number;
  review_report: ReviewReport;
  review_score: number;
  ready_for_submission: boolean;
}

/* ── Full validation response (from /api/validation/{task_id}) ── */

export interface FullValidationResponse extends ValidationResult {
  ieee_report?: IEEEReport;
  enhancement_scores?: EnhancementScores;
}

/* ── Pipeline steps for live dashboard ── */

export type PipelineStage =
  | "pending"
  | "model_selection"
  | "research"
  | "synthesis"
  | "writing"
  | "formatting"
  | "validation"
  | "review"
  | "enhancement"
  | "complete"
  | "failed";

export interface PipelineStep {
  id: string;
  label: string;
  description: string;
}

export const PIPELINE_STEPS: PipelineStep[] = [
  { id: "model_selection", label: "Model Selection",  description: "Selecting available LLM" },
  { id: "research",         label: "Research",         description: "Fetching arXiv papers" },
  { id: "writing",          label: "Writing",          description: "Generating sections" },
  { id: "formatting",       label: "Formatting",       description: "Building IEEE LaTeX" },
  { id: "validation",       label: "Validation",       description: "Checking IEEE compliance" },
  { id: "review",           label: "Review",           description: "Final quality review" },
  { id: "complete",         label: "Complete",         description: "Paper ready" },
];

/* ── Available models ── */

export interface ModelOption {
  value: string;
  label: string;
  tier: "free" | "paid";
}

export const MODELS: ModelOption[] = [
  { value: "free", label: "Auto (OpenRouter Free)", tier: "free" },
  { value: "meta-llama/llama-3.1-8b-instruct:free", label: "Llama 3.1 8B (Free)", tier: "free" },
  { value: "mistralai/mistral-7b-instruct:free", label: "Mistral 7B (Free)", tier: "free" },
  { value: "google/gemma-2-9b-it:free", label: "Gemma 2 9B (Free)", tier: "free" },
  { value: "qwen/qwen-2.5-7b-instruct:free", label: "Qwen 2.5 7B (Free)", tier: "free" },
  { value: "openai/gpt-4-turbo", label: "GPT-4 Turbo", tier: "paid" },
  { value: "anthropic/claude-3.5-sonnet", label: "Claude 3.5 Sonnet", tier: "paid" },
];

/* ── Paper sections ── */

export const IEEE_SECTIONS = [
  "Abstract",
  "Introduction",
  "Related Work",
  "Proposed Methodology",
  "Implementation & Results",
  "Results & Discussion",
  "Conclusion",
  "References",
] as const;

export type IEEESectionName = (typeof IEEE_SECTIONS)[number];
