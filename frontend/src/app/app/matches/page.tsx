"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowDownRight, ArrowUpRight, Download, GitCompareArrows, Minus } from "lucide-react";
import { useState } from "react";
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
  const [selected, setSelected] = useState<number[]>([]);

  const toggleSelect = (id: number) =>
    setSelected((current) =>
      current.includes(id)
        ? current.filter((x) => x !== id)
        : current.length >= 2
          ? [current[1], id]
          : [...current, id],
    );

  const compared = (matches.data ?? [])
    .filter((m) => selected.includes(m.id))
    .sort((a, b) => +new Date(a.created_at) - +new Date(b.created_at));
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
          <p className="text-muted-foreground">
            Every match you&apos;ve run, newest first. Pick any two to compare —
            two runs against the same job tell the version story.
          </p>
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

      {compared.length === 2 && (
        <ComparePanel older={compared[0]} newer={compared[1]} resumeName={resumeName} jobName={jobName} />
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
              <div className="flex flex-col gap-2">
                <a href={api.matchPdfUrl(match.id)} download className={buttonVariants({ variant: "outline", size: "sm" })}>
                  <Download className="mr-1.5 h-3.5 w-3.5" /> PDF report
                </a>
                <button
                  onClick={() => toggleSelect(match.id)}
                  className={cn(
                    buttonVariants({ variant: selected.includes(match.id) ? "default" : "ghost", size: "sm" }),
                    selected.includes(match.id) && "bg-blue-700 hover:bg-blue-800",
                  )}
                >
                  <GitCompareArrows className="mr-1.5 h-3.5 w-3.5" />
                  {selected.includes(match.id) ? "Selected" : "Compare"}
                </button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ComparePanel({
  older,
  newer,
  resumeName,
  jobName,
}: {
  older: NonNullable<ReturnType<typeof api.listMatches> extends Promise<infer T> ? T : never>[number];
  newer: NonNullable<ReturnType<typeof api.listMatches> extends Promise<infer T> ? T : never>[number];
  resumeName: (id: number) => string;
  jobName: (id: number) => string;
}) {
  const sameJob = older.job_id === newer.job_id;
  const delta = (newer.overall_score ?? 0) - (older.overall_score ?? 0);
  const olderMissing = new Set(older.missing_keywords ?? []);
  const newerMissing = new Set(newer.missing_keywords ?? []);
  const resolved = [...olderMissing].filter((s) => !newerMissing.has(s));
  const stillMissing = [...olderMissing].filter((s) => newerMissing.has(s));
  const newGaps = [...newerMissing].filter((s) => !olderMissing.has(s));

  return (
    <Card className="border-blue-200 bg-blue-50/50">
      <CardContent className="space-y-4 py-5">
        <div className="flex flex-wrap items-center gap-3">
          <p className="font-semibold">
            {sameJob ? "Version story" : "Side by side"} — {jobName(older.job_id)}
            {!sameJob && <span className="text-muted-foreground"> vs {jobName(newer.job_id)}</span>}
          </p>
          {delta > 0 ? (
            <Badge className="bg-emerald-600">
              <ArrowUpRight className="mr-1 h-3.5 w-3.5" /> +{delta.toFixed(1)} pts
            </Badge>
          ) : delta < 0 ? (
            <Badge variant="destructive">
              <ArrowDownRight className="mr-1 h-3.5 w-3.5" /> {delta.toFixed(1)} pts
            </Badge>
          ) : (
            <Badge variant="secondary">
              <Minus className="mr-1 h-3.5 w-3.5" /> no change
            </Badge>
          )}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            { label: "Earlier", match: older },
            { label: "Later", match: newer },
          ].map(({ label, match }) => (
            <div key={label} className="rounded-lg border bg-white p-3 text-sm">
              <p className="font-medium">
                {label} · {Math.round(match.overall_score ?? 0)}%
              </p>
              <p className="text-xs text-muted-foreground">
                {resumeName(match.resume_id)} · {new Date(match.created_at).toLocaleString()} ·
                semantic {Math.round(match.similarity_score ?? 0)}% · keywords{" "}
                {Math.round(match.keyword_score ?? 0)}%
              </p>
            </div>
          ))}
        </div>
        {sameJob && (
          <div className="space-y-2 text-sm">
            {resolved.length > 0 && (
              <p>
                <span className="font-medium text-emerald-700">Gaps closed:</span>{" "}
                {resolved.join(", ")}
              </p>
            )}
            {stillMissing.length > 0 && (
              <p>
                <span className="font-medium">Still missing:</span> {stillMissing.join(", ")}
              </p>
            )}
            {newGaps.length > 0 && (
              <p>
                <span className="font-medium text-red-700">New gaps:</span> {newGaps.join(", ")}
              </p>
            )}
            {resolved.length === 0 && stillMissing.length === 0 && newGaps.length === 0 && (
              <p className="text-muted-foreground">Identical skill coverage in both runs.</p>
            )}
          </div>
        )}
        {!sameJob && (
          <p className="text-xs text-muted-foreground">
            Different jobs — scores aren&apos;t directly comparable, but the
            missing-skill lists still show what each role asks for.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
