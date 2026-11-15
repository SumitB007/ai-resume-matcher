// Types mirroring the FastAPI backend's Pydantic schemas (app/schemas/*).
// Kept hand-written and small on purpose: the backend OpenAPI document is the
// contract; if a schema changes there, change it here too.

export interface User {
  id: number;
  name: string | null;
  email: string;
  created_at: string;
}

export interface Resume {
  id: number;
  user_id: number;
  raw_text?: string;
  file_name: string | null;
  parsed_skills: string[] | null;
  status: "pending" | "processing" | "completed" | "failed";
  task_id: string | null;
  created_at: string;
}

export interface Job {
  id: number;
  user_id: number;
  raw_text?: string;
  title: string | null;
  company: string | null;
  parsed_skills: string[] | null;
  status: "pending" | "processing" | "completed" | "failed";
  task_id: string | null;
  created_at: string;
}

export interface ItemStatus {
  id: number;
  item_type: "resume" | "job";
  status: string;
  task_id: string | null;
  has_embedding: boolean;
  skills_count: number;
}

export interface SectionScores {
  skills_match: number;
  experience_relevance: number;
  keyword_density: number;
}

export interface Match {
  id: number;
  resume_id: number;
  job_id: number;
  user_id: number;
  similarity_score: number | null;
  keyword_score: number | null;
  overall_score: number | null;
  section_scores: SectionScores | null;
  missing_keywords: string[] | null;
  ai_feedback: string | null;
  created_at: string;
}

export interface MatchListItem {
  id: number;
  resume_id: number;
  job_id: number;
  overall_score: number | null;
  similarity_score: number | null;
  keyword_score: number | null;
  missing_keywords: string[] | null;
  created_at: string;
}

export interface LlmModel {
  id: string;
  name: string;
  provider: string;
  description: string;
}

export interface ModelList {
  default_model: string;
  recommended_models: LlmModel[];
}

export interface SkillFrequency {
  skill: string;
  count: number;
  percentage: number;
}

// ── Phase 6: analytics + recommendations ──
export interface TimelineEntry {
  match_id: number;
  resume_id: number;
  resume_file_name: string | null;
  overall_score: number;
  similarity_score: number | null;
  keyword_score: number | null;
  missing_keywords: string[] | null;
  created_at: string;
}

export interface ResumeProgress {
  job_id: number;
  job_title: string | null;
  job_company: string | null;
  total_evaluations: number;
  initial_score: number | null;
  latest_score: number | null;
  score_improvement: number | null;
  average_score: number | null;
  skills_gained: string[];
  timeline: TimelineEntry[];
}

export interface ResumeEvaluationsSummary {
  resume_id: number;
  resume_file_name: string | null;
  total_jobs_matched: number;
  average_score: number | null;
  highest_score: number | null;
  lowest_score: number | null;
  matches: Array<{
    job_id: number;
    job_title: string | null;
    job_company: string | null;
    overall_score: number;
    similarity_score: number | null;
    keyword_score: number | null;
    created_at: string;
  }>;
}

export interface JobRecommendationItem {
  job_id: number;
  title: string | null;
  company: string | null;
  similarity_score: number;
  keyword_score: number;
  overall_score: number;
  matching_skills: string[];
  missing_skills: string[];
  created_at: string;
}

export interface JobRecommendations {
  resume_id: number;
  resume_file_name: string | null;
  total_jobs_evaluated: number;
  returned_count: number;
  recommendations: JobRecommendationItem[];
}

export interface DashboardData {
  total_resumes: number;
  total_jobs: number;
  total_matches: number;
  average_match_score: number | null;
  highest_match_score: number | null;
  lowest_match_score: number | null;
  top_missing_skills: SkillFrequency[];
  top_candidate_skills: SkillFrequency[];
  recent_matches: Array<{
    match_id: number;
    resume_id: number;
    resume_file_name: string | null;
    overall_score: number;
    similarity_score: number | null;
    keyword_score: number | null;
    missing_keywords: string[] | null;
    created_at: string;
  }>;
}

export interface AtsCheckItem {
  id: string;
  group: "file_parse" | "contact" | "sections" | "content" | "skills" | "length_format";
  label: string;
  status: "pass" | "warn" | "fail";
  detail: string;
  weight: number;
}

