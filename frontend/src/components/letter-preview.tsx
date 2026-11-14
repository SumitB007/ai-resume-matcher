"use client";

// Cover-letter renderer (Phase 14): the same six visual identities as the
// resume templates, adapted to a letter layout — a letter that matches its
// resume is the behaviour users value (roadmap §8). One component powers the
// editor preview, the public samples, and the print route.

import type { DocTheme, LetterContent } from "@/lib/api/types";
import { cn } from "@/lib/utils";

function senderBits(content: LetterContent): string[] {
  const s = content.sender;
  return [s.email, s.phone, s.location].filter((x) => x && x.trim());
}

function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

export function LetterPreview({
  content,
  templateId,
  theme,
}: {
  content: LetterContent;
  templateId: string;
  theme?: DocTheme;
}) {
  const accent = theme?.accent || "#1d4ed8";
  const compact = theme?.density === "compact" || templateId === "compact-tech";
  const s = content.sender;
  const r = content.recipient;
  const bits = senderBits(content);

  const body = (
    <>
      <div className={compact ? "space-y-3" : "space-y-4"}>
        <p>{formatDate(content.date)}</p>
        {(r.name || r.company) && (
          <div>
            {r.name && <p className="font-medium">{r.name}</p>}
            {r.company && <p>{r.company}</p>}
          </div>
        )}
        <p>{content.greeting || "Dear Hiring Manager,"}</p>
        {content.paragraphs.map((paragraph, i) => (
          <p key={i}>{paragraph}</p>
        ))}
        <div>
          <p>{content.closing || "Sincerely,"}</p>
          <p className="mt-6 font-semibold">{content.signature_name || s.name}</p>
        </div>
      </div>
    </>
  );

  const rootClass = cn(
    "bg-white text-neutral-900",
    theme?.font === "serif" ? "font-serif" : "font-sans",
    compact ? "p-7 text-[12.5px] leading-snug" : "p-10 text-[14px] leading-relaxed",
  );

  if (templateId === "sidebar") {
    return (
      <div className={cn(rootClass, "flex gap-0 !p-0")}>
        <aside
          className={cn("w-[30%] shrink-0", compact ? "p-5" : "p-7")}
          style={{ backgroundColor: `${accent}14` }}
        >
          <h1 className="text-[1.4em] leading-tight font-bold" style={{ color: accent }}>
            {s.name || "Your name"}
          </h1>
          {s.title && <p className="mt-0.5 opacity-80">{s.title}</p>}
          {bits.length > 0 && (
            <ul className="mt-5 space-y-1 break-words">
              {bits.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          )}
        </aside>
        <main className={cn("flex-1", compact ? "p-5" : "p-7")}>{body}</main>
      </div>
    );
  }

  const centered = templateId === "classic" || templateId === "graduate";
  return (
    <div className={rootClass}>
      <header
        className={cn(
          centered && "text-center",
          templateId === "classic" && "border-b pb-4",
          templateId === "modern" && "border-b-2 pb-4",
        )}
        style={
          templateId === "classic"
            ? { borderColor: accent }
            : templateId === "modern"
              ? { borderColor: accent }
              : undefined
        }
      >
        <h1
          className="text-[1.7em] leading-tight font-bold"
          style={templateId === "modern" || templateId === "graduate" ? { color: accent } : undefined}
        >
          {templateId === "compact-tech" ? (
            <span className="font-mono">{s.name || "Your name"}</span>
          ) : (
            s.name || "Your name"
          )}
        </h1>
        {s.title && <p className="mt-0.5 text-[1.05em] opacity-85">{s.title}</p>}
        {bits.length > 0 && (
          <p className={cn("mt-1.5 text-[0.9em] opacity-75", centered && "mx-auto")}>
            {bits.join(" | ")}
          </p>
        )}
      </header>
      <div className="mt-6">{body}</div>
    </div>
  );
}
