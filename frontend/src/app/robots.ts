import type { MetadataRoute } from "next";

import { SITE_URL } from "@/components/json-ld";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // App, auth, print, and API surfaces aren't public content.
        disallow: ["/app/", "/api/", "/print/", "/login", "/signup"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
