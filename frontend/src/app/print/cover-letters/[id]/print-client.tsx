"use client";

// Print route for cover letters (Phase 14): same contract as the resume
// print route — only the letter at exact A4, then the print dialog.

import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect } from "react";

import { LetterPreview } from "@/components/letter-preview";
import { A4Page } from "@/components/resume-preview";
import { api } from "@/lib/api/client";

export default function PrintCoverLetterClient() {
  const params = useParams<{ id: string }>();
  const letterId = Number(params.id);

  const letterQuery = useQuery({
    queryKey: ["cover-letter", letterId],
    queryFn: () => api.getCoverLetter(letterId),
  });

  useEffect(() => {
    if (letterQuery.data) {
      document.title = `${letterQuery.data.title} — Cover Letter`;
      const t = setTimeout(() => window.print(), 600);
      return () => clearTimeout(t);
    }
  }, [letterQuery.data]);

  if (letterQuery.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (letterQuery.isError || !letterQuery.data) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 text-center text-sm text-muted-foreground">
        Couldn&apos;t load this cover letter. Make sure you&apos;re signed in, then try again.
      </div>
    );
  }

  const letter = letterQuery.data;
  return (
    <div className="print-area min-h-screen bg-neutral-200 py-8 print:bg-white print:py-0">
      <p className="mx-auto mb-4 max-w-md text-center text-sm text-neutral-600 print:hidden">
        Use <strong>Save as PDF</strong> in the print dialog. Set margins to
        None for an exact A4 page.
      </p>
      <A4Page>
        <LetterPreview content={letter.content} templateId={letter.template_id} theme={letter.theme} />
      </A4Page>
    </div>
  );
}
