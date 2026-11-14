"use client";

// Shared ATS result renderer — used by the public checker page and the
// signed-in resumes page so both show identical, honestly-labelled results.
// The score is an ATS *readiness* score, never a job-match score; the
// explainer line under the dial keeps that distinction in front of the user.

import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

import { ScoreDial } from "@/components/score-dial";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { AtsCheckResult } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export const ATS_GROUP_LABELS: Record<string, string> = {
  file_parse: "File & parsing",
  contact: "Contact & links",
  sections: "Sections",
  content: "Content quality",
  skills: "Skills & keywords",
  length_format: "Length & format",
};

const GROUP_ORDER = ["file_parse", "contact", "sections", "content", "skills", "length_format"];

const statusIcon = {
  pass: <CheckCircle2 className="h-4.5 w-4.5 shrink-0 text-emerald-600" />,
  warn: <AlertTriangle className="h-4.5 w-4.5 shrink-0 text-amber-500" />,
  fail: <XCircle className="h-4.5 w-4.5 shrink-0 text-red-500" />,
};

export function AtsResultView({ result }: { result: AtsCheckResult }) {
  const failCount = result.checks.filter((c) => c.status === "fail").length;
  const warnCount = result.checks.filter((c) => c.status === "warn").length;

  return (
    <div className="space-y-8">
      <div className="flex flex-col items-center gap-8 sm:flex-row">
        <div className="text-center">
          <ScoreDial score={result.score} label="ATS readiness" />
          <p className="mx-auto mt-2 max-w-55 text-xs text-muted-foreground">
            How well this resume parses and reads to an ATS — not a match score
            for a specific job.
          </p>
        </div>
        <div className="w-full flex-1 space-y-3">
          {GROUP_ORDER.map((group) => (
            <div key={group}>
              <div className="mb-1 flex justify-between text-sm">
                <span>{ATS_GROUP_LABELS[group]}</span>
                <span className="font-medium">{Math.round(result.groups[group] ?? 0)}%</span>
              </div>
              <Progress value={result.groups[group] ?? 0} />
            </div>
          ))}
          <p className="pt-1 text-xs text-muted-foreground">
            {result.checks.length} checks · {result.word_count} words ·{" "}
            {result.skills_found.length} skills recognised
            {failCount > 0 && <> · <span className="text-red-600">{failCount} to fix</span></>}
            {warnCount > 0 && <> · <span className="text-amber-600">{warnCount} to improve</span></>}
          </p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {GROUP_ORDER.map((group) => {
          const items = result.checks.filter((c) => c.group === group);
          if (items.length === 0) return null;
          return (
            <div key={group}>
              <h3 className="mb-2 text-sm font-semibold">{ATS_GROUP_LABELS[group]}</h3>
              <ul className="space-y-2.5">
                {items.map((check) => (
                  <li key={check.id} className="flex gap-2.5">
                    {statusIcon[check.status]}
                    <div>
                      <p
                        className={cn(
                          "text-sm font-medium",
                          check.status === "fail" && "text-red-700",
                        )}
                      >
                        {check.label}
                      </p>
                      <p className="text-xs text-muted-foreground">{check.detail}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {result.skills_found.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">
            Skills recognised ({result.skills_found.length})
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {result.skills_found.map((skill) => (
              <Badge key={skill} variant="secondary">
                {skill}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
