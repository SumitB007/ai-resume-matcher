import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { JsonLd, SITE_URL } from "@/components/json-ld";
import { ResumePreview } from "@/components/resume-preview";
import { SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getTemplateInfo,
  sampleContentForTemplate,
  TEMPLATE_INFO,
} from "@/lib/sample-data";
import { cn } from "@/lib/utils";

export function generateStaticParams() {
  return TEMPLATE_INFO.map((t) => ({ id: t.id }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const info = getTemplateInfo(id);
  if (!info) return {};
  return {
    title: `${info.label} resume template — ${info.tagline}`,
    description: info.description,
    openGraph: {
      title: `${info.label} resume template`,
      description: info.tagline,
      url: `${SITE_URL}/templates/${info.id}`,
    },
  };
}

export default async function TemplatePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const info = getTemplateInfo(id);
  if (!info) notFound();

  const others = TEMPLATE_INFO.filter((t) => t.id !== info.id);

  return (
    <div className="flex min-h-screen flex-col">
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "WebPage",
          name: `${info.label} resume template`,
          url: `${SITE_URL}/templates/${info.id}`,
          description: info.description,
        }}
      />
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6">
        <Link href="/templates" className="text-sm text-blue-700 hover:underline">
          ← All templates
        </Link>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{info.label}</h1>
          <Badge variant="secondary">{info.tagline}</Badge>
        </div>
        <p className="mt-3 max-w-2xl text-muted-foreground">{info.description}</p>

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_380px]">
          <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
            <ResumePreview
              content={sampleContentForTemplate(info.id)}
              templateId={info.id}
            />
            <p className="border-t px-4 py-2 text-center text-xs text-muted-foreground">
              Sample document rendered live in the {info.label} template — your
              content, same output.
            </p>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Who it&apos;s for</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-inside list-disc space-y-1.5 text-sm">
                  {info.bestFor.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">ATS notes</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-inside list-disc space-y-1.5 text-sm">
                  {info.atsNotes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card className="border-blue-200 bg-blue-50/60">
              <CardContent className="py-5 text-center">
                <p className="font-medium">Use this template free</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Import your current resume or start blank — switch templates
                  any time without losing content.
                </p>
                <Link
                  href="/signup"
                  className={cn(buttonVariants(), "mt-4 bg-blue-700 hover:bg-blue-800")}
                >
                  Start building
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="mt-12">
          <h2 className="text-lg font-semibold">Other templates</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {others.map((t) => (
              <Link
                key={t.id}
                href={`/templates/${t.id}`}
                className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
              >
                {t.label}
              </Link>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
