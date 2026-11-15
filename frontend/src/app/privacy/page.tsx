import type { Metadata } from "next";
import Link from "next/link";

import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "Privacy policy",
  description:
    "What AI Resume Matcher stores, what it never does, and how to delete everything. Written from the actual system, not a template.",
};

// This policy describes the system as it actually behaves (Phase 8). If a
// behaviour changes, this page changes in the same PR.
const SECTIONS: Array<{ title: string; body: string[] }> = [
  {
    title: "What we store when you create an account",
    body: [
      "Your email address, an optional name, and a hashed password (bcrypt — we never store or see your actual password).",
      "The resumes you upload: we extract and store the text and the skills we detect in it. The original file is parsed in memory; matching and feedback work from the extracted text.",
      "The job descriptions you save, your match results and scores, your builder documents, cover letters, and ATS check results — the working data of the product, tied to your account.",
    ],
  },
  {
    title: "The anonymous ATS checker stores nothing",
    body: [
      "The free resume checker on our home page works without an account. Your file is parsed in memory, checked, and the result is returned to your browser. The file, its text, and the result are never written to our database.",
    ],
  },
  {
    title: "How AI processing works",
    body: [
      "When an AI model is configured on our side, the text needed for a feature (for example your bullet points, or your resume and a job description for feedback) is sent to the model provider (OpenRouter) over an encrypted connection to generate the response. We do not control that provider's own data handling; their policy applies to that processing.",
      "When no model is configured, features run on local, deterministic fallbacks — nothing leaves our servers, and the product tells you when a result was generated offline.",
      "We never use your resume to train models, and we never sell or rent your data to anyone. There are no advertising trackers on this site.",
    ],
  },
  {
    title: "Cookies",
    body: [
      "One essential cookie keeps you signed in (an httpOnly session token). That's it — no analytics cookies, no marketing cookies.",
    ],
  },
  {
    title: "Deleting your data",
    body: [
      "Settings → Delete account removes your account and all of its data — resumes and their extracted text, jobs, matches, documents, cover letters, and ATS results — in a single transaction. There is no recovery and no retained copy kept for 'just in case'.",
      "If you can't sign in and want your data deleted, contact us from the email address on the account and we'll verify and delete it manually.",
    ],
  },
  {
    title: "Security practices",
    body: [
      "Passwords are bcrypt-hashed; sessions are signed tokens with a 24-hour expiry; sign-in and the anonymous checker are rate-limited per IP; AI features carry a per-user daily cap. The API only accepts requests from this website's own origin.",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12 sm:px-6">
        <h1 className="text-3xl font-bold tracking-tight">Privacy policy</h1>
        <p className="mt-3 text-muted-foreground">
          Your resume is one of the most personal documents you own. This page
          describes — plainly, and matching how the system actually behaves —
          what we keep, what we never do, and how to make us forget all of it.
        </p>
        <div className="mt-10 space-y-10">
          {SECTIONS.map((section) => (
            <section key={section.title}>
              <h2 className="text-lg font-semibold">{section.title}</h2>
              {section.body.map((paragraph) => (
                <p key={paragraph.slice(0, 40)} className="mt-2 text-sm leading-6 text-muted-foreground">
                  {paragraph}
                </p>
              ))}
            </section>
          ))}
        </div>
        <p className="mt-12 text-sm text-muted-foreground">
          Ready to check your resume?{" "}
          <Link href="/resume-checker" className="font-medium text-blue-700 hover:underline">
            The free checker stores nothing
          </Link>{" "}
          — or{" "}
          <Link href="/signup" className="font-medium text-blue-700 hover:underline">
            create an account
          </Link>{" "}
          for matching, the builder, and cover letters.
        </p>
      </main>
    </div>
  );
}
