// Types mirroring the FastAPI backend's Pydantic schemas (app/schemas/*).
// Kept hand-written and small on purpose: the backend OpenAPI document is the
// contract; if a schema changes there, change it here too.

export interface User {
  id: number;
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

/** The backend's standard error envelope (app/main.py exception handlers). */
export interface ApiErrorBody {
  error: boolean;
  type: string;
  detail?: string;
  message?: string;
  details?: Array<{ field: string; message: string }>;
}
