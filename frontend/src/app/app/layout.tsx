"use client";

// Signed-in app shell: sidebar navigation + user bar.
// The proxy (src/proxy.ts) already redirected anonymous visitors away; this
// layout additionally verifies the session with /api/auth/me and bounces to
// /login on a 401 (expired token), so the UI never renders a dead session.

import {
  Briefcase,
  FileText,
  History,
  LayoutDashboard,
  Loader2,
  LogOut,
  ScanSearch,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

import { Logo } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api/client";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/app", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/app/match", label: "Job Matcher", icon: ScanSearch, exact: false },
  { href: "/app/resumes", label: "My Resumes", icon: FileText, exact: false },
  { href: "/app/jobs", label: "Saved Jobs", icon: Briefcase, exact: false },
  { href: "/app/matches", label: "Match History", icon: History, exact: false },
];

export default function AppLayout({ children }: LayoutProps<"/app">) {
  const pathname = usePathname();
  const router = useRouter();

  const meQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: api.me,
    retry: false,
  });

  useEffect(() => {
    if (meQuery.error instanceof ApiError && meQuery.error.status === 401) {
      router.replace("/login");
    }
  }, [meQuery.error, router]);

  async function handleLogout() {
    await api.logout();
    router.replace("/");
    router.refresh();
  }

  return (
    <div className="flex min-h-full flex-col lg:flex-row">
      <aside className="flex w-full shrink-0 flex-col border-b bg-muted/30 lg:min-h-screen lg:w-64 lg:border-r lg:border-b-0">
        <div className="flex h-16 items-center justify-between px-4 lg:px-6">
          <Logo />
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={handleLogout}
            aria-label="Log out"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:px-3 lg:pb-0">
          {navItems.map((item) => {
            const active = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors",
                  active
                    ? "bg-blue-700/10 text-blue-800"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto hidden items-center justify-between gap-2 border-t px-4 py-3 lg:flex lg:px-6">
          <span className="truncate text-sm text-muted-foreground">
            {meQuery.data?.email ?? "…"}
          </span>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            <LogOut className="mr-1.5 h-4 w-4" /> Log out
          </Button>
        </div>
      </aside>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
        {meQuery.isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          children
        )}
      </main>
    </div>
  );
}
