"use client";

// Inline AI assists for the builder editor (Phase 15): summary variants and
// bullet generation. Both follow the product contract — pick-to-insert,
// never auto-applied, and the copy says plainly that generation only
// rephrases the user's own facts.

import { useMutation } from "@tanstack/react-query";
import { Check, Loader2, Plus, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import type { SummaryVariant } from "@/lib/api/types";

export function SummaryAssist({
  title,
  skills,
  onPick,
}: {
  title: string;
  skills: string[];
  onPick: (text: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [variants, setVariants] = useState<SummaryVariant[]>([]);

  const generate = useMutation({
    mutationFn: () => api.generateSummary({ title, skills, target_role: title }),
    onSuccess: (data) => {
      setVariants(data.variants);
      setOpen(true);
    },
    onError: () => toast.error("Summary generation failed."),
  });

  return (
    <div>
      <Button
        type="button"
        size="sm"
        variant="outline"
        onClick={() => generate.mutate()}
        disabled={generate.isPending}
      >
        {generate.isPending ? (
          <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
        ) : (
          <Sparkles className="mr-1.5 h-3.5 w-3.5" />
        )}
        Generate with AI
      </Button>
      {open && variants.length > 0 && (
        <div className="mt-3 space-y-2">
          {variants.map((variant) => (
            <div key={variant.label} className="rounded-md border bg-muted/30 p-3">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-xs font-semibold tracking-wide uppercase">
                  {variant.label}
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-7 text-blue-700"
                  onClick={() => {
                    onPick(variant.text);
                    setOpen(false);
                  }}
                >
                  <Check className="mr-1 h-3.5 w-3.5" /> Use this
                </Button>
              </div>
              <p className="text-sm">{variant.text}</p>
            </div>
          ))}
          <p className="text-xs text-muted-foreground">
            Built only from your title and skills — edit freely after inserting.
          </p>
        </div>
      )}
    </div>
  );
}

export function BulletsAssist({
  role,
  company,
  onAdd,
}: {
  role: string;
  company: string;
  onAdd: (bullets: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [bullets, setBullets] = useState<string[]>([]);
  const [added, setAdded] = useState<Set<number>>(new Set());

  const generate = useMutation({
    mutationFn: () => api.generateBullets({ role, company, notes }),
    onSuccess: (data) => {
      setBullets(data.bullets);
      setAdded(new Set());
      if (data.bullets.length === 0) toast.error("Nothing usable in those notes — add a bit more detail.");
    },
    onError: () => toast.error("Bullet generation failed."),
  });

  if (!open) {
    return (
      <Button type="button" size="sm" variant="ghost" className="text-blue-700" onClick={() => setOpen(true)}>
        <Sparkles className="mr-1.5 h-3.5 w-3.5" /> Write bullets from rough notes
      </Button>
    );
  }

  return (
    <div className="space-y-2 rounded-md border bg-muted/30 p-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold tracking-wide uppercase">Rough notes → bullets</p>
        <Button type="button" size="icon" variant="ghost" className="h-7 w-7" onClick={() => setOpen(false)} aria-label="Close bullet assistant">
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>
      <Textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={3}
        placeholder="What did you actually do? e.g. 'responsible for the payments API; migrated db to postgres; cut deploy time from 40 to 15 minutes'"
      />
      <div className="flex items-center gap-2">
        <Button type="button" size="sm" className="bg-blue-700 hover:bg-blue-800" onClick={() => generate.mutate()} disabled={notes.trim().length < 10 || generate.isPending}>
          {generate.isPending ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Sparkles className="mr-1.5 h-3.5 w-3.5" />}
          Generate bullets
        </Button>
        <span className="text-xs text-muted-foreground">
          Your facts only — numbers are never invented.
        </span>
      </div>
      {bullets.length > 0 && (
        <ul className="space-y-1.5">
          {bullets.map((bullet, i) => (
            <li key={i} className="flex items-start justify-between gap-2 rounded bg-background p-2 text-sm">
              <span>{bullet}</span>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-7 shrink-0"
                disabled={added.has(i)}
                onClick={() => {
                  onAdd([bullet]);
                  setAdded((prev) => new Set(prev).add(i));
                }}
              >
                {added.has(i) ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
