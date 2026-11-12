import {
  ArrowRight,
  FileText,
  Gauge,
  KeyRound,
  ListChecks,
  PenLine,
  ScanSearch,
  Sparkles,
  Upload,
} from "lucide-react";
import Link from "next/link";

import { SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const steps = [
  {
    icon: Upload,
    title: "Upload your resume",
    text: "Drop in a PDF or DOCX. We extract the text and skills, and build a semantic embedding of your experience.",
  },
  {
    icon: FileText,
    title: "Paste the job description",
    text: "Add the exact posting you're targeting — title, company, and the full description text.",
  },
  {
    icon: Gauge,
    title: "Get your honest score",
    text: "A hybrid score — 60% semantic fit, 40% keyword coverage — with the sub-scores shown separately, never hidden.",
  },
];

const resultCards = [
  {
    icon: ScanSearch,
    title: "Missing keywords, named",
    text: "The exact skills the job asks for that your resume doesn't mention yet — as a checklist, not a vague tip.",
  },
  {
    icon: ListChecks,
    title: "Section-level scores",
    text: "Skills match, experience relevance, and keyword density scored individually, so you know where the gap lives.",
  },
  {
    icon: Sparkles,
    title: "AI feedback that rewrites",
    text: "Strengths, critical gaps, and before/after bullet rewrites in the X-Y-Z formula — streamed in as it's written.",
  },
  {
    icon: PenLine,
    title: "A report you can keep",
    text: "Download a styled PDF assessment of every match, and watch your score improve across resume versions.",
  },
];

const roadmapItems = [
  {
    title: "Standalone ATS checker",
    text: "Score any resume on its own — file, sections, content quality — no job description needed.",
  },
  {
    title: "Resume builder & templates",
    text: "Build a resume in the browser with ATS-safe templates, live preview, and one-click PDF export.",
  },
  {
    title: "Cover letters",
    text: "Matching cover letter templates and an AI generator that writes from your resume and the job.",
  },
  {
    title: "One-click tailoring",
    text: "Adapt a built resume to a specific job description, accepting or rejecting every suggested change.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader />

      <main className="flex-1">
        {/* Hero — the JD matcher is the product, so it is the headline. */}
        <section className="border-b bg-gradient-to-b from-blue-50/80 to-background">
          <div className="mx-auto max-w-6xl px-4 py-20 text-center sm:px-6 sm:py-24">
            <Badge variant="secondary" className="mb-5">
              <KeyRound className="mr-1 h-3 w-3" /> Resume ↔ Job Description Matcher
            </Badge>
            <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
              Your resume vs. the job description —{" "}
              <span className="text-blue-700">scored honestly.</span>
            </h1>
            <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
              Upload your resume, paste a job description, and see exactly how
              well they match: what&apos;s missing, what to add, and AI
              suggestions to close the gap.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Link href="/signup" className={cn(buttonVariants({ size: "lg" }), "bg-blue-700 hover:bg-blue-800")}>
                Check my match <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
              <Link href="/#how-it-works" className={buttonVariants({ size: "lg", variant: "outline" })}>
                See how it works
              </Link>
            </div>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-2 text-sm text-muted-foreground">
              <Badge variant="outline">60% semantic fit</Badge>
              <Badge variant="outline">40% keyword coverage</Badge>
              <Badge variant="outline">Missing skills, named</Badge>
              <Badge variant="outline">AI bullet rewrites</Badge>
              <Badge variant="outline">PDF match report</Badge>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 className="text-center text-2xl font-bold tracking-tight sm:text-3xl">
            Three steps to your score
          </h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {steps.map((step, index) => (
              <Card key={step.title}>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-700/10 text-blue-700">
                      <step.icon className="h-5 w-5" />
                    </span>
                    <span className="text-sm font-medium text-muted-foreground">
                      Step {index + 1}
                    </span>
                  </div>
                  <CardTitle className="mt-2">{step.title}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {step.text}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* What you get */}
        <section className="border-y bg-muted/40">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
            <h2 className="text-center text-2xl font-bold tracking-tight sm:text-3xl">
              Not just a number — a breakdown you can act on
            </h2>
            <div className="mt-10 grid gap-6 sm:grid-cols-2">
              {resultCards.map((card) => (
                <Card key={card.title} className="bg-background">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-700/10 text-blue-700">
                        <card.icon className="h-5 w-5" />
                      </span>
                      <CardTitle>{card.title}</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    {card.text}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Roadmap — honest about what is live vs next. */}
        <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <div className="text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
              The matcher is live. The studio is coming.
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-muted-foreground">
              We&apos;re building the full resume studio around the matcher —
              in the open, one phase at a time.
            </p>
          </div>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {roadmapItems.map((item) => (
              <Card key={item.title}>
                <CardHeader>
                  <Badge variant="secondary" className="w-fit">
                    In the roadmap
                  </Badge>
                  <CardTitle className="mt-2 text-base">{item.title}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {item.text}
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="mt-12 text-center">
            <Link href="/signup" className={cn(buttonVariants({ size: "lg" }), "bg-blue-700 hover:bg-blue-800")}>
              Start with your first match <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 text-sm text-muted-foreground sm:flex-row sm:px-6">
          <span>AI Resume Matcher — built in public, one phase at a time.</span>
          <span>Your resume is yours: we never sell your data.</span>
        </div>
      </footer>
    </div>
  );
}
