"use client";

// Cover-letter editor (Phase 14): same two-pane pattern as the resume
// builder — form left, live A4 preview right, debounced autosave, template
// and theme controls, PDF via the print route. State is local (a letter is a
// flat form, unlike the builder's nested tree that justified Zustand).

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  FileDown,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { LetterPreview } from "@/components/letter-preview";
import { A4Page } from "@/components/resume-preview";
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
import {
  TEMPLATE_IDS,
  TEMPLATE_LABELS,
  type CoverLetter,
  type LetterContent,
} from "@/lib/api/types";

function Field({
  label, value, onChange, className,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  className?: string;
}) {
  return (
    <div className={className}>
      <Label className="text-xs">{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} className="mt-1" />
    </div>
  );
}

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

export default function LetterEditorClient() {
  const params = useParams<{ id: string }>();
  const letterId = Number(params.id);
  const queryClient = useQueryClient();

  const [letter, setLetter] = useState<CoverLetter | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const initialised = useRef(false);

  const letterQuery = useQuery({
    queryKey: ["cover-letter", letterId],
    queryFn: () => api.getCoverLetter(letterId),
  });

  useEffect(() => {
    if (letterQuery.data && !initialised.current) {
      initialised.current = true;
      setLetter(letterQuery.data);
    }
  }, [letterQuery.data]);

  // Debounced autosave, mirroring the builder editor.
  useEffect(() => {
    if (!dirty || !letter) return;
    const t = setTimeout(async () => {
      setSaving(true);
      try {
        await api.updateCoverLetter(letter.id, {
          title: letter.title,
          template_id: letter.template_id,
          theme: letter.theme,
          content: letter.content,
        });
        setDirty(false);
        setLastSavedAt(new Date());
        queryClient.invalidateQueries({ queryKey: ["cover-letters"] });
      } catch {
        toast.error("Autosave failed — your changes are still in the editor.");
      } finally {
        setSaving(false);
      }
    }, 1200);
    return () => clearTimeout(t);
  }, [dirty, letter, queryClient]);

  const patch = (partial: Partial<CoverLetter>) => {
    setLetter((current) => (current ? { ...current, ...partial } : current));
    setDirty(true);
  };
  const patchContent = (mutate: (draft: LetterContent) => void) => {
    setLetter((current) => {
      if (!current) return current;
      const draft = structuredClone(current.content) as LetterContent;
      mutate(draft);
      return { ...current, content: draft };
    });
    setDirty(true);
  };

  if (letterQuery.isLoading || !letter) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const c = letter.content;
  const theme = letter.theme ?? {};

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/app/cover-letters" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Cover letters
        </Link>
        <Input
          value={letter.title}
          onChange={(e) => patch({ title: e.target.value })}
          className="w-72 font-medium"
          aria-label="Letter title"
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
        <div className="ml-auto">
          <Button
            size="sm"
            className="bg-blue-700 hover:bg-blue-800"
            onClick={() => window.open(`/print/cover-letters/${letter.id}`, "_blank")}
          >
            <FileDown className="mr-1.5 h-4 w-4" /> PDF
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/30 px-3 py-2">
        <div className="flex items-center gap-2">
          <Label className="text-xs">Template</Label>
          <Select value={letter.template_id} onValueChange={(v) => patch({ template_id: v ?? "classic" })}>
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
            onChange={(e) => patch({ theme: { ...theme, accent: e.target.value } })}
            className="h-8 w-10 cursor-pointer rounded border bg-transparent"
          />
        </div>
        <div className="flex items-center gap-2">
          <Label className="text-xs">Font</Label>
          <Select value={theme.font ?? "sans"} onValueChange={(v) => patch({ theme: { ...theme, font: (v as "sans" | "serif") ?? "sans" } })}>
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sans">Sans</SelectItem>
              <SelectItem value="serif">Serif</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground">
          Tip: use the same template + accent as your resume — they read as one application.
        </p>
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(380px,460px)_1fr]">
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Sender</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-3">
              <Field label="Your name" value={c.sender.name} onChange={(v) => patchContent((d) => { d.sender.name = v; })} />
              <Field label="Your title" value={c.sender.title} onChange={(v) => patchContent((d) => { d.sender.title = v; })} />
              <Field label="Email" value={c.sender.email} onChange={(v) => patchContent((d) => { d.sender.email = v; })} />
              <Field label="Phone" value={c.sender.phone} onChange={(v) => patchContent((d) => { d.sender.phone = v; })} />
              <Field label="Location" value={c.sender.location} onChange={(v) => patchContent((d) => { d.sender.location = v; })} className="col-span-2" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Recipient</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-3">
              <Field label="Recipient name (optional)" value={c.recipient.name} onChange={(v) => patchContent((d) => { d.recipient.name = v; })} />
              <Field label="Company" value={c.recipient.company} onChange={(v) => patchContent((d) => { d.recipient.company = v; })} />
              <Field label="Role applied for" value={c.recipient.role} onChange={(v) => patchContent((d) => { d.recipient.role = v; })} />
              <div>
                <Label className="text-xs">Date</Label>
                <Input type="date" value={c.date} onChange={(e) => patchContent((d) => { d.date = e.target.value; })} className="mt-1" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Letter</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Field label="Greeting" value={c.greeting} onChange={(v) => patchContent((d) => { d.greeting = v; })} />
              {c.paragraphs.map((paragraph, i) => (
                <div key={i} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <Label className="text-xs">Paragraph {i + 1}</Label>
                    <div className="flex gap-1">
                      <Button type="button" size="icon" variant="ghost" className="h-7 w-7" disabled={i === 0} onClick={() => patchContent((d) => { [d.paragraphs[i - 1], d.paragraphs[i]] = [d.paragraphs[i], d.paragraphs[i - 1]]; })} aria-label="Move paragraph up">
                        <ArrowUp className="h-3.5 w-3.5" />
                      </Button>
                      <Button type="button" size="icon" variant="ghost" className="h-7 w-7" disabled={i === c.paragraphs.length - 1} onClick={() => patchContent((d) => { [d.paragraphs[i + 1], d.paragraphs[i]] = [d.paragraphs[i], d.paragraphs[i + 1]]; })} aria-label="Move paragraph down">
                        <ArrowDown className="h-3.5 w-3.5" />
                      </Button>
                      <Button type="button" size="icon" variant="ghost" className="h-7 w-7 text-destructive" onClick={() => patchContent((d) => { d.paragraphs.splice(i, 1); })} aria-label="Remove paragraph">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                  <Textarea
                    value={paragraph}
                    onChange={(e) => patchContent((d) => { d.paragraphs[i] = e.target.value; })}
                    rows={4}
                  />
                </div>
              ))}
              <Button variant="outline" size="sm" onClick={() => patchContent((d) => { d.paragraphs.push(""); })}>
                <Plus className="mr-1 h-3.5 w-3.5" /> Add paragraph
              </Button>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Closing" value={c.closing} onChange={(v) => patchContent((d) => { d.closing = v; })} />
                <Field label="Signature name" value={c.signature_name} onChange={(v) => patchContent((d) => { d.signature_name = v; })} />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="sticky top-4">
          <ScaledPreview>
            <A4Page>
              <LetterPreview content={c} templateId={letter.template_id} theme={theme} />
            </A4Page>
          </ScaledPreview>
        </div>
      </div>
    </div>
  );
}
