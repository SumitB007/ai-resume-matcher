"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2, RefreshCw, ScanSearch, Sparkles } from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";

import { AtsResultView } from "@/components/ats-result";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";
import type { AtsCheckResult } from "@/lib/api/types";

export default function ResumesPage() {
  const queryClient = useQueryClient();
  const resumes = useQuery({ queryKey: ["resumes"], queryFn: api.listResumes });

  const [atsResults, setAtsResults] = useState<Record<number, AtsCheckResult>>({});
  const [expandedAts, setExpandedAts] = useState<number | null>(null);
  const [expandedRecs, setExpandedRecs] = useState<number | null>(null);

  const atsCheck = useMutation({
    mutationFn: (id: number) => api.runAtsCheck(id),
    onSuccess: (result, id) => {
      setAtsResults((current) => ({ ...current, [id]: result }));
      setExpandedAts(id);
    },
    onError: () => toast.error("The ATS check failed. Try again."),
  });

  const reprocess = useMutation({
    mutationFn: (id: number) => api.reprocessResume(id),
    onSuccess: () => {
      toast.success("Reprocessing started");
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
    onError: () => toast.error("Could not start reprocessing."),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My Resumes</h1>
          <p className="text-muted-foreground">Every resume you&apos;ve uploaded.</p>
        </div>
        <Link href="/app/match" className={cn(buttonVariants(), "bg-blue-700 hover:bg-blue-800")}>
          Upload in the matcher
        </Link>
      </div>

      {resumes.isLoading && <Skeleton className="h-40" />}

      {resumes.data?.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No resumes yet — upload your first one in the matcher.
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {resumes.data?.map((resume) => (
          <Card key={resume.id}>
            <CardContent className="flex flex-wrap items-center gap-4 py-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-700/10 text-blue-700">
                <FileText className="h-5 w-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">
                  {resume.file_name ?? `Resume #${resume.id}`}
                </p>
                <p className="text-xs text-muted-foreground">
                  Uploaded {new Date(resume.created_at).toLocaleDateString()} ·{" "}
                  {resume.parsed_skills?.length ?? 0} skills detected
                </p>
                {resume.parsed_skills && resume.parsed_skills.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {resume.parsed_skills.slice(0, 12).map((skill) => (
                      <Badge key={skill} variant="secondary" className="text-[11px]">
                        {skill}
                      </Badge>
                    ))}
                    {resume.parsed_skills.length > 12 && (
                      <Badge variant="outline" className="text-[11px]">
                        +{resume.parsed_skills.length - 12} more
                      </Badge>
                    )}
                  </div>
                )}
              </div>
              <Badge variant={resume.status === "completed" ? "secondary" : "outline"}>
                {resume.status}
              </Badge>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (atsResults[resume.id]) {
                    setExpandedAts(expandedAts === resume.id ? null : resume.id);
                  } else {
                    atsCheck.mutate(resume.id);
                  }
                }}
                disabled={atsCheck.isPending}
              >
                {atsCheck.isPending ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ScanSearch className="mr-1.5 h-3.5 w-3.5" />
                )}
                {atsResults[resume.id]
                  ? `ATS ${Math.round(atsResults[resume.id].score)}%`
                  : "ATS check"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setExpandedRecs(expandedRecs === resume.id ? null : resume.id)
                }
              >
                <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                Best-fit jobs
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => reprocess.mutate(resume.id)}
                disabled={reprocess.isPending}
              >
                {reprocess.isPending ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                )}
                Reprocess
              </Button>
            </CardContent>
            {expandedAts === resume.id && atsResults[resume.id] && (
              <CardContent className="border-t pt-5">
                <AtsResultView result={atsResults[resume.id]} />
              </CardContent>
            )}
            {expandedRecs === resume.id && (
              <CardContent className="border-t pt-5">
                <RecommendationsPanel resumeId={resume.id} />
              </CardContent>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

function RecommendationsPanel({ resumeId }: { resumeId: number }) {
  const recs = useQuery({
    queryKey: ["recommendations", resumeId],
    queryFn: () => api.resumeRecommendations(resumeId, 5),
  });

  if (recs.isLoading) return <Skeleton className="h-24" />;
  if (recs.isError)
    return (
      <p className="text-sm text-muted-foreground">
        Couldn&apos;t rank your saved jobs right now. Try again in a moment.
      </p>
    );
  const data = recs.data;
  if (!data || data.recommendations.length === 0)
    return (
      <p className="text-sm text-muted-foreground">
        No saved jobs to rank yet — add a job description and this resume gets
        a best-fit list.
      </p>
    );

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Ranked from the {data.total_jobs_evaluated} job
        {data.total_jobs_evaluated === 1 ? "" : "s"} you&apos;ve saved — your
        own shortlist, not a job board.
      </p>
      {data.recommendations.map((rec) => (
        <div key={rec.job_id} className="rounded-lg border p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="font-medium">
              {rec.title ?? `Job #${rec.job_id}`}
              {rec.company ? (
                <span className="text-muted-foreground"> · {rec.company}</span>
              ) : null}
            </p>
            <Badge variant={rec.overall_score >= 75 ? "default" : "secondary"}>
              {Math.round(rec.overall_score)}% fit
            </Badge>
          </div>
          {rec.matching_skills.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {rec.matching_skills.slice(0, 8).map((skill) => (
                <Badge key={skill} variant="secondary" className="bg-emerald-50 text-[11px] text-emerald-900">
                  {skill}
                </Badge>
              ))}
            </div>
          )}
          {rec.missing_skills.length > 0 && (
            <p className="mt-1.5 text-xs text-muted-foreground">
              Missing: {rec.missing_skills.slice(0, 5).join(", ")}
              {rec.missing_skills.length > 5 ? ` +${rec.missing_skills.length - 5} more` : ""}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
