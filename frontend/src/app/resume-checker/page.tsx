"use client";

// Public, anonymous ATS checker — the free tool at the top of the funnel
// (roadmap Phase 2). No account, and nothing is stored: the backend parses
// the upload in-memory and returns the result (see app/api/ats.py).

import { FileUp, Loader2, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { AtsResultView } from "@/components/ats-result";
import { SiteHeader } from "@/components/site-header";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ApiError, anonymousAtsCheck } from "@/lib/api/client";
import type { AtsCheckResult } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export default function ResumeCheckerPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [result, setResult] = useState<AtsCheckResult | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext !== "pdf" && ext !== "docx") {
      toast.error("Only PDF or DOCX resumes are accepted.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error("That file is over the 10 MB limit.");
      return;
    }
    setIsChecking(true);
    setResult(null);
    setFileName(file.name);
    try {
      setResult(await anonymousAtsCheck(file));
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.detail : "The check failed. Try again.",
      );
    } finally {
      setIsChecking(false);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-14 sm:px-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Free ATS resume checker
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Upload your resume and get an instant ATS-readiness report — 22
            checks across parsing, contact details, sections, content quality,
            skills, and format. No account needed.
          </p>
          <p className="mt-3 inline-flex items-center gap-1.5 text-sm text-muted-foreground">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            Your file is checked in-memory and never stored.
          </p>
        </div>

        <Card className="mt-10">
          <CardContent className="pt-6">
            <div
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                handleFile(e.dataTransfer.files?.[0]);
              }}
              className={cn(
                "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-10 text-center transition-colors",
                dragOver
                  ? "border-blue-600 bg-blue-50"
                  : "border-muted-foreground/25 hover:border-blue-400",
              )}
            >
              {isChecking ? (
                <Loader2 className="h-9 w-9 animate-spin text-blue-700" />
              ) : (
                <FileUp className="h-9 w-9 text-blue-700" />
              )}
              <p className="mt-2 font-medium">
                {isChecking
                  ? `Checking ${fileName ?? "your resume"}…`
                  : "Drop your resume here, or click to browse"}
              </p>
              <p className="text-sm text-muted-foreground">PDF or DOCX, up to 10 MB</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx"
                className="hidden"
                onChange={(e) => {
                  handleFile(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </div>
          </CardContent>
        </Card>

        {result && (
          <Card className="mt-6">
            <CardContent className="pt-6">
              <AtsResultView result={result} />
              <div className="mt-8 rounded-lg bg-blue-50 p-5 text-center">
                <p className="font-medium">Want to know how this resume scores against a real job?</p>
                <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
                  The checker grades your resume on its own. Create a free
                  account to match it against a job description — with missing
                  keywords and AI suggestions.
                </p>
                <Link
                  href="/signup"
                  className={cn(buttonVariants(), "mt-4 bg-blue-700 hover:bg-blue-800")}
                >
                  Run the job matcher
                </Link>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
