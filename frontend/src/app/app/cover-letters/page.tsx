"use client";

// Cover letters — list + generate panel (Phase 14).
// The primary flow is one-click generation: resume (upload or built
// document) + job (saved or pasted) + tone → an editable letter draft.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, FilePlus2, Loader2, MailPlus, PenLine, Sparkles, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import { LETTER_TONES, TEMPLATE_LABELS, type LetterContent } from "@/lib/api/types";

const BLANK_CONTENT: LetterContent = {
  sender: { name: "", title: "", email: "", phone: "", location: "" },
  recipient: { name: "", company: "", role: "" },
  date: new Date().toISOString().slice(0, 10),
  greeting: "Dear Hiring Manager,",
  paragraphs: [""],
  closing: "Sincerely,",
  signature_name: "",
};

export default function CoverLettersPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [source, setSource] = useState(""); // "resume:<id>" | "document:<id>"
  const [jobSource, setJobSource] = useState(""); // "job:<id>" | "paste"
  const [jobText, setJobText] = useState("");
  const [tone, setTone] = useState("professional");

  const letters = useQuery({ queryKey: ["cover-letters"], queryFn: api.listCoverLetters });
  const resumes = useQuery({ queryKey: ["resumes"], queryFn: api.listResumes });
  const documents = useQuery({ queryKey: ["documents"], queryFn: api.listDocuments });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.listJobs });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["cover-letters"] });

  const generate = useMutation({
    mutationFn: () => {
      const [kind, id] = source.split(":");
      const body: Parameters<typeof api.generateCoverLetter>[0] = { tone };
      if (kind === "resume") body.resume_id = Number(id);
      if (kind === "document") body.resume_document_id = Number(id);
      if (jobSource === "paste") body.job_text = jobText;
      else if (jobSource.startsWith("job:")) body.job_id = Number(jobSource.split(":")[1]);
      return api.generateCoverLetter(body);
    },
    onSuccess: (letter) => {
      toast.success("Draft generated — make it yours in the editor.");
      router.push(`/app/cover-letters/${letter.id}`);
    },
    onError: () => toast.error("Generation failed. Check the resume and job, then try again."),
  });

  const createBlank = useMutation({
    mutationFn: () =>
      api.createCoverLetter({
        title: "Untitled cover letter",
        template_id: "classic",
        theme: { accent: "#1d4ed8", font: "sans", density: "normal" },
        content: structuredClone(BLANK_CONTENT),
      }),
    onSuccess: (letter) => router.push(`/app/cover-letters/${letter.id}`),
    onError: () => toast.error("Could not create the letter."),
  });

  const duplicate = useMutation({
    mutationFn: (id: number) => api.duplicateCoverLetter(id),
    onSuccess: invalidate,
    onError: () => toast.error("Duplicate failed."),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteCoverLetter(id),
    onSuccess: invalidate,
    onError: () => toast.error("Delete failed."),
  });

  const canGenerate =
    source &&
    (jobSource === "paste" ? jobText.trim().length >= 30 : jobSource.startsWith("job:"));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Cover Letters</h1>
        <p className="text-muted-foreground">
          Generate a draft from a resume + job, then edit it like any document.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 pt-6">
          <p className="flex items-center gap-2 text-sm font-medium">
            <Sparkles className="h-4 w-4 text-blue-700" /> Generate a draft
          </p>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>Your resume</Label>
              <Select value={source} onValueChange={(v) => setSource(v ?? "")}>
                <SelectTrigger>
                  <SelectValue placeholder="Upload or built document" />
                </SelectTrigger>
                <SelectContent>
                  {(resumes.data ?? []).map((r) => (
                    <SelectItem key={`r${r.id}`} value={`resume:${r.id}`}>
                      {r.file_name ?? `Resume #${r.id}`}
                    </SelectItem>
                  ))}
                  {(documents.data ?? []).map((d) => (
                    <SelectItem key={`d${d.id}`} value={`document:${d.id}`}>
                      {d.title} (built)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>The job</Label>
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
            <div className="space-y-2">
              <Label>Tone</Label>
              <Select value={tone} onValueChange={(v) => setTone(v ?? "professional")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LETTER_TONES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t[0].toUpperCase() + t.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {jobSource === "paste" && (
            <Textarea
              value={jobText}
              onChange={(e) => setJobText(e.target.value)}
              rows={5}
              placeholder="Paste the job description here…"
            />
          )}
          <div className="flex flex-wrap gap-2">
            <Button
              className="bg-blue-700 hover:bg-blue-800"
              onClick={() => generate.mutate()}
              disabled={!canGenerate || generate.isPending}
            >
              {generate.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <MailPlus className="mr-2 h-4 w-4" />
              )}
              Generate draft
            </Button>
            <Button variant="outline" onClick={() => createBlank.mutate()} disabled={createBlank.isPending}>
              <FilePlus2 className="mr-2 h-4 w-4" /> Start blank instead
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Generation uses AI when a model is available and a structured template
            otherwise — either way the draft is grounded only in your resume, and
            skill gaps are framed honestly, never invented.
          </p>
        </CardContent>
      </Card>

      {letters.isLoading && <Skeleton className="h-32" />}
      {letters.data?.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No cover letters yet — generate one above.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {letters.data?.map((letter) => (
          <Card key={letter.id}>
            <CardContent className="space-y-3 pt-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{letter.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {TEMPLATE_LABELS[letter.template_id] ?? letter.template_id} · Updated{" "}
                    {new Date(letter.updated_at).toLocaleDateString()}
                  </p>
                </div>
                {letter.job_id ? (
                  <Badge variant="secondary">From a match</Badge>
                ) : (
                  <Badge variant="outline">Manual</Badge>
                )}
              </div>
              <div className="flex gap-2">
                <Button size="sm" className="bg-blue-700 hover:bg-blue-800" onClick={() => router.push(`/app/cover-letters/${letter.id}`)}>
                  <PenLine className="mr-1.5 h-3.5 w-3.5" /> Edit
                </Button>
                <Button size="sm" variant="outline" onClick={() => duplicate.mutate(letter.id)} disabled={duplicate.isPending}>
                  <Copy className="mr-1.5 h-3.5 w-3.5" /> Duplicate
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-destructive"
                  onClick={() => {
                    if (confirm(`Delete "${letter.title}"? This cannot be undone.`)) {
                      remove.mutate(letter.id);
                    }
                  }}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" /> Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
