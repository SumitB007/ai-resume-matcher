"use client";


// Builder editor (Phase 13): form on the left, live A4 preview on the right,
// debounced autosave, template/theme controls, live ATS score, sync-to-matcher,
// and PDF via the print route. Editor state lives in the Zustand store
// (src/lib/store/editor-store.ts); saving goes through TanStack mutations.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  CheckCircle2,
  FileDown,
  Loader2,
  Plus,
  RefreshCw,
  ScanSearch,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { AtsResultView } from "@/components/ats-result";
import { A4Page, ResumePreview } from "@/components/resume-preview";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { TEMPLATE_IDS, TEMPLATE_LABELS, type AtsCheckResult } from "@/lib/api/types";
import { useEditorStore } from "@/lib/store/editor-store";

// ── Small form helpers ──────────────────────────────────────────────────────

function Field({
  label, value, onChange, placeholder, className,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <Label className="text-xs">{label}</Label>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1"
      />
    </div>
  );
}

function LinesField({
  label, items, onChange, placeholder, hint,
}: {
  label: string;
  items: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
  hint?: string;
}) {
  return (
    <div>
      <Label className="text-xs">{label}</Label>
      <Textarea
        value={items.join("\n")}
        onChange={(e) => onChange(e.target.value.split("\n"))}
        placeholder={placeholder}
        rows={Math.max(2, items.length)}
        className="mt-1"
      />
      {hint && <p className="mt-1 text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

function EntryControls({
  index, count, onMove, onRemove,
}: {
  index: number;
  count: number;
  onMove: (dir: -1 | 1) => void;
  onRemove: () => void;
}) {
  return (
    <div className="flex gap-1">
      <Button type="button" size="icon" variant="ghost" className="h-7 w-7" disabled={index === 0} onClick={() => onMove(-1)} aria-label="Move up">
        <ArrowUp className="h-3.5 w-3.5" />
      </Button>
      <Button type="button" size="icon" variant="ghost" className="h-7 w-7" disabled={index === count - 1} onClick={() => onMove(1)} aria-label="Move down">
        <ArrowDown className="h-3.5 w-3.5" />
      </Button>
      <Button type="button" size="icon" variant="ghost" className="h-7 w-7 text-destructive" onClick={onRemove} aria-label="Remove entry">
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function move<T>(arr: T[], index: number, dir: -1 | 1): T[] {
  const target = index + dir;
  if (target < 0 || target >= arr.length) return arr;
  const copy = [...arr];
  [copy[index], copy[target]] = [copy[target], copy[index]];
  return copy;
}

/** Scales the fixed-width A4 preview to fit its container. */
function ScaledPreview({ children }: { children: React.ReactNode }) {
  const outerRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.66);
  const [height, setHeight] = useState(760);

  useEffect(() => {
    const outer = outerRef.current;
    const inner = innerRef.current;
    if (!outer || !inner) return;
    const update = () => {
      const s = Math.min(1, outer.clientWidth / 794);
      setScale(s);
      setHeight(inner.scrollHeight * s);
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(outer);
    ro.observe(inner);
    return () => ro.disconnect();
  }, []);

  return (
    <div ref={outerRef} className="relative w-full overflow-hidden" style={{ height }}>
      <div
        ref={innerRef}
        className="absolute top-0 left-0 origin-top-left"
        style={{ transform: `scale(${scale})`, width: 794 }}
      >
        {children}
      </div>
    </div>
  );
}

// ── Editor page ─────────────────────────────────────────────────────────────

export default function BuilderEditorPage() {
  const params = useParams<{ id: string }>();
  const documentId = Number(params.id);
  const queryClient = useQueryClient();

  const doc = useEditorStore((s) => s.document);
  const dirty = useEditorStore((s) => s.dirty);
  const saving = useEditorStore((s) => s.saving);
  const lastSavedAt = useEditorStore((s) => s.lastSavedAt);
  const init = useEditorStore((s) => s.init);
  const setTitle = useEditorStore((s) => s.setTitle);
  const setTemplate = useEditorStore((s) => s.setTemplate);
  const setTheme = useEditorStore((s) => s.setTheme);
  const updateContent = useEditorStore((s) => s.updateContent);
  const setSaving = useEditorStore((s) => s.setSaving);
  const markSaved = useEditorStore((s) => s.markSaved);

  const [atsResult, setAtsResult] = useState<AtsCheckResult | null>(null);
  const [showAts, setShowAts] = useState(false);
  const initialisedFor = useRef<number | null>(null);

  const docQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => api.getDocument(documentId),
  });

  useEffect(() => {
    if (docQuery.data && initialisedFor.current !== documentId) {
      initialisedFor.current = documentId;
      init(docQuery.data);
    }
  }, [docQuery.data, documentId, init]);

  const saveNow = useCallback(async () => {
    const current = useEditorStore.getState().document;
    if (!current) return;
    setSaving(true);
    try {
      await api.updateDocument(current.id, {
        title: current.title,
        template_id: current.template_id,
        theme: current.theme,
        content: current.content,
      });
      markSaved();
    } catch {
      setSaving(false);
      toast.error("Autosave failed — your changes are still in the editor.");
    }
  }, [markSaved, setSaving]);

  // Debounced autosave: 1.2s after the last edit.
  useEffect(() => {
    if (!dirty || !doc) return;
    const t = setTimeout(saveNow, 1200);
    return () => clearTimeout(t);
  }, [dirty, doc, saveNow]);

  const syncMutation = useMutation({
    mutationFn: async () => {
      if (useEditorStore.getState().dirty) await saveNow();
      return api.syncDocumentResume(documentId);
    },
    onSuccess: () => {
      toast.success("Synced — this resume is now available in the matcher.");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      queryClient.invalidateQueries({ queryKey: ["document", documentId] });
      initialisedFor.current = null;
      docQuery.refetch();
    },
    onError: () => toast.error("Sync failed. Add more content and try again."),
  });

  const atsMutation = useMutation({
    mutationFn: async () => {
      if (useEditorStore.getState().dirty) await saveNow();
      return api.documentAtsCheck(documentId);
    },
    onSuccess: (result) => {
      setAtsResult(result);
      setShowAts(true);
    },
    onError: () => toast.error("ATS check failed."),
  });

  if (docQuery.isLoading || !doc) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const c = doc.content;
  const theme = doc.theme ?? {};

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/app/builder" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Builder
        </Link>
        <Input
          value={doc.title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-64 font-medium"
          aria-label="Document title"
        />
        <span className="text-xs text-muted-foreground">
          {saving
            ? "Saving…"
            : dirty
              ? "Unsaved changes"
              : lastSavedAt
                ? `Saved ${lastSavedAt.toLocaleTimeString()}`
                : "All changes saved"}
        </span>
        <div className="ml-auto flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => atsMutation.mutate()} disabled={atsMutation.isPending}>
            {atsMutation.isPending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <ScanSearch className="mr-1.5 h-4 w-4" />}
            ATS score{atsResult ? `: ${Math.round(atsResult.score)}%` : ""}
          </Button>
          <Button variant="outline" size="sm" onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
            {syncMutation.isPending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-1.5 h-4 w-4" />}
            {doc.resume_id ? "Re-sync to matcher" : "Sync to matcher"}
          </Button>
          <Button
            size="sm"
            className="bg-blue-700 hover:bg-blue-800"
            onClick={() => window.open(`/print/documents/${doc.id}`, "_blank")}
          >
            <FileDown className="mr-1.5 h-4 w-4" /> PDF
          </Button>
        </div>
      </div>

      {doc.resume_id && (
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
          Synced as a resume in the matcher — re-sync after edits to refresh its score data.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/30 px-3 py-2">
        <div className="flex items-center gap-2">
          <Label className="text-xs">Template</Label>
          <Select value={doc.template_id} onValueChange={(v) => setTemplate(v ?? "classic")}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TEMPLATE_IDS.map((id) => (
                <SelectItem key={id} value={id}>
                  {TEMPLATE_LABELS[id]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Label className="text-xs" htmlFor="accent">Accent</Label>
          <input
            id="accent"
            type="color"
            value={theme.accent ?? "#1d4ed8"}
            onChange={(e) => setTheme({ ...theme, accent: e.target.value })}
            className="h-8 w-10 cursor-pointer rounded border bg-transparent"
          />
        </div>
        <div className="flex items-center gap-2">
          <Label className="text-xs">Font</Label>
          <Select value={theme.font ?? "sans"} onValueChange={(v) => setTheme({ ...theme, font: (v as "sans" | "serif") ?? "sans" })}>
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sans">Sans</SelectItem>
              <SelectItem value="serif">Serif</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Label className="text-xs">Density</Label>
          <Select value={theme.density ?? "normal"} onValueChange={(v) => setTheme({ ...theme, density: (v as "normal" | "compact") ?? "normal" })}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="normal">Normal</SelectItem>
              <SelectItem value="compact">Compact</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {showAts && atsResult && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">ATS readiness — live from your content</CardTitle>
          </CardHeader>
          <CardContent>
            <AtsResultView result={atsResult} />
          </CardContent>
        </Card>
      )}

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(380px,460px)_1fr]">
        {/* ── Form column ── */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Personal details</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-3">
              <Field label="Full name" value={c.personal.full_name} onChange={(v) => updateContent((d) => { d.personal.full_name = v; })} />
              <Field label="Job title" value={c.personal.title} onChange={(v) => updateContent((d) => { d.personal.title = v; })} />
              <Field label="Email" value={c.personal.email} onChange={(v) => updateContent((d) => { d.personal.email = v; })} />
              <Field label="Phone" value={c.personal.phone} onChange={(v) => updateContent((d) => { d.personal.phone = v; })} />
              <Field label="Location" value={c.personal.location} onChange={(v) => updateContent((d) => { d.personal.location = v; })} className="col-span-2" />
              <div className="col-span-2">
                <LinesField label="Links (one per line)" items={c.personal.links} onChange={(v) => updateContent((d) => { d.personal.links = v; })} placeholder="linkedin.com/in/you" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Summary</CardTitle></CardHeader>
            <CardContent>
              <Textarea value={c.summary} onChange={(e) => updateContent((d) => { d.summary = e.target.value; })} rows={4} placeholder="2–3 lines: who you are, strongest skills, what you're targeting." />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between pb-3">
              <CardTitle className="text-base">Experience</CardTitle>
              <Button size="sm" variant="outline" onClick={() => updateContent((d) => { d.experience.push({ role: "", company: "", location: "", start: "", end: "", current: false, bullets: [] }); })}>
                <Plus className="mr-1 h-3.5 w-3.5" /> Add role
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {c.experience.map((job, i) => (
                <div key={i} className="space-y-3 rounded-lg border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{job.role || job.company || `Role ${i + 1}`}</span>
                    <EntryControls index={i} count={c.experience.length} onRemove={() => updateContent((d) => { d.experience.splice(i, 1); })} onMove={(dir) => updateContent((d) => { d.experience = move(d.experience, i, dir); })} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Role" value={job.role} onChange={(v) => updateContent((d) => { d.experience[i].role = v; })} />
                    <Field label="Company" value={job.company} onChange={(v) => updateContent((d) => { d.experience[i].company = v; })} />
                    <Field label="Start (e.g. 2021)" value={job.start} onChange={(v) => updateContent((d) => { d.experience[i].start = v; })} />
                    <Field label="End" value={job.end} onChange={(v) => updateContent((d) => { d.experience[i].end = v; })} />
                  </div>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={job.current} onChange={(e) => updateContent((d) => { d.experience[i].current = e.target.checked; })} className="h-4 w-4" />
                    I currently work here
                  </label>
                  <LinesField label="Bullets (one per line)" items={job.bullets} onChange={(v) => updateContent((d) => { d.experience[i].bullets = v; })} placeholder={"Built a FastAPI platform serving 2M requests/day"} hint="Start with an action verb and add numbers wherever they're true." />
                </div>
              ))}
              {c.experience.length === 0 && <p className="text-sm text-muted-foreground">No roles yet — add your most recent one.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between pb-3">
              <CardTitle className="text-base">Skills</CardTitle>
              <Button size="sm" variant="outline" onClick={() => updateContent((d) => { d.skills.groups.push({ label: "", items: [] }); })}>
                <Plus className="mr-1 h-3.5 w-3.5" /> Add group
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {c.skills.groups.map((group, i) => (
                <div key={i} className="space-y-3 rounded-lg border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{group.label || `Group ${i + 1}`}</span>
                    <EntryControls index={i} count={c.skills.groups.length} onRemove={() => updateContent((d) => { d.skills.groups.splice(i, 1); })} onMove={(dir) => updateContent((d) => { d.skills.groups = move(d.skills.groups, i, dir); })} />
                  </div>
                  <Field label="Group label" value={group.label} onChange={(v) => updateContent((d) => { d.skills.groups[i].label = v; })} placeholder="Backend" />
                  <div>
                    <Label className="text-xs">Skills (comma separated)</Label>
                    <Textarea value={group.items.join(", ")} onChange={(e) => updateContent((d) => { d.skills.groups[i].items = e.target.value.split(",").map((s) => s.trim()).filter(Boolean); })} rows={2} className="mt-1" placeholder="Python, FastAPI, PostgreSQL" />
                  </div>
                </div>
              ))}
              {c.skills.groups.length === 0 && <p className="text-sm text-muted-foreground">Group skills by area (Backend, DevOps…) or keep one group.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between pb-3">
              <CardTitle className="text-base">Education</CardTitle>
              <Button size="sm" variant="outline" onClick={() => updateContent((d) => { d.education.push({ school: "", degree: "", field: "", start: "", end: "" }); })}>
                <Plus className="mr-1 h-3.5 w-3.5" /> Add
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {c.education.map((edu, i) => (
                <div key={i} className="space-y-3 rounded-lg border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{edu.degree || edu.school || `Education ${i + 1}`}</span>
                    <EntryControls index={i} count={c.education.length} onRemove={() => updateContent((d) => { d.education.splice(i, 1); })} onMove={(dir) => updateContent((d) => { d.education = move(d.education, i, dir); })} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Degree" value={edu.degree} onChange={(v) => updateContent((d) => { d.education[i].degree = v; })} />
                    <Field label="Field" value={edu.field} onChange={(v) => updateContent((d) => { d.education[i].field = v; })} />
                    <Field label="School" value={edu.school} onChange={(v) => updateContent((d) => { d.education[i].school = v; })} className="col-span-2" />
                    <Field label="Start" value={edu.start} onChange={(v) => updateContent((d) => { d.education[i].start = v; })} />
                    <Field label="End" value={edu.end} onChange={(v) => updateContent((d) => { d.education[i].end = v; })} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between pb-3">
              <CardTitle className="text-base">Projects</CardTitle>
              <Button size="sm" variant="outline" onClick={() => updateContent((d) => { d.projects.push({ name: "", description: "", bullets: [] }); })}>
                <Plus className="mr-1 h-3.5 w-3.5" /> Add
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {c.projects.map((project, i) => (
                <div key={i} className="space-y-3 rounded-lg border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{project.name || `Project ${i + 1}`}</span>
                    <EntryControls index={i} count={c.projects.length} onRemove={() => updateContent((d) => { d.projects.splice(i, 1); })} onMove={(dir) => updateContent((d) => { d.projects = move(d.projects, i, dir); })} />
                  </div>
                  <Field label="Name" value={project.name} onChange={(v) => updateContent((d) => { d.projects[i].name = v; })} />
                  <div>
                    <Label className="text-xs">Description</Label>
                    <Textarea value={project.description} onChange={(e) => updateContent((d) => { d.projects[i].description = e.target.value; })} rows={2} className="mt-1" />
                  </div>
                  <LinesField label="Bullets (one per line)" items={project.bullets} onChange={(v) => updateContent((d) => { d.projects[i].bullets = v; })} />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Certifications & languages</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <LinesField label="Certifications (one per line)" items={c.certifications} onChange={(v) => updateContent((d) => { d.certifications = v; })} />
              <div>
                <Label className="text-xs">Languages (comma separated)</Label>
                <Textarea value={c.languages.join(", ")} onChange={(e) => updateContent((d) => { d.languages = e.target.value.split(",").map((s) => s.trim()).filter(Boolean); })} rows={1} className="mt-1" placeholder="English, Hindi" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between pb-3">
              <CardTitle className="text-base">Custom sections</CardTitle>
              <Button size="sm" variant="outline" onClick={() => updateContent((d) => { d.custom_sections.push({ title: "", items: [] }); })}>
                <Plus className="mr-1 h-3.5 w-3.5" /> Add section
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {c.custom_sections.map((section, i) => (
                <div key={i} className="space-y-3 rounded-lg border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{section.title || `Section ${i + 1}`}</span>
                    <EntryControls index={i} count={c.custom_sections.length} onRemove={() => updateContent((d) => { d.custom_sections.splice(i, 1); })} onMove={(dir) => updateContent((d) => { d.custom_sections = move(d.custom_sections, i, dir); })} />
                  </div>
                  <Field label="Section title" value={section.title} onChange={(v) => updateContent((d) => { d.custom_sections[i].title = v; })} placeholder="Volunteering" />
                  <LinesField label="Items (one per line)" items={section.items} onChange={(v) => updateContent((d) => { d.custom_sections[i].items = v; })} />
                </div>
              ))}
              {c.custom_sections.length === 0 && <p className="text-sm text-muted-foreground">Anything that doesn&apos;t fit above — volunteering, awards, publications.</p>}
            </CardContent>
          </Card>
        </div>

        {/* ── Preview column ── */}
        <div className="sticky top-4">
          <ScaledPreview>
            <A4Page>
              <ResumePreview content={c} templateId={doc.template_id} theme={theme} />
            </A4Page>
          </ScaledPreview>
        </div>
      </div>
    </div>
  );
}