export interface AtsCheckResult {
  id: number | null;
  resume_id: number | null;
  score: number;
  groups: Record<string, number>;
  checks: AtsCheckItem[];
  word_count: number;
  skills_found: string[];
  created_at: string | null;
}

// ── Builder documents (mirror app/services/document_service.py) ──

export interface DocPersonal {
  full_name: string;
  title: string;
  email: string;
  phone: string;
  location: string;
  links: string[];
}

export interface DocExperience {
  role: string;
  company: string;
  location: string;
  start: string;
  end: string;
  current: boolean;
  bullets: string[];
}

export interface DocEducation {
  school: string;
  degree: string;
  field: string;
  start: string;
  end: string;
}

export interface DocSkillGroup {
  label: string;
  items: string[];
}

export interface DocProject {
  name: string;
  description: string;
  bullets: string[];
}

export interface DocCustomSection {
  title: string;
  items: string[];
}

export interface DocumentContent {
  personal: DocPersonal;
  summary: string;
  experience: DocExperience[];
  education: DocEducation[];
  skills: { groups: DocSkillGroup[] };
  projects: DocProject[];
  certifications: string[];
  languages: string[];
  custom_sections: DocCustomSection[];
}

export interface DocTheme {
  accent?: string;
  font?: "sans" | "serif";
  density?: "normal" | "compact";
}

export interface ResumeDocument {
  id: number;
  title: string;
  template_id: string;
  theme: DocTheme;
  content: DocumentContent;
  resume_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface ResumeDocumentListItem {
  id: number;
  title: string;
  template_id: string;
  resume_id: number | null;
  created_at: string;
  updated_at: string;
}

export const TEMPLATE_IDS = [
  "classic",
  "modern",
  "compact-tech",
  "sidebar",
  "minimal",
  "graduate",
] as const;

export const TEMPLATE_LABELS: Record<string, string> = {
  classic: "Classic",
  modern: "Modern",
  "compact-tech": "Compact Tech",
  sidebar: "Two-Column Sidebar",
  minimal: "Minimal",
  graduate: "Graduate",
};

export const EMPTY_CONTENT: DocumentContent = {
  personal: { full_name: "", title: "", email: "", phone: "", location: "", links: [] },
  summary: "",
  experience: [],
  education: [],
  skills: { groups: [] },
  projects: [],
  certifications: [],
  languages: [],
  custom_sections: [],
};

// ── Cover letters (mirror app/schemas/cover_letter.py) ──

export interface LetterSender {
  name: string;
  title: string;
  email: string;
  phone: string;
  location: string;
}

export interface LetterContent {
  sender: LetterSender;
  recipient: { name: string; company: string; role: string };
  date: string;
  greeting: string;
  paragraphs: string[];
  closing: string;
  signature_name: string;
}

export interface CoverLetter {
  id: number;
  title: string;
  template_id: string;
  theme: DocTheme;
  content: LetterContent;
  resume_id: number | null;
  resume_document_id: number | null;
  job_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CoverLetterListItem {
  id: number;
  title: string;
  template_id: string;
  resume_id: number | null;
  job_id: number | null;
  created_at: string;
  updated_at: string;
}

export const LETTER_TONES = ["professional", "enthusiastic", "concise"] as const;

// ── Phase 15 generators + tailoring (mirror app/schemas/generator.py) ──

export interface SummaryVariant {
  label: string;
  text: string;
}

export interface SkillGroupOut {
  name: string;
  skills: string[];
}

export interface TailorSuggestion {
  id: string;
  type: "add_skill" | "rewrite_bullet" | "summary" | string;
  skill?: string | null;
  group?: string | null;
  experience_index?: number | null;
  bullet_index?: number | null;
  original: string;
  proposed: string;
}

export interface TailorResult {
  overall_score: number;
  similarity_score: number;
  keyword_score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  suggestions: TailorSuggestion[];
  model_used: string;
  fallback_used: boolean;
}

/** The backend's standard error envelope (app/main.py exception handlers). */
export interface ApiErrorBody {
  error: boolean;
  type: string;
  detail?: string;
  message?: string;
  details?: Array<{ field: string; message: string }>;
}
