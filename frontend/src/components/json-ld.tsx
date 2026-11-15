// Structured data (Phase 7). Server-rendered JSON-LD — kept as data, never
// string-built HTML, so it stays valid by construction.
export function JsonLd({ data }: { data: Record<string, unknown> | Record<string, unknown>[] }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export function webApplicationLd() {
  return {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    name: "AI Resume Matcher",
    url: SITE_URL,
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    description:
      "Check your resume against any job description: hybrid match score, missing keywords, ATS readiness checks, a resume builder with ATS-safe templates, and cover letters generated from your own experience.",
    offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
  };
}

export function faqLd(faqs: Array<{ q: string; a: string }>) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((f) => ({
      "@type": "Question",
      name: f.q,
      acceptedAnswer: { "@type": "Answer", text: f.a },
    })),
  };
}
