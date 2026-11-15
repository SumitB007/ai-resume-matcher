import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { faqLd, JsonLd, SITE_URL } from "@/components/json-ld";
import { ResumePreview } from "@/components/resume-preview";
import { SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getRoleExample, getTemplateInfo, ROLE_EXAMPLES } from "@/lib/sample-data";
import { cn } from "@/lib/utils";

export function generateStaticParams() {
  return ROLE_EXAMPLES.map((r) => ({ role: r.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ role: string }>;
}): Promise<Metadata> {
  const { role } = await params;
  const example = getRoleExample(role);
  if (!example) return {};
  return {
    title: example.headline,
    description: example.intro,
    openGraph: {
      title: example.headline,
      description: example.intro,
      url: `${SITE_URL}/examples/${example.slug}`,
    },
  };
}

export default async function ExamplePage({
  params,
}: {
  params: Promise<{ role: string }>;
}) {
  const { role } = await params;
  const example = getRoleExample(role);
  if (!example) notFound();

  const template = getTemplateInfo(example.templateId);
  const faqs = [
    {
      q: `What skills should a ${example.role.toLowerCase()} resume include?`,
      a: `Postings for this role most often screen for: ${example.scoredOn.join(", ")}. Include the ones you genuinely have, worded the way the posting words them — matching is literal.`,
    },
    {
      q: "Is this a real person's resume?",
      a: "No — it's a hand-written sample with a fictional person and companies, built to show structure, wording, and the level of detail that scores well. Your own resume should use your real facts and your real numbers.",
    },
    {
      q: "Can I start from this example?",
      a: "Yes — the builder's templates produce exactly this layout. Sign up free, pick the template, and write your own content into the same structure. Never copy sample bullets as your own experience.",
    },
  ];

  return (
    <div className="flex min-h-screen flex-col">
      <JsonLd data={faqLd(faqs)} />
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6">
        <Link href="/templates" className="text-sm text-blue-700 hover:underline">
          ← Templates
        </Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight">{example.headline}</h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">{example.intro}</p>

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_380px]">
          <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
            <ResumePreview content={example.content} templateId={example.templateId} />
            <p className="border-t px-4 py-2 text-center text-xs text-muted-foreground">
              Sample resume — fictional person, real structure. Rendered in the{" "}
              {template?.label ?? example.templateId} template.
            </p>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">What this role is scored on</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1.5">
                  {example.scoredOn.map((skill) => (
                    <Badge key={skill} variant="secondary">
                      {skill}
                    </Badge>
                  ))}
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  The skills job descriptions for this role name most — and
                  keyword screens look for, verbatim.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Make yours score like this</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-inside list-disc space-y-1.5 text-sm">
                  {example.tips.map((tip) => (
                    <li key={tip}>{tip}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card className="border-blue-200 bg-blue-50/60">
              <CardContent className="space-y-3 py-5 text-center">
                <p className="font-medium">Check your own resume — free</p>
                <p className="text-sm text-muted-foreground">
                  Run the ATS checker with no account, or match your resume
                  against a real job description for a full score.
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  <Link href="/resume-checker" className={cn(buttonVariants(), "bg-blue-700 hover:bg-blue-800")}>
                    Free ATS check
                  </Link>
                  <Link href="/signup" className={cn(buttonVariants({ variant: "outline" }))}>
                    Match a job
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="mt-12 max-w-3xl">
          <h2 className="text-lg font-semibold">Questions</h2>
          <div className="mt-4 space-y-5">
            {faqs.map((f) => (
              <div key={f.q}>
                <p className="font-medium">{f.q}</p>
                <p className="mt-1 text-sm text-muted-foreground">{f.a}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12">
          <h2 className="text-lg font-semibold">More examples</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {ROLE_EXAMPLES.filter((r) => r.slug !== example.slug).map((r) => (
              <Link
                key={r.slug}
                href={`/examples/${r.slug}`}
                className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
              >
                {r.role}
              </Link>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
