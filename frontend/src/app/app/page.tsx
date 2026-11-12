"use client";

// Dashboard — a thin v1 over GET /analytics/dashboard (roadmap Phase 1 §5.3).
// The richer analytics page (progress timelines, recommendations) is roadmap
// Phase 6 and reuses the same endpoints.

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Briefcase, FileText, Gauge, Trophy } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-6">
        <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-blue-700/10 text-blue-700">
          <Icon className="h-5 w-5" />
        </span>
        <div>
          <div className="text-2xl font-bold">{value}</div>
          <div className="text-sm text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const dashboard = useQuery({
    queryKey: ["analytics", "dashboard"],
    queryFn: api.dashboard,
  });

  const data = dashboard.data;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Your resumes, jobs, and match progress at a glance.
          </p>
        </div>
        <Link href="/app/match" className={cn(buttonVariants(), "bg-blue-700 hover:bg-blue-800")}>
          Run a new match <ArrowRight className="ml-1 h-4 w-4" />
        </Link>
      </div>

      {dashboard.isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      )}

      {dashboard.isError && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            Couldn&apos;t load your dashboard.{" "}
            <button
              className="font-medium text-blue-700 hover:underline"
              onClick={() => dashboard.refetch()}
            >
              Try again
            </button>
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={FileText} label="Resumes" value={String(data.total_resumes)} />
            <StatCard icon={Briefcase} label="Job descriptions" value={String(data.total_jobs)} />
            <StatCard icon={Gauge} label="Matches run" value={String(data.total_matches)} />
            <StatCard
              icon={Trophy}
              label="Best score"
              value={
                data.highest_match_score != null
                  ? `${Math.round(data.highest_match_score)}%`
                  : "—"
              }
            />
          </div>

          {data.total_matches === 0 ? (
            <Card>
              <CardContent className="py-10 text-center">
                <p className="font-medium">No matches yet</p>
                <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
                  Upload a resume, paste a job description, and run your first
                  match to see your score, missing skills, and AI suggestions.
                </p>
                <Link href="/app/match" className={cn(buttonVariants(), "mt-5 bg-blue-700 hover:bg-blue-800")}>
                  Go to the matcher
                </Link>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Skills jobs keep asking for (and you&apos;re missing)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {data.top_missing_skills.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No recurring gaps — nice work.
                    </p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {data.top_missing_skills.map((skill) => (
                        <Badge key={skill.skill} variant="secondary">
                          {skill.skill} · {skill.count}×
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Recent matches</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.recent_matches.map((match) => (
                    <div
                      key={match.match_id}
                      className="flex items-center justify-between gap-3 text-sm"
                    >
                      <span className="truncate">
                        {match.resume_file_name ?? `Resume #${match.resume_id}`}
                      </span>
                      <Badge variant={match.overall_score >= 75 ? "default" : "secondary"}>
                        {Math.round(match.overall_score)}%
                      </Badge>
                    </div>
                  ))}
                  <Link href="/app/matches" className={cn(buttonVariants({ variant: "outline", size: "sm" }), "mt-2")}>
                    View all matches
                  </Link>
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}
