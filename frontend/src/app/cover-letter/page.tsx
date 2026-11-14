"use client";

// Public cover-letter page (Phase 14): what the generator does, three
// original sample letters rendered with the real template component, and the
// path in. Samples are illustrative — written for this page, tech roles
// first, matching the product's v1 positioning.

import Link from "next/link";

import { LetterPreview } from "@/components/letter-preview";
import { SiteHeader } from "@/components/site-header";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { LetterContent } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const SAMPLES: { label: string; templateId: string; content: LetterContent }[] = [
  {
    label: "Backend developer — Classic",
    templateId: "classic",
    content: {
      sender: { name: "Aarav Sharma", title: "Senior Backend Developer", email: "aarav@example.com", phone: "+91 98200 12345", location: "Pune, India" },
      recipient: { name: "", company: "FinEdge", role: "Senior Backend Developer" },
      date: "2026-11-10",
      greeting: "Dear Hiring Manager,",
      paragraphs: [
        "I am writing to apply for the Senior Backend Developer position at FinEdge. As a backend developer with six years of experience building payment-adjacent APIs, the role's focus on reliability and auditability is exactly where I have spent my career.",
        "My background covers Python, FastAPI, and PostgreSQL — the core of your stack. At my current company I own the ledger service that processes two million transactions a day, and I led our migration to idempotent, event-driven writes, which cut reconciliation breaks by 70%.",
        "Thank you for considering my application. I would appreciate the opportunity to discuss how that experience maps onto what FinEdge is building.",
      ],
      closing: "Sincerely,",
      signature_name: "Aarav Sharma",
    },
  },
  {
    label: "Full-stack developer — Modern",
    templateId: "modern",
    content: {
      sender: { name: "Meera Nair", title: "Full-Stack Developer", email: "meera@example.com", phone: "", location: "Bengaluru, India" },
      recipient: { name: "Rohan Iyer", company: "Craftly", role: "Product Engineer" },
      date: "2026-11-08",
      greeting: "Dear Rohan Iyer,",
      paragraphs: [
        "I was excited to see the Product Engineer opening at Craftly — I am a full-stack developer with four years of experience, and the role's mix of product thinking and hands-on building is precisely what I am looking for next.",
        "I work primarily in TypeScript, React, and Node.js. Most recently I built the onboarding flow for a B2B SaaS dashboard used by 40,000 teams, owning everything from the schema to the empty states — activation rose 18% in the quarter after launch.",
        "To be straightforward about fit: your posting mentions Go, which I am actively building depth in through a side project rather than professional work. What I offer today is strength in the core of the role and a track record of picking up adjacent technology quickly.",
      ],
      closing: "Warm regards,",
      signature_name: "Meera Nair",
    },
  },
  {
    label: "Data engineer — Minimal",
    templateId: "minimal",
    content: {
      sender: { name: "Kunal Verma", title: "Data Engineer", email: "kunal@example.com", phone: "", location: "Remote" },
      recipient: { name: "", company: "Northwind Analytics", role: "Data Engineer" },
      date: "2026-11-05",
      greeting: "Dear Hiring Manager,",
      paragraphs: [
        "I am applying for the Data Engineer position at Northwind Analytics. I have five years of experience building pipelines that analysts actually trust, most recently on Spark and Airflow at terabyte scale.",
        "My core work is Python, SQL, and dbt. I rebuilt our ingestion layer to be fully incremental with data-quality gates at every stage; late or silent failures dropped to near zero, and the team stopped keeping shadow spreadsheets.",
        "I would welcome a conversation about how that approach fits your platform plans.",
      ],
      closing: "Best regards,",
      signature_name: "Kunal Verma",
    },
  },
];

export default function CoverLetterPublicPage() {
  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-14 sm:px-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            A cover letter that matches your resume
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-muted-foreground">
            Pick your resume and the job — the generator drafts a letter from
            what your resume actually says, in the same template, ready to edit.
            Skill gaps are bridged honestly, never invented.
          </p>
          <Link
            href="/signup"
            className={cn(buttonVariants(), "mt-6 bg-blue-700 hover:bg-blue-800")}
          >
            Draft my cover letter
          </Link>
        </div>

        <div className="mt-14 space-y-10">
          {SAMPLES.map((sample) => (
            <div key={sample.label}>
              <h2 className="mb-3 text-sm font-semibold tracking-wide text-muted-foreground uppercase">
                {sample.label}
              </h2>
              <Card>
                <CardContent className="overflow-x-auto pt-4">
                  <div className="mx-auto max-w-3xl">
                    <LetterPreview
                      content={sample.content}
                      templateId={sample.templateId}
                      theme={{ accent: "#1d4ed8", font: "sans", density: "normal" }}
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
          ))}
        </div>

        <p className="mt-10 text-center text-sm text-muted-foreground">
          Samples are illustrative. Your letters are generated from your own
          resume and the job you paste — and stay private to your account.
        </p>
      </main>
    </div>
  );
}
