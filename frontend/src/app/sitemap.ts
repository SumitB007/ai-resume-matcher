import type { MetadataRoute } from "next";

import { SITE_URL } from "@/components/json-ld";
import { ROLE_EXAMPLES, TEMPLATE_INFO } from "@/lib/sample-data";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE_URL}/resume-checker`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${SITE_URL}/cover-letter`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${SITE_URL}/templates`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${SITE_URL}/examples`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${SITE_URL}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
  ];
  const templateRoutes: MetadataRoute.Sitemap = TEMPLATE_INFO.map((t) => ({
    url: `${SITE_URL}/templates/${t.id}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.7,
  }));
  const exampleRoutes: MetadataRoute.Sitemap = ROLE_EXAMPLES.map((r) => ({
    url: `${SITE_URL}/examples/${r.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.7,
  }));
  return [...staticRoutes, ...templateRoutes, ...exampleRoutes];
}
