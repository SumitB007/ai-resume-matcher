"use client";

// Matcher workspace — the product's hero flow (roadmap Phase 1 §5.2):
//   pick/upload a resume → pick/paste a job description → run the match →
//   score breakdown, missing skills, streamed AI feedback, PDF report.
//
// Backend behaviours this page is built around:
//  · uploads/jobs return before processing finishes → status is polled
//    until the embedding exists (POST /resumes, GET /resumes/{id}/status)
//  · repeat matches are Redis-cached and return instantly — no fake delay
//  · matches are rate-limited (10/min) → 429 shows a calm message (ApiError)
//  · AI feedback streams token-by-token over SSE

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileUp,
  Loader2,
  Play,
  RefreshCw,
  Sparkles,
  Wand2,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { FeedbackView } from "@/components/feedback-view";
import { ScoreDial } from "@/components/score-dial";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api, streamMatchFeedback } from "@/lib/api/client";
import type { Match } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const SAMPLE_JD = `Senior Python Backend Developer
Company: TechCorp Inc.
Location: Remote

We are looking for a Senior Python Backend Developer to join our team.

Requirements:
- 5+ years of experience with Python
- Strong experience with FastAPI or Django
- PostgreSQL and database design expertise
- Experience with Redis for caching and message queuing
- Docker and Kubernetes knowledge
- Familiarity with CI/CD pipelines
- Experience with AWS or GCP
- Strong understanding of RESTful API design
- Unit testing with pytest

Nice to have:
- GraphQL experience
- Terraform for infrastructure as code
- Experience with Kafka or RabbitMQ`;

function errorText(error: unknown): string {
  return error instanceof ApiError
    ? error.detail
    : "Something went wrong. Try again.";
}

function ProcessingBadge({ ready, failed }: { ready: boolean; failed?: boolean }) {
  if (failed)
    return (
      <Badge variant="destructive" className="gap-1">
        <AlertCircle className="h-3 w-3" /> Processing failed
      </Badge>
    );
  if (ready)
    return (
      <Badge variant="secondary" className="gap-1">
        <CheckCircle2 className="h-3 w-3 text-emerald-600" /> Ready
      </Badge>
    );
  return (
    <Badge variant="secondary" className="gap-1">
      <Loader2 className="h-3 w-3 animate-spin" /> Processing…
    </Badge>
  );
}

