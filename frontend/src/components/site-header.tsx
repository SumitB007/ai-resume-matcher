import { FileSearch } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 font-semibold">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-700 text-white">
        <FileSearch className="h-4.5 w-4.5" />
      </span>
      AI Resume Matcher
    </Link>
  );
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
          <Link href="/#how-it-works" className="hover:text-foreground">
            How it works
          </Link>
          <Link href="/resume-checker" className="hover:text-foreground">
            Resume checker
          </Link>
          <Link href="/templates" className="hover:text-foreground">
            Templates
          </Link>
          <Link href="/examples" className="hover:text-foreground">
            Examples
          </Link>
          <Link href="/cover-letter" className="hover:text-foreground">
            Cover letters
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          <Link href="/login" className={buttonVariants({ variant: "ghost" })}>
            Log in
          </Link>
          <Link href="/signup" className={cn(buttonVariants(), "bg-blue-700 hover:bg-blue-800")}>
            Get started
          </Link>
        </div>
      </div>
    </header>
  );
}
