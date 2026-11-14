"use client";


// Print route for builder documents (Phase 13): renders ONLY the resume at
// exact A4 size with print CSS, then opens the browser's print dialog —
// "Save as PDF" produces the file. Rationale for browser-print over a
// server-side Chromium renderer is in decisions.md §13.5: it guarantees the
// PDF is byte-for-byte the preview the user approved, with no extra runtime
// to host. Auth still applies: the document loads through the BFF proxy.

import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect } from "react";

import { A4Page, ResumePreview } from "@/components/resume-preview";
import { api } from "@/lib/api/client";

export default function PrintDocumentPage() {
  const params = useParams<{ id: string }>();
  const documentId = Number(params.id);

  const docQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => api.getDocument(documentId),
  });

  useEffect(() => {
    if (docQuery.data) {
      document.title = `${docQuery.data.title} — Resume`;
      const t = setTimeout(() => window.print(), 600);
      return () => clearTimeout(t);
    }
  }, [docQuery.data]);

  if (docQuery.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (docQuery.isError || !docQuery.data) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 text-center text-sm text-muted-foreground">
        Couldn&apos;t load this document. Make sure you&apos;re signed in, then try again.
      </div>
    );
  }

  const doc = docQuery.data;
  return (
    <div className="print-area min-h-screen bg-neutral-200 py-8 print:bg-white print:py-0">
      <p className="mx-auto mb-4 max-w-md text-center text-sm text-neutral-600 print:hidden">
        Use <strong>Save as PDF</strong> in the print dialog. Set margins to
        None for an exact A4 page.
      </p>
      <A4Page>
        <ResumePreview content={doc.content} templateId={doc.template_id} theme={doc.theme} />
      </A4Page>
    </div>
  );
}
