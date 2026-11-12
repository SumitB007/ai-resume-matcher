"use client";

import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import Link from "next/link";

import { ScoreDial } from "@/components/score-dial";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";

export default function MatchesPage() {
  const matches = useQuery({ queryKey: ["matches"], queryFn: () => api.listMatches() });
  const resumes = useQuery({ queryKey: ["resumes"], queryFn: api.listResumes });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.listJobs });

  const resumeName = (id: number) =>
    resumes.data?.find((r) => r.id === id)?.file_name ?? `Resume #${id}`;
  const jobName = (id: number) => {
    const job = jobs.data?.find((j) => j.id === id);
    if (!job) return `Job #${id}`;
    return job.company ? `${job.title ?? "Job"} · ${job.company}` : (job.title ?? `Job #${id}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Match History</h1>
          <p className="text-muted-foreground">Every match you&apos;ve run, newest first.</p>
        </div>
        <Link href="/app/match" className={cn(buttonVariants(), "bg-blue-700 hover:bg-blue-800")}>
          Run a new match
        </Link>
      </div>

      {matches.isLoading && <Skeleton className="h-40" />}

      {matches.data?.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No matches yet — your results will appear here after your first run.
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {matches.data?.map((match) => (
          <Card key={match.id}>
            <CardContent className="flex flex-wrap items-center gap-5 py-4">
              <ScoreDial score={match.overall_score ?? 0} size={72} label="" />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">
                  {resumeName(match.resume_id)} <span className="text-muted-foreground">vs</span>{" "}
                  {jobName(match.job_id)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {new Date(match.created_at).toLocaleString()} · Semantic{" "}
                  {Math.round(match.similarity_score ?? 0)}% · Keywords{" "}
                  {Math.round(match.keyword_score ?? 0)}%
                </p>
                {(match.missing_keywords ?? []).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    <span className="text-xs text-muted-foreground">Missing:</span>
                    {(match.missing_keywords ?? []).slice(0, 6).map((skill) => (
                      <Badge key={skill} variant="secondary" className="bg-red-50 text-[11px] text-red-800">
                        {skill}
                      </Badge>
                    ))}
                    {(match.missing_keywords ?? []).length > 6 && (
                      <Badge variant="outline" className="text-[11px]">
                        +{(match.missing_keywords ?? []).length - 6} more
                      </Badge>
                    )}
                  </div>
                )}
              </div>
              <a href={api.matchPdfUrl(match.id)} download className={buttonVariants({ variant: "outline", size: "sm" })}>
                <Download className="mr-1.5 h-3.5 w-3.5" /> PDF report
              </a>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
