"use client";

import { useQuery } from "@tanstack/react-query";
import { Briefcase } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";

export default function JobsPage() {
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.listJobs });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Saved Jobs</h1>
          <p className="text-muted-foreground">
            Job descriptions you&apos;ve added for matching.
          </p>
        </div>
        <Link href="/app/match" className={cn(buttonVariants(), "bg-blue-700 hover:bg-blue-800")}>
          Add in the matcher
        </Link>
      </div>

      {jobs.isLoading && <Skeleton className="h-40" />}

      {jobs.data?.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No job descriptions yet — paste your first one in the matcher.
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {jobs.data?.map((job) => (
          <Card key={job.id}>
            <CardContent className="flex flex-wrap items-center gap-4 py-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-700/10 text-blue-700">
                <Briefcase className="h-5 w-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{job.title ?? `Job #${job.id}`}</p>
                <p className="text-xs text-muted-foreground">
                  {job.company ? `${job.company} · ` : ""}
                  Added {new Date(job.created_at).toLocaleDateString()} ·{" "}
                  {job.parsed_skills?.length ?? 0} skills required
                </p>
                {job.parsed_skills && job.parsed_skills.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {job.parsed_skills.slice(0, 12).map((skill) => (
                      <Badge key={skill} variant="secondary" className="text-[11px]">
                        {skill}
                      </Badge>
                    ))}
                    {job.parsed_skills.length > 12 && (
                      <Badge variant="outline" className="text-[11px]">
                        +{job.parsed_skills.length - 12} more
                      </Badge>
                    )}
                  </div>
                )}
              </div>
              <Badge variant={job.status === "completed" ? "secondary" : "outline"}>
                {job.status}
              </Badge>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
