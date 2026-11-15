import type { Metadata } from "next";
import Link from "next/link";

import { SiteHeader } from "@/components/site-header";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ROLE_EXAMPLES } from "@/lib/sample-data";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Resume examples by role",
  description:
    "Hand-written sample resumes for backend, frontend, data, and DevOps engineers and new graduates — each with the skills the role is scored on and the tips that make the difference.",
};

export default function ExamplesPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6">
        <div className="max-w-2xl">
          <h1 className="text-3xl font-bold tracking-tight">Resume examples by role</h1>
          <p className="mt-3 text-muted-foreground">
            Fictional people, real structure. Each example shows the layout,
            the wording level, and the skills that role&apos;s job descriptions
            actually screen for — then links you to the free checker to score
            your own.
          </p>
        </div>
        <div className="mt-10 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {ROLE_EXAMPLES.map((example) => (
            <Card key={example.slug}>
              <CardHeader>
                <CardTitle className="text-base">{example.headline}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="line-clamp-3 text-sm text-muted-foreground">{example.intro}</p>
                <Link
                  href={`/examples/${example.slug}`}
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                >
                  View the example
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}
