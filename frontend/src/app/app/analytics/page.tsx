"use client";

// Analytics (Phase 6) — progress views over the pre-existing backend:
// GET /analytics/resume-progress/{job_id} and /analytics/resumes/{id}/progress.
// The story these endpoints tell is iteration: run a match, improve the
// resume, run it again — did the score move, and which gaps closed?

import { useQuery } from "@tanstack/react-query";
import { ArrowDownRight, ArrowUpRight, Minus, TrendingUp } from "lucide-react";
import { useState } from "react";

import { ScoreDial } from "@/components/score-dial";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";

function ImprovementBadge({ value }: { value: number | null }) {
  if (value == null) return null;
  if (value > 0)
    return (
      <Badge className="bg-emerald-600">
        <ArrowUpRight className="mr-1 h-3.5 w-3.5" /> +{value.toFixed(1)} pts
      </Badge>
    );
  if (value < 0)
    return (
      <Badge variant="destructive">
        <ArrowDownRight className="mr-1 h-3.5 w-3.5" /> {value.toFixed(1)} pts
      </Badge>
    );
  return (
    <Badge variant="secondary">
      <Minus className="mr-1 h-3.5 w-3.5" /> no change
    </Badge>
  );
}

function JobProgress() {
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.listJobs });
  const [jobId, setJobId] = useState<string>("");
  const progress = useQuery({
    queryKey: ["resume-progress", jobId],
    queryFn: () => api.resumeProgress(Number(jobId)),
    enabled: jobId !== "",
  });

  const data = progress.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <TrendingUp className="h-4 w-4 text-blue-700" /> Progress against one job
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Every version you&apos;ve matched against this job, in order — the
          improvement story, with the skills you closed along the way.
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        <Select value={jobId} onValueChange={(v) => setJobId(v ?? "")}>
          <SelectTrigger className="max-w-md">
            <SelectValue placeholder="Pick a saved job" />
          </SelectTrigger>
          <SelectContent>
            {(jobs.data ?? []).map((job) => (
              <SelectItem key={job.id} value={String(job.id)}>
                {job.title ?? "Untitled job"}
                {job.company ? ` · ${job.company}` : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {progress.isLoading && <Skeleton className="h-32" />}
        {data && data.total_evaluations === 0 && (
          <p className="text-sm text-muted-foreground">
            No matches against this job yet — run one from the matcher and
            this timeline starts.
          </p>
        )}
        {data && data.total_evaluations > 0 && (
          <>
            <div className="flex flex-wrap items-center gap-6">
              <div className="text-center">
                <ScoreDial score={data.initial_score ?? 0} size={84} label="first" />
              </div>
              <div className="text-2xl text-muted-foreground">→</div>
              <div className="text-center">
                <ScoreDial score={data.latest_score ?? 0} size={84} label="latest" />
              </div>
              <div className="space-y-1">
                <ImprovementBadge value={data.score_improvement} />
                <p className="text-xs text-muted-foreground">
                  {data.total_evaluations} evaluations · average{" "}
                  {data.average_score != null ? `${Math.round(data.average_score)}%` : "—"}
                </p>
              </div>
            </div>

            {data.skills_gained.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-medium">Skills gained since the first version</p>
                <div className="flex flex-wrap gap-1.5">
                  {data.skills_gained.map((skill) => (
                    <Badge key={skill} className="bg-emerald-600">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-2">
              {data.timeline.map((entry) => (
                <div
                  key={entry.match_id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
                >
                  <span>
                    {entry.resume_file_name ?? `Resume #${entry.resume_id}`}
                    <span className="ml-2 text-xs text-muted-foreground">
                      {new Date(entry.created_at).toLocaleString()}
                    </span>
                  </span>
                  <span className="flex items-center gap-2">
                    {(entry.missing_keywords ?? []).length > 0 && (
                      <span className="text-xs text-muted-foreground">
                        missing: {(entry.missing_keywords ?? []).slice(0, 3).join(", ")}
                        {(entry.missing_keywords ?? []).length > 3 ? "…" : ""}
                      </span>
                    )}
                    <Badge variant={entry.overall_score >= 75 ? "default" : "secondary"}>
                      {Math.round(entry.overall_score)}%
                    </Badge>
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ResumeSummary() {
  const resumes = useQuery({ queryKey: ["resumes"], queryFn: api.listResumes });
  const [resumeId, setResumeId] = useState<string>("");
  const summary = useQuery({
    queryKey: ["resume-evaluations", resumeId],
    queryFn: () => api.resumeEvaluations(Number(resumeId)),
    enabled: resumeId !== "",
  });
  const data = summary.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">One resume across all its jobs</CardTitle>
        <p className="text-sm text-muted-foreground">
          Where this resume is strong, where it struggles — by job.
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        <Select value={resumeId} onValueChange={(v) => setResumeId(v ?? "")}>
          <SelectTrigger className="max-w-md">
            <SelectValue placeholder="Pick a resume" />
          </SelectTrigger>
          <SelectContent>
            {(resumes.data ?? []).map((resume) => (
              <SelectItem key={resume.id} value={String(resume.id)}>
                {resume.file_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {summary.isLoading && <Skeleton className="h-32" />}
        {data && data.total_jobs_matched === 0 && (
          <p className="text-sm text-muted-foreground">
            This resume hasn&apos;t been matched yet.
          </p>
        )}
        {data && data.total_jobs_matched > 0 && (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              {[
                { label: "Average", value: data.average_score },
                { label: "Highest", value: data.highest_score },
                { label: "Lowest", value: data.lowest_score },
              ].map((stat) => (
                <div key={stat.label} className="rounded-lg border p-3 text-center">
                  <div className="text-xl font-bold">
                    {stat.value != null ? `${Math.round(stat.value)}%` : "—"}
                  </div>
                  <div className="text-xs text-muted-foreground">{stat.label}</div>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              {data.matches.map((match) => (
                <div
                  key={match.job_id}
                  className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
                >
                  <span>
                    {match.job_title ?? `Job #${match.job_id}`}
                    {match.job_company ? (
                      <span className="text-muted-foreground"> · {match.job_company}</span>
                    ) : null}
                  </span>
                  <Badge variant={match.overall_score >= 75 ? "default" : "secondary"}>
                    {Math.round(match.overall_score)}%
                  </Badge>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground">
          Progress over time — the point of iterating on a resume, made visible.
        </p>
      </div>
      <JobProgress />
      <ResumeSummary />
    </div>
  );
}
