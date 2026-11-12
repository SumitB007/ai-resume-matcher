import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output: the Docker runner image ships only the self-contained
  // server bundle (see frontend/Dockerfile, decisions.md §11.4).
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
