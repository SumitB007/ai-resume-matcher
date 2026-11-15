"use client";

// Tailor-to-a-job panel (Phase 15, roadmap §9.2).
//
// Contract, enforced here: tailoring never edits the master document. The
// first run duplicates it ("… — tailored for {Company}"), switches the
// editor to the copy, and only the copy receives accepted suggestions.
// Every suggestion is accepted or skipped individually; skipping a skill
// carries no penalty language — it's a normal, expected choice.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Crosshair, Loader2, RefreshCw, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ScoreDial } from "@/components/score-dial";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import type { TailorResult, TailorSuggestion } from "@/lib/api/types";
import { useEditorStore } from "@/lib/store/editor-store";

type Decision = "accepted" | "skipped";

export function TailorPanel({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const doc = useEditorStore((s) => s.document);
  const updateContent = useEditorStore((s) => s.updateContent);

  const [jobSource, setJobSource] = useState("");
  const [jobText, setJobText] = useState("");
  const [workingId, setWorkingId] = useState<number | null>(null);
  const [result, setResult] = useState<TailorResult | null>(null);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [preparing, setPreparing] = useState(false);

  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.listJobs });

  const selectedJob =
    jobSource.startsWith("job:")
      ? jobs.data?.find((j) => j.id === Number(jobSource.split(":")[1]))
      : undefined;

  const tailorMutation = useMutation({
    mutationFn: (documentId: number) =>
      api.tailorDocument(documentId, {
        job_id: selectedJob?.id,
        job_text: selectedJob ? undefined : jobText,
        job_title: selectedJob?.title ?? undefined,
      }),
    onSuccess: (data) => {
      setResult(data);
      setDecisions({});
    },
    onError: () => toast.error("Tailoring failed. Try again."),
  });

  if (!doc) return null;
  const isTailoredCopy = doc.title.includes("— tailored for");

  const startTailoring = async () => {
    let targetId = doc.id;
    try {
      setPreparing(true);
      if (!isTailoredCopy) {
        // Duplicate first — the master document is never tailored in place.
        const copy = await api.duplicateDocument(doc.id);
        const forWhom = selectedJob?.company || selectedJob?.title || "this job";
        const renamed = await api.updateDocument(copy.id, {
          title: `${doc.title} — tailored for ${forWhom}`,
        });
        useEditorStore.getState().init(renamed);
        router.replace(`/app/builder/${renamed.id}`);
        queryClient.invalidateQueries({ queryKey: ["documents"] });
        targetId = renamed.id;
        toast.success("Working on a tailored copy — your master resume is untouched.");
      }
      setWorkingId(targetId);
      tailorMutation.mutate(targetId);
    } catch {
      toast.error("Could not prepare the tailored copy.");
    } finally {
      setPreparing(false);
    }
  };

  const recheck = async () => {
    const id = workingId ?? doc.id;
    // Flush pending edits through the editor's autosave path first.
    await new Promise((r) => setTimeout(r, 1400));
    tailorMutation.mutate(id);
  };

  const applySuggestion = (suggestion: TailorSuggestion, decision: Decision) => {
    if (decision === "accepted") {
      if (suggestion.type === "add_skill" && suggestion.skill) {
        const skill = suggestion.skill;
        const groupName = suggestion.group || "Other";
        updateContent((d) => {
          const groups = d.skills.groups;
          const existing = groups.find((g) => g.label === groupName);
          if (existing) {
            if (!existing.items.includes(skill)) existing.items.push(skill);
          } else {
            groups.push({ label: groupName, items: [skill] });
          }
        });
      } else if (
        suggestion.type === "rewrite_bullet" &&
        suggestion.experience_index != null &&
        suggestion.bullet_index != null
      ) {
        const ei = suggestion.experience_index;
        const bi = suggestion.bullet_index;
        updateContent((d) => {
          if (d.experience[ei]?.bullets[bi] !== undefined) {
            d.experience[ei].bullets[bi] = suggestion.proposed;
          }
        });
      } else if (suggestion.type === "summary") {
        updateContent((d) => {
          d.summary = suggestion.proposed;
        });
      }
    }
    setDecisions((prev) => ({ ...prev, [suggestion.id]: decision }));
  };

  const busy = preparing || tailorMutation.isPending;
  const canStart = selectedJob != null || jobText.trim().length >= 30;

  return (
    <Card className="border-blue-700/40">
      <CardHeader className="flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Crosshair className="h-4 w-4 text-blue-700" /> Tailor to a job
        </CardTitle>
        <Button size="icon" variant="ghost" className="h-8 w-8" onClick={onClose} aria-label="Close tailor panel">
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {!result && (
          <>
            <div className="grid gap-3 sm:grid-cols-[240px_1fr]">
              <div className="space-y-1.5">
                <Label className="text-xs">Job</Label>
                <Select value={jobSource} onValueChange={(v) => setJobSource(v ?? "")}>
                  <SelectTrigger>
                    <SelectValue placeholder="Saved job or paste" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="paste">Paste a job description…</SelectItem>
                    {(jobs.data ?? []).map((j) => (
                      <SelectItem key={j.id} value={`job:${j.id}`}>
                        {j.title ?? "Untitled"} {j.company ? `· ${j.company}` : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {jobSource === "paste" && (
                <Textarea
                  value={jobText}
                  onChange={(e) => setJobText(e.target.value)}
                  rows={4}
                  placeholder="Paste the job description…"
                />
              )}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button className="bg-blue-700 hover:bg-blue-800" onClick={startTailoring} disabled={!canStart || busy}>
                {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Crosshair className="mr-2 h-4 w-4" />}
                {isTailoredCopy ? "Run tailoring" : "Duplicate & tailor"}
              </Button>
              <p className="text-xs text-muted-foreground">
                {isTailoredCopy
                  ? "This is already a tailored copy — suggestions apply here."
                  : "Your master resume stays untouched; suggestions land on a copy."}{" "}
                Suggestions only rephrase your own facts — skip anything that isn't true for you.
              </p>
            </div>
          </>
        )}

        {result && (
          <>
            <div className="flex flex-wrap items-center gap-5">
              <ScoreDial score={result.overall_score} size={84} label="Match" />
              <div className="space-y-1 text-sm">
                <p>
                  Semantic <strong>{Math.round(result.similarity_score)}%</strong> · Keyword{" "}
                  <strong>{Math.round(result.keyword_score)}%</strong>
                </p>
                <p className="text-muted-foreground">
                  {result.matched_keywords.length} skills matched ·{" "}
                  {result.missing_keywords.length} missing
                  {result.fallback_used ? " · offline suggestions (template-based)" : ""}
                </p>
                <Button size="sm" variant="outline" onClick={recheck} disabled={busy}>
                  {busy ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="mr-1.5 h-3.5 w-3.5" />}
                  Re-check score
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              {result.suggestions.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No suggestions — this document already covers the job well.
                </p>
              )}
              {result.suggestions.map((suggestion) => {
                const decision = decisions[suggestion.id];
                return (
                  <div
                    key={suggestion.id}
                    className={`rounded-md border p-3 ${decision ? "opacity-60" : ""}`}
                  >
                    <div className="mb-1.5 flex items-center gap-2">
                      <Badge variant="secondary">
                        {suggestion.type === "add_skill"
                          ? "Add skill"
                          : suggestion.type === "rewrite_bullet"
                            ? "Rewrite bullet"
                            : "Summary"}
                      </Badge>
                      {suggestion.type === "add_skill" && (
                        <span className="text-xs text-muted-foreground">
                          → {suggestion.group} · only accept skills you actually have
                        </span>
                      )}
                      {decision && (
                        <Badge variant={decision === "accepted" ? "default" : "outline"}>
                          {decision === "accepted" ? "Applied" : "Skipped"}
                        </Badge>
                      )}
                    </div>
                    {suggestion.type === "add_skill" ? (
                      <p className="text-sm">
                        Add <strong>{suggestion.proposed}</strong> to your skills
                      </p>
                    ) : (
                      <div className="space-y-1 text-sm">
                        {suggestion.original && (
                          <p className="text-muted-foreground line-through decoration-muted-foreground/50">
                            {suggestion.original}
                          </p>
                        )}
                        <p>{suggestion.proposed}</p>
                      </div>
                    )}
                    {!decision && (
                      <div className="mt-2 flex gap-2">
                        <Button size="sm" className="bg-blue-700 hover:bg-blue-800" onClick={() => applySuggestion(suggestion, "accepted")}>
                          <Check className="mr-1 h-3.5 w-3.5" /> Accept
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => applySuggestion(suggestion, "skipped")}>
                          Skip — that's fine
                        </Button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              Accepted changes save automatically to this tailored copy. Sync it to
              the matcher from the toolbar when you're done, and the match becomes
              part of your history.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