export default function MatchPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [resumeId, setResumeId] = useState<number | null>(null);
  const [jobId, setJobId] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const [jobTitle, setJobTitle] = useState("");
  const [jobCompany, setJobCompany] = useState("");
  const [jobText, setJobText] = useState("");

  const [match, setMatch] = useState<Match | null>(null);
  const [streamedFeedback, setStreamedFeedback] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [model, setModel] = useState<string>("");

  const [bullet, setBullet] = useState("");
  const [rewrite, setRewrite] = useState<string | null>(null);

  const resumes = useQuery({ queryKey: ["resumes"], queryFn: api.listResumes });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.listJobs });
  const models = useQuery({ queryKey: ["ai", "models"], queryFn: api.listModels });

  const resumeStatus = useQuery({
    queryKey: ["resume-status", resumeId],
    queryFn: () => api.resumeStatus(resumeId!),
    enabled: resumeId != null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1500;
    },
  });
  const jobStatus = useQuery({
    queryKey: ["job-status", jobId],
    queryFn: () => api.jobStatus(jobId!),
    enabled: jobId != null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1500;
    },
  });

  const selectedResume = resumes.data?.find((r) => r.id === resumeId) ?? null;
  const selectedJob = jobs.data?.find((j) => j.id === jobId) ?? null;
  const resumeReady =
    resumeStatus.data?.has_embedding === true ||
    resumeStatus.data?.status === "completed";
  const jobReady =
    jobStatus.data?.has_embedding === true || jobStatus.data?.status === "completed";

  const matchedSkills = useMemo(() => {
    if (!selectedResume?.parsed_skills || !selectedJob?.parsed_skills) return [];
    const jobSkills = new Set(selectedJob.parsed_skills);
    return selectedResume.parsed_skills.filter((s) => jobSkills.has(s)).sort();
  }, [selectedResume, selectedJob]);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadResume(file),
    onSuccess: (resume) => {
      setResumeId(resume.id);
      setMatch(null);
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      toast.success(`Uploaded ${resume.file_name ?? "resume"} — processing…`);
    },
    onError: (error) => toast.error(errorText(error)),
  });

  function handleFile(file: File | undefined) {
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext !== "pdf" && ext !== "docx") {
      toast.error("Only PDF or DOCX resumes are accepted.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error("That file is over the 10 MB limit.");
      return;
    }
    uploadMutation.mutate(file);
  }

  const createJobMutation = useMutation({
    mutationFn: () =>
      api.createJob(jobText.trim(), jobTitle.trim() || undefined, jobCompany.trim() || undefined),
    onSuccess: (job) => {
      setJobId(job.id);
      setMatch(null);
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Job description saved — processing…");
    },
    onError: (error) => toast.error(errorText(error)),
  });

  const runMutation = useMutation({
    mutationFn: () => api.runMatch(resumeId!, jobId!, true),
    onSuccess: (result) => {
      setMatch(result);
      setStreamedFeedback(null);
      queryClient.invalidateQueries({ queryKey: ["matches"] });
      queryClient.invalidateQueries({ queryKey: ["analytics", "dashboard"] });
    },
    onError: (error) => toast.error(errorText(error)),
  });

  const feedbackMutation = useMutation({
    mutationFn: () => api.regenerateFeedback(match!.id, model || undefined),
    onSuccess: (result) => {
      setMatch((current) =>
        current ? { ...current, ai_feedback: result.ai_feedback } : current,
      );
      setStreamedFeedback(null);
    },
    onError: (error) => toast.error(errorText(error)),
  });

  const rewriteMutation = useMutation({
    mutationFn: () =>
      api.rewriteBullet(bullet.trim(), selectedJob?.raw_text, match?.missing_keywords ?? undefined),
    onSuccess: (result) => setRewrite(result.rewrite_content),
    onError: (error) => toast.error(errorText(error)),
  });

  async function handleStreamFeedback() {
    if (!match) return;
    setIsStreaming(true);
    setStreamedFeedback("");
    try {
      await streamMatchFeedback(
        match.id,
        (token) => setStreamedFeedback((current) => (current ?? "") + token),
        model || undefined,
      );
    } catch (error) {
      toast.error(errorText(error));
    } finally {
      setIsStreaming(false);
    }
  }

  const canRun =
    resumeId != null && jobId != null && resumeReady && jobReady && !runMutation.isPending;
  const feedbackText = streamedFeedback ?? match?.ai_feedback ?? null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Job Matcher</h1>
        <p className="text-muted-foreground">
          Pick a resume and a job description, then run the match.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ── Resume picker ── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">1 · Your resume</CardTitle>
            <CardDescription>Upload a PDF/DOCX or pick one you uploaded before.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                handleFile(e.dataTransfer.files?.[0]);
              }}
              className={cn(
                "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors",
                dragOver ? "border-blue-600 bg-blue-50" : "border-muted-foreground/25 hover:border-blue-400",
              )}
            >
              {uploadMutation.isPending ? (
                <Loader2 className="h-8 w-8 animate-spin text-blue-700" />
              ) : (
                <FileUp className="h-8 w-8 text-blue-700" />
              )}
              <p className="mt-2 text-sm font-medium">
                {uploadMutation.isPending ? "Uploading…" : "Drop your resume here, or click to browse"}
              </p>
              <p className="text-xs text-muted-foreground">PDF or DOCX, up to 10 MB</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx"
                className="hidden"
                onChange={(e) => {
                  handleFile(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </div>

            {resumes.data && resumes.data.length > 0 && (
              <div className="space-y-2">
                <Label>Your resumes</Label>
                <Select
                  value={resumeId != null ? String(resumeId) : undefined}
                  onValueChange={(value) => {
                    setResumeId(Number(value));
                    setMatch(null);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a resume" />
                  </SelectTrigger>
                  <SelectContent>
                    {resumes.data.map((resume) => (
                      <SelectItem key={resume.id} value={String(resume.id)}>
                        {resume.file_name ?? `Resume #${resume.id}`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {resumeId != null && (
              <div className="flex items-center gap-2">
                <ProcessingBadge
                  ready={resumeReady}
                  failed={resumeStatus.data?.status === "failed"}
                />
                {resumeStatus.data && (
                  <span className="text-xs text-muted-foreground">
                    {resumeStatus.data.skills_count} skills detected
                  </span>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Job picker ── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">2 · Job description</CardTitle>
            <CardDescription>Paste a new one, or pick a saved job.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="job-title">Job title (optional)</Label>
                <Input
                  id="job-title"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="Senior Python Developer"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="job-company">Company (optional)</Label>
                <Input
                  id="job-company"
                  value={jobCompany}
                  onChange={(e) => setJobCompany(e.target.value)}
                  placeholder="TechCorp"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="job-text">Description</Label>
              <Textarea
                id="job-text"
                value={jobText}
                onChange={(e) => setJobText(e.target.value)}
                placeholder="Paste the full job description here (at least 50 characters)…"
                rows={7}
              />
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className="text-xs font-medium text-blue-700 hover:underline"
                  onClick={() => {
                    setJobText(SAMPLE_JD);
                    setJobTitle("Senior Python Backend Developer");
                    setJobCompany("TechCorp Inc.");
                  }}
                >
                  Fill with a sample job description
                </button>
                <span className="text-xs text-muted-foreground">{jobText.trim().length} chars</span>
              </div>
            </div>
            <Button
              onClick={() => createJobMutation.mutate()}
              disabled={jobText.trim().length < 50 || createJobMutation.isPending}
              variant="outline"
              className="w-full"
            >
              {createJobMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save this job description
            </Button>

            {jobs.data && jobs.data.length > 0 && (
              <div className="space-y-2">
                <Label>Saved jobs</Label>
                <Select
                  value={jobId != null ? String(jobId) : undefined}
                  onValueChange={(value) => {
                    setJobId(Number(value));
                    setMatch(null);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a job" />
                  </SelectTrigger>
                  <SelectContent>
                    {jobs.data.map((job) => (
                      <SelectItem key={job.id} value={String(job.id)}>
                        {job.title ?? `Job #${job.id}`}
                        {job.company ? ` · ${job.company}` : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {jobId != null && (
              <ProcessingBadge ready={jobReady} failed={jobStatus.data?.status === "failed"} />
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Run ── */}
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-6">
          <Button
            size="lg"
            className="bg-blue-700 px-8 hover:bg-blue-800"
            disabled={!canRun}
            onClick={() => runMutation.mutate()}
          >
            {runMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            {runMutation.isPending ? "Matching…" : "Run match"}
          </Button>
          <p className="text-xs text-muted-foreground">
            {resumeId == null || jobId == null
              ? "Select both a resume and a job description to run a match."
              : !resumeReady || !jobReady
                ? "Waiting for processing to finish (embeddings are generated in the background)…"
                : "Score = 60% semantic fit + 40% keyword coverage. AI feedback is generated with the match."}
          </p>
        </CardContent>
      </Card>

      {/* ── Results ── */}
      {match && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Your match result</CardTitle>
              <CardDescription>
                {selectedResume?.file_name ?? "Resume"} vs{" "}
                {selectedJob?.title ?? "the job"}
                {selectedJob?.company ? ` at ${selectedJob.company}` : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center gap-8 sm:flex-row">
                <ScoreDial score={match.overall_score ?? 0} />
                <div className="w-full flex-1 space-y-4">
                  <div>
                    <div className="mb-1 flex justify-between text-sm">
                      <span>Semantic fit (60%)</span>
                      <span className="font-medium">{Math.round(match.similarity_score ?? 0)}%</span>
                    </div>
                    <Progress value={match.similarity_score ?? 0} />
                  </div>
                  <div>
                    <div className="mb-1 flex justify-between text-sm">
                      <span>Keyword coverage (40%)</span>
                      <span className="font-medium">{Math.round(match.keyword_score ?? 0)}%</span>
                    </div>
                    <Progress value={match.keyword_score ?? 0} />
                  </div>
                  {match.section_scores && (
                    <div className="grid grid-cols-3 gap-3 pt-1 text-center">
                      {(
                        [
                          ["Skills match", match.section_scores.skills_match],
                          ["Experience relevance", match.section_scores.experience_relevance],
                          ["Keyword density", match.section_scores.keyword_density],
                        ] as const
                      ).map(([label, value]) => (
                        <div key={label} className="rounded-lg bg-muted/60 px-2 py-3">
                          <div className="text-lg font-bold">{Math.round(value)}%</div>
                          <div className="text-xs text-muted-foreground">{label}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-8 grid gap-6 md:grid-cols-2">
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-emerald-700">
                    Matched skills ({matchedSkills.length})
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {matchedSkills.length === 0 && (
                      <span className="text-sm text-muted-foreground">None detected yet.</span>
                    )}
                    {matchedSkills.map((skill) => (
                      <Badge key={skill} variant="secondary" className="bg-emerald-50 text-emerald-800">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-red-700">
                    Missing keywords ({match.missing_keywords?.length ?? 0})
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {(match.missing_keywords ?? []).length === 0 && (
                      <span className="text-sm text-muted-foreground">
                        Nothing missing — full keyword coverage.
                      </span>
                    )}
                    {(match.missing_keywords ?? []).map((skill) => (
                      <Badge key={skill} variant="secondary" className="bg-red-50 text-red-800">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                  {(match.missing_keywords ?? []).length > 0 && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      Add these where they&apos;re genuinely true for you — in
                      bullets that show the skill, not just a list.
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                <a href={api.matchPdfUrl(match.id)} download className={buttonVariants({ variant: "outline", size: "sm" })}>
                  <Download className="mr-1.5 h-4 w-4" /> Download PDF report
                </a>
              </div>
            </CardContent>
          </Card>

          {/* ── AI feedback ── */}
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-blue-700" /> AI feedback & suggestions
                  </CardTitle>
                  <CardDescription>
                    Strengths, gaps, and bullet rewrites for this specific job.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Select value={model} onValueChange={(value) => setModel(value ?? "")}>
                    <SelectTrigger className="w-56">
                      <SelectValue placeholder="Default model" />
                    </SelectTrigger>
                    <SelectContent>
                      {(models.data?.recommended_models ?? []).map((m) => (
                        <SelectItem key={m.id} value={m.id}>
                          {m.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {feedbackText ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => feedbackMutation.mutate()}
                      disabled={feedbackMutation.isPending}
                    >
                      {feedbackMutation.isPending ? (
                        <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="mr-1.5 h-4 w-4" />
                      )}
                      Regenerate
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      className="bg-blue-700 hover:bg-blue-800"
                      onClick={handleStreamFeedback}
                      disabled={isStreaming}
                    >
                      {isStreaming ? (
                        <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                      ) : (
                        <Sparkles className="mr-1.5 h-4 w-4" />
                      )}
                      Generate feedback
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {feedbackText ? (
                <FeedbackView text={feedbackText} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  {isStreaming
                    ? "Writing your feedback…"
                    : "No feedback yet for this match — generate it and it will stream in here."}
                </p>
              )}
              {isStreaming && <Loader2 className="mt-3 h-4 w-4 animate-spin text-blue-700" />}
            </CardContent>
          </Card>

          {/* ── Bullet improver ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Wand2 className="h-4 w-4 text-blue-700" /> Improve a bullet point
              </CardTitle>
              <CardDescription>
                Paste one weak bullet — get quantified, keyword-aware rewrites.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                value={bullet}
                onChange={(e) => setBullet(e.target.value)}
                placeholder="e.g. Worked on backend APIs and helped with the database."
                rows={2}
              />
              <Button
                onClick={() => rewriteMutation.mutate()}
                disabled={bullet.trim().length < 10 || rewriteMutation.isPending}
                className="bg-blue-700 hover:bg-blue-800"
              >
                {rewriteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Rewrite this bullet
              </Button>
              {rewrite && (
                <div className="rounded-lg bg-muted/50 p-4">
                  <FeedbackView text={rewrite} />
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
