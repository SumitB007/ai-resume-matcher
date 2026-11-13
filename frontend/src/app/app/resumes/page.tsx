"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";

export default function ResumesPage() {
  const queryClient = useQueryClient();
  const resumes = useQuery({ queryKey: ["resumes"], queryFn: api.listResumes });

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
          </Card>
        ))}
      </div>
    </div>
  );
}
