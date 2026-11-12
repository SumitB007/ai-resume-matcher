"use client";

// App-wide client providers.
// TanStack Query owns all *server* state (resumes, jobs, matches, analytics):
// caching, background refetch, and the status polling the matcher needs.
// There is deliberately no Redux store (decisions.md §11.6) — the only true
// client state in this phase is form/editor state, which lives in components.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { Toaster } from "@/components/ui/sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster richColors position="top-center" />
    </QueryClientProvider>
  );
}
