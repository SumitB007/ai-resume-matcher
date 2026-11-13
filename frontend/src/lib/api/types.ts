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

/** The backend's standard error envelope (app/main.py exception handlers). */
export interface ApiErrorBody {
  error: boolean;
  type: string;
  detail?: string;
  message?: string;
  details?: Array<{ field: string; message: string }>;
}
