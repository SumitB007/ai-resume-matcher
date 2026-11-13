"use client";

// Resume template renderer (Phase 13). ONE component renders the structured
// document in six original template designs. Every template renders real,
// selectable text in reading order — the ATS-safety rules from the roadmap:
// no text in images, no layout tricks that scramble extraction order (the
// sidebar template keeps contact/skills in the DOM before experience only in
// visual order via flex; the flattened pipeline text comes from the backend
// flattener, not from this DOM, so print layout can never corrupt parsing).
//
// The same component powers the editor's live preview and the /print route,
// so what the user sees is exactly what prints.

import type { DocumentContent, DocTheme } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface P {
  content: DocumentContent;
  templateId: string;
  theme?: DocTheme;
}

function contactBits(content: DocumentContent): string[] {
  const p = content.personal;
  return [p.email, p.phone, p.location, ...(p.links ?? [])].filter(
    (x) => x && x.trim(),
  );
}

function dateRange(start: string, end: string, current?: boolean): string {
  const parts = [start, current ? "Present" : end].filter((x) => x && x.trim());
  return parts.join(" – ");
}

function ExperienceList({ content, compact }: { content: DocumentContent; compact?: boolean }) {
  return (
    <div className={compact ? "space-y-2.5" : "space-y-3.5"}>
      {content.experience.map((job, i) => (
        <div key={i}>
          <div className="flex items-baseline justify-between gap-3">
            <p className="font-semibold">
              {job.role}
              {job.company && <span className="font-normal"> · {job.company}</span>}
            </p>
            <p className="shrink-0 text-[0.85em] opacity-70">
              {dateRange(job.start, job.end, job.current)}
            </p>
          </div>
          {job.location && <p className="text-[0.85em] opacity-70">{job.location}</p>}
          {job.bullets.length > 0 && (
            <ul className="mt-1 list-disc space-y-0.5 pl-5">
              {job.bullets.map((b, j) => (
                <li key={j}>{b}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

function EducationList({ content }: { content: DocumentContent }) {
  return (
    <div className="space-y-2">
      {content.education.map((edu, i) => (
        <div key={i} className="flex items-baseline justify-between gap-3">
          <p>
            <span className="font-medium">
              {[edu.degree, edu.field].filter(Boolean).join(", ")}
            </span>
            {edu.school && <span> · {edu.school}</span>}
          </p>
          <p className="shrink-0 text-[0.85em] opacity-70">{dateRange(edu.start, edu.end)}</p>
        </div>
      ))}
    </div>
  );
}

function SkillsText({ content }: { content: DocumentContent }) {
  return (
    <div className="space-y-1">
      {content.skills.groups.map((g, i) => (
        <p key={i}>
          {g.label && <span className="font-medium">{g.label}: </span>}
          {g.items.join(", ")}
        </p>
      ))}
    </div>
  );
}

function ProjectsList({ content }: { content: DocumentContent }) {
  return (
    <div className="space-y-3">
      {content.projects.map((project, i) => (
        <div key={i}>
          <p className="font-semibold">{project.name}</p>
          {project.description && <p>{project.description}</p>}
          {project.bullets.length > 0 && (
            <ul className="mt-1 list-disc space-y-0.5 pl-5">
              {project.bullets.map((b, j) => (
                <li key={j}>{b}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

function Section({
  title, children, variant, accent,
}: {
  title: string;
  children: React.ReactNode;
  variant: string;
  accent: string;
}) {
  if (!children) return null;
  const titleEl = (() => {
    switch (variant) {
      case "classic":
        return (
          <h2 className="mb-2 border-b pb-1 text-[1.05em] font-bold tracking-widest uppercase" style={{ borderColor: accent }}>
            {title}
          </h2>
        );
      case "modern":
        return (
          <h2 className="mb-2 flex items-center gap-2 text-[1.05em] font-bold tracking-wide uppercase" style={{ color: accent }}>
            <span className="inline-block h-3.5 w-1 rounded" style={{ backgroundColor: accent }} />
            {title}
          </h2>
        );
      case "minimal":
        return <h2 className="mb-2 text-[0.85em] font-medium tracking-[0.2em] uppercase opacity-60">{title}</h2>;
      case "compact-tech":
        return (
          <h2 className="mb-1.5 font-mono text-[1em] font-bold uppercase" style={{ color: accent }}>
            {"// "}{title}
          </h2>
        );
      default:
        return (
          <h2 className="mb-2 border-b border-neutral-300 pb-1 text-[1.05em] font-bold tracking-widest uppercase">
            {title}
          </h2>
        );
    }
  })();
  return (
    <section className="mt-4 first:mt-0">
      {titleEl}
      {children}
    </section>
  );
}

const has = {
  summary: (c: DocumentContent) => Boolean(c.summary.trim()),
  experience: (c: DocumentContent) => c.experience.length > 0,
  education: (c: DocumentContent) => c.education.length > 0,
  skills: (c: DocumentContent) => c.skills.groups.some((g) => g.items.length > 0),
  projects: (c: DocumentContent) => c.projects.length > 0,
  certifications: (c: DocumentContent) => c.certifications.length > 0,
  languages: (c: DocumentContent) => c.languages.length > 0,
};

function MainSections({ content, variant, accent }: { content: DocumentContent; variant: string; accent: string }) {
  const compact = variant === "compact-tech";
  return (
    <>
      {has.summary(content) && (
        <Section title="Summary" variant={variant} accent={accent}>
          <p>{content.summary}</p>
        </Section>
      )}
      {has.experience(content) && (
        <Section title="Experience" variant={variant} accent={accent}>
          <ExperienceList content={content} compact={compact} />
        </Section>
      )}
      {has.projects(content) && (
        <Section title="Projects" variant={variant} accent={accent}>
          <ProjectsList content={content} />
        </Section>
      )}
      {variant !== "sidebar" && has.skills(content) && (
        <Section title="Skills" variant={variant} accent={accent}>
          <SkillsText content={content} />
        </Section>
      )}
      {has.education(content) && (
        <Section title="Education" variant={variant} accent={accent}>
          <EducationList content={content} />
        </Section>
      )}
      {has.certifications(content) && (
        <Section title="Certifications" variant={variant} accent={accent}>
          <p>{content.certifications.join(" · ")}</p>
        </Section>
      )}
      {has.languages(content) && (
        <Section title="Languages" variant={variant} accent={accent}>
          <p>{content.languages.join(", ")}</p>
        </Section>
      )}
      {content.custom_sections.map(
        (s, i) =>
          s.items.length > 0 && (
            <Section key={i} title={s.title || "Additional"} variant={variant} accent={accent}>
              <ul className="list-disc space-y-0.5 pl-5">
                {s.items.map((item, j) => (
                  <li key={j}>{item}</li>
                ))}
              </ul>
            </Section>
          ),
      )}
    </>
  );
}

export function ResumePreview({ content, templateId, theme }: P) {
  const accent = theme?.accent || "#1d4ed8";
  const density = theme?.density || "normal";
  const compactAll = density === "compact" || templateId === "compact-tech";
  const p = content.personal;
  const bits = contactBits(content);

  const rootClass = cn(
    "bg-white text-neutral-900",
    theme?.font === "serif" ? "font-serif" : "font-sans",
    compactAll ? "p-7 text-[12.5px] leading-snug" : "p-10 text-[14px] leading-relaxed",
  );

  if (templateId === "sidebar") {
    return (
      <div className={cn(rootClass, "flex gap-0 !p-0")}>
        <aside
          className={cn("w-[31%] shrink-0 space-y-5", compactAll ? "p-5" : "p-7")}
          style={{ backgroundColor: `${accent}14` }}
        >
          <div>
            <h1 className="text-[1.5em] leading-tight font-bold" style={{ color: accent }}>
              {p.full_name || "Your name"}
            </h1>
            {p.title && <p className="mt-0.5 opacity-80">{p.title}</p>}
          </div>
          {bits.length > 0 && (
            <div>
              <h2 className="mb-1.5 text-[0.85em] font-bold tracking-widest uppercase" style={{ color: accent }}>
                Contact
              </h2>
              <ul className="space-y-1 break-words">
                {bits.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </div>
          )}
          {has.skills(content) && (
            <div>
              <h2 className="mb-1.5 text-[0.85em] font-bold tracking-widest uppercase" style={{ color: accent }}>
                Skills
              </h2>
              <SkillsText content={content} />
            </div>
          )}
          {has.education(content) && (
            <div>
              <h2 className="mb-1.5 text-[0.85em] font-bold tracking-widest uppercase" style={{ color: accent }}>
                Education
              </h2>
              <EducationList content={content} />
            </div>
          )}
          {has.languages(content) && (
            <div>
              <h2 className="mb-1.5 text-[0.85em] font-bold tracking-widest uppercase" style={{ color: accent }}>
                Languages
              </h2>
              <p>{content.languages.join(", ")}</p>
            </div>
          )}
        </aside>
        <main className={cn("flex-1", compactAll ? "p-5" : "p-7")}>
          {has.summary(content) && (
            <Section title="Summary" variant="modern" accent={accent}>
              <p>{content.summary}</p>
            </Section>
          )}
          {has.experience(content) && (
            <Section title="Experience" variant="modern" accent={accent}>
              <ExperienceList content={content} compact={compactAll} />
            </Section>
          )}
          {has.projects(content) && (
            <Section title="Projects" variant="modern" accent={accent}>
              <ProjectsList content={content} />
            </Section>
          )}
          {has.certifications(content) && (
            <Section title="Certifications" variant="modern" accent={accent}>
              <p>{content.certifications.join(" · ")}</p>
            </Section>
          )}
        </main>
      </div>
    );
  }

  const centered = templateId === "classic" || templateId === "graduate";
  return (
    <div className={rootClass}>
      <header className={centered ? "text-center" : undefined}>
        <h1
          className="text-[1.9em] leading-tight font-bold"
          style={templateId === "modern" ? { color: accent } : undefined}
        >
          {p.full_name || "Your name"}
        </h1>
        {p.title && (
          <p className={cn("mt-0.5 text-[1.1em]", templateId === "minimal" && "font-light opacity-80")}>
            {p.title}
          </p>
        )}
        {bits.length > 0 && (
          <p className={cn("mt-1.5 text-[0.9em] opacity-75", centered && "mx-auto")}>
            {bits.join(" | ")}
          </p>
        )}
      </header>
      <div className="mt-5">
        {templateId === "graduate" ? (
          <>
            {has.education(content) && (
              <Section title="Education" variant="classic" accent={accent}>
                <EducationList content={content} />
              </Section>
            )}
            {has.summary(content) && (
              <Section title="Summary" variant="classic" accent={accent}>
                <p>{content.summary}</p>
              </Section>
            )}
            {has.experience(content) && (
              <Section title="Experience" variant="classic" accent={accent}>
                <ExperienceList content={content} />
              </Section>
            )}
            {has.projects(content) && (
              <Section title="Projects" variant="classic" accent={accent}>
                <ProjectsList content={content} />
              </Section>
            )}
            {has.skills(content) && (
              <Section title="Skills" variant="classic" accent={accent}>
                <SkillsText content={content} />
              </Section>
            )}
          </>
        ) : (
          <MainSections content={content} variant={templateId} accent={accent} />
        )}
      </div>
    </div>
  );
}

/** A4 page frame (210mm wide) used by editor preview and the print route. */
export function A4Page({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="resume-a4 mx-auto bg-white shadow-md ring-1 ring-black/5"
      style={{ width: "210mm", minHeight: "297mm" }}
    >
      {children}
    </div>
  );
}
