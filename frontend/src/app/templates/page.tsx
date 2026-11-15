import type { Metadata } from "next";
import Link from "next/link";

import { ResumePreview } from "@/components/resume-preview";
import { SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { sampleContentForTemplate, TEMPLATE_INFO } from "@/lib/sample-data";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Resume templates — ATS-safe designs with honest notes",
  description:
    "Six resume templates rendered live from real sample documents: Classic, Modern, Compact Tech, Two-Column Sidebar, Minimal, and Graduate — each with guidance on who it's for and how ATS parsers handle it.",
};

export default function TemplatesPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6">
        <div className="max-w-2xl">
          <h1 className="text-3xl font-bold tracking-tight">Resume templates</h1>
          <p className="mt-3 text-muted-foreground">
            Every preview below is the real template rendering a real sample
            document — the same output the builder produces. Pick by who you
            are and where you&apos;re applying; each template page carries
            honest ATS notes, including the one template some parsers dislike.
          </p>
        </div>

        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {TEMPLATE_INFO.map((template) => (
            <Card key={template.id} className="overflow-hidden">
              <div className="max-h-96 overflow-hidden border-b bg-white">
                <div className="origin-top scale-[0.62]" style={{ width: "161%" }}>
                  <ResumePreview
                    content={sampleContentForTemplate(template.id)}
                    templateId={template.id}
                  />
                </div>
              </div>
              <CardContent className="space-y-3 py-5">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">{template.label}</h2>
                  <Badge variant="secondary">{template.tagline}</Badge>
                </div>
                <p className="line-clamp-2 text-sm text-muted-foreground">
                  {template.description}
                </p>
                <Link
                  href={`/templates/${template.id}`}
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                >
                  Who it&apos;s for & ATS notes
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-12 rounded-xl border bg-blue-50/60 p-6 text-center">
          <p className="font-medium">Templates are free in the builder — no watermark, ever.</p>
          <p className="mx-auto mt-1 max-w-lg text-sm text-muted-foreground">
            Start from any template, import your existing resume, and tailor it
            to a job description with a live match score.
          </p>
          <Link href="/signup" className={cn(buttonVariants(), "mt-4 bg-blue-700 hover:bg-blue-800")}>
            Build my resume
          </Link>
        </div>
      </main>
    </div>
  );
}
