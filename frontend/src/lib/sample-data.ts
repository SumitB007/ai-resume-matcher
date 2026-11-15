// Sample content for the public SEO surface (Phase 7).
//
// Everything here is fictional and illustrative — sample people, sample
// companies — written by hand for the examples/templates pages. Pages that
// render this data label it "Sample". The documents use the builder's real
// DocumentContent shape and render through the real ResumePreview, so what
// a visitor sees is exactly what the builder produces.

import type { DocumentContent } from "@/lib/api/types";

export interface TemplateInfo {
  id: string;
  label: string;
  tagline: string;
  description: string;
  bestFor: string[];
  atsNotes: string[];
  sampleRole: string; // key into ROLE_EXAMPLES used for the live preview
}

export const TEMPLATE_INFO: TemplateInfo[] = [
  {
    id: "classic",
    label: "Classic",
    tagline: "The safe pair of hands",
    description:
      "A traditional single-column layout with serif headings and clear section rules. Recruiters in finance, law, healthcare, and large enterprises have read this shape for decades — nothing to learn, nothing to trip over.",
    bestFor: ["Finance & banking", "Law & consulting", "Healthcare", "Large enterprises", "Career changers with long histories"],
    atsNotes: [
      "Single column, standard headings — every major ATS parses it cleanly.",
      "No tables, icons, or text boxes anywhere in the layout.",
      "Chronological order with explicit dates, the way parsers expect.",
    ],
    sampleRole: "backend-developer",
  },
  {
    id: "modern",
    label: "Modern",
    tagline: "Clean, current, quietly confident",
    description:
      "Sans-serif type, a restrained accent colour, and generous spacing. The default recommendation for tech and product roles: contemporary without being decorative, and still a single linear column under the hood.",
    bestFor: ["Software engineering", "Product management", "Design & UX", "Startups & scale-ups", "Marketing"],
    atsNotes: [
      "Accent colour is cosmetic only — all text is real, selectable text.",
      "Section order follows the convention parsers weight most: summary, experience, skills, education.",
      "Links are printed as plain URLs, so nothing is lost in plain-text extraction.",
    ],
    sampleRole: "frontend-developer",
  },
  {
    id: "compact-tech",
    label: "Compact Tech",
    tagline: "Maximum signal per page",
    description:
      "A dense layout built for senior engineers whose problem is fitting ten years of real work into two pages. Smaller type, tighter leading, skills grouped up top where technical screeners look first.",
    bestFor: ["Senior & staff engineers", "DevOps & SRE", "Data engineers", "Anyone over one page and proud of it"],
    atsNotes: [
      "Density comes from spacing, not from columns or tables — parsing stays linear.",
      "Grouped skills use standard category labels (Languages, Frameworks, Cloud & DevOps).",
      "Keep bullets achievement-shaped; at this density, duty lists read as noise.",
    ],
    sampleRole: "devops-engineer",
  },
  {
    id: "sidebar",
    label: "Two-Column Sidebar",
    tagline: "Skills first, story second",
    description:
      "A left rail carries contact details, skills, and certifications while the main column tells the experience story. Striking for human readers — and the one template where you should read the ATS notes before choosing it.",
    bestFor: ["Consultants", "Freelancers", "Roles hired through referrals", "Portfolio-led applications"],
    atsNotes: [
      "Honest warning: some older ATS parsers read columns out of order. Our export keeps the DOM in reading order, which modern parsers (Workday, Greenhouse, Lever) handle — legacy systems may not.",
      "If a posting says 'upload a simple resume', pick Classic or Modern instead.",
      "Never put critical keywords only in the sidebar; repeat them in experience bullets.",
    ],
    sampleRole: "data-engineer",
  },
  {
    id: "minimal",
    label: "Minimal",
    tagline: "Nothing on the page that isn't earning its place",
    description:
      "No accent colour, no rules, no decoration — just type, space, and your work. Favoured by designers and writers whose portfolios speak elsewhere, and by anyone who believes content is the design.",
    bestFor: ["Designers", "Writers & editors", "Researchers", "Minimalists applying anywhere"],
    atsNotes: [
      "The most parser-friendly layout we ship: one column, no styling tricks at all.",
      "Works entirely in black and white — prints perfectly on any printer.",
      "Because nothing decorates it, weak bullets have nowhere to hide. Edit ruthlessly.",
    ],
    sampleRole: "frontend-developer",
  },
  {
    id: "graduate",
    label: "Graduate",
    tagline: "Built for first jobs",
    description:
      "Education and projects lead, experience follows — because for a new graduate, coursework, internships, and projects ARE the evidence. Links to GitHub and portfolio sit directly under the name.",
    bestFor: ["New graduates", "Internship applicants", "Career switchers with project work", "Bootcamp graduates"],
    atsNotes: [
      "Projects are formatted as structured entries (name, description, bullets) so parsers file them correctly.",
      "Put the skills from the job posting in the skills groups — new-grad resumes are keyword-screened hardest.",
      "One page, enforced by the layout's spacing. Cut coursework before you cut projects.",
    ],
    sampleRole: "graduate-engineer",
  },
];

export interface RoleExample {
  slug: string;
  role: string;
  headline: string;
  intro: string;
  scoredOn: string[];
  tips: string[];
  templateId: string;
  content: DocumentContent;
}

const backendContent: DocumentContent = {
  personal: {
    full_name: "Aarav Sharma",
    title: "Senior Backend Developer",
    email: "aarav.sharma@example.com",
    phone: "+91 98200 12345",
    location: "Bengaluru, IN",
    links: ["github.com/aaravsharma", "linkedin.com/in/aaravsharma"],
  },
  summary:
    "Senior backend developer with 6 years building payment and logistics APIs in Python. Owns services end to end — design, build, deploy, on-call — with a track record of cutting latency and failure rates on high-traffic systems.",
  experience: [
    {
      role: "Senior Backend Developer",
      company: "Finlytics",
      location: "Bengaluru",
      start: "2022",
      end: "Present",
      current: true,
      bullets: [
        "Built a FastAPI microservice platform serving 2M requests per day with PostgreSQL and Redis",
        "Reduced API latency by 45% by introducing Redis caching and query optimisation",
        "Led migration from a monolith to 8 independently deployable services with zero-downtime cutover",
        "Introduced contract tests in CI, cutting production API regressions to near zero in two quarters",
      ],
    },
    {
      role: "Backend Developer",
      company: "ShipKart",
      location: "Pune",
      start: "2019",
      end: "2022",
      current: false,
      bullets: [
        "Developed order-tracking APIs used by 400+ enterprise shippers",
        "Automated invoice reconciliation with Celery pipelines, saving the ops team 15 hours a week",
        "Mentored 3 junior developers through structured code review",
      ],
    },
  ],
  education: [
    { school: "Pune University", degree: "B.E.", field: "Computer Engineering", start: "2015", end: "2019" },
  ],
  skills: {
    groups: [
      { label: "Languages", items: ["python", "sql", "go"] },
      { label: "Frameworks & Libraries", items: ["fastapi", "django", "celery"] },
      { label: "Databases & Storage", items: ["postgresql", "redis", "mongodb"] },
      { label: "Cloud & DevOps", items: ["docker", "kubernetes", "aws", "ci/cd"] },
    ],
  },
  projects: [
    {
      name: "Open-source rate limiter",
      description: "Token-bucket rate-limiting middleware for FastAPI, published on PyPI.",
      bullets: ["1,200+ GitHub stars", "Configurable per-route limits with Redis backend"],
    },
  ],
  certifications: ["AWS Certified Developer – Associate"],
  languages: ["English", "Hindi"],
  custom_sections: [],
};

const frontendContent: DocumentContent = {
  personal: {
    full_name: "Maya Chen",
    title: "Frontend Developer",
    email: "maya.chen@example.com",
    phone: "+1 415 555 0132",
    location: "Seattle, US",
    links: ["github.com/mayachen", "mayachen.dev"],
  },
  summary:
    "Frontend developer with 4 years shipping React and TypeScript products in fintech and health. Obsessive about accessibility and performance budgets; happiest where design systems meet real user data.",
  experience: [
    {
      role: "Frontend Developer",
      company: "Northwind Health",
      location: "Seattle",
      start: "2023",
      end: "Present",
      current: true,
      bullets: [
        "Built a patient-portal redesign in React + TypeScript that lifted task completion from 61% to 84%",
        "Cut bundle size by 38% through route-level code splitting and image optimisation",
        "Shipped a WCAG 2.2 AA design system used by 4 product teams",
      ],
    },
    {
      role: "UI Developer",
      company: "Brightcart",
      location: "Remote",
      start: "2021",
      end: "2023",
      current: false,
      bullets: [
        "Developed checkout flows handling 60k daily transactions",
        "Introduced visual regression testing, catching layout bugs before release",
      ],
    },
  ],
  education: [
    { school: "University of Washington", degree: "B.S.", field: "Human-Computer Interaction", start: "2017", end: "2021" },
  ],
  skills: {
    groups: [
      { label: "Languages", items: ["typescript", "javascript", "html", "css"] },
      { label: "Frameworks & Libraries", items: ["react", "next.js", "tailwind css", "redux"] },
      { label: "Practices & Tools", items: ["accessibility", "jest", "storybook", "figma"] },
    ],
  },
  projects: [
    {
      name: "Accessible component library",
      description: "Open-source React components with full keyboard and screen-reader support.",
      bullets: ["Used by 30+ projects", "Documented with interactive examples"],
    },
  ],
  certifications: [],
  languages: ["English", "Mandarin"],
  custom_sections: [],
};

const dataContent: DocumentContent = {
  personal: {
    full_name: "Diego Alvarez",
    title: "Data Engineer",
    email: "diego.alvarez@example.com",
    phone: "+34 612 34 56 78",
    location: "Madrid, ES",
    links: ["github.com/diegoalvarez", "linkedin.com/in/diegoalvarez"],
  },
  summary:
    "Data engineer with 5 years building ELT pipelines and analytics platforms. Specialises in turning unreliable source systems into tested, documented, boring-in-a-good-way data products.",
  experience: [
    {
      role: "Data Engineer",
      company: "Metricly",
      location: "Madrid",
      start: "2022",
      end: "Present",
      current: true,
      bullets: [
        "Built Airflow + dbt pipelines processing 300M events per day into Snowflake",
        "Reduced pipeline failure rate by 70% with data-quality checks at every stage",
        "Modelled a self-serve metrics layer adopted by 5 analyst teams",
      ],
    },
    {
      role: "Analytics Engineer",
      company: "Tienda Digital",
      location: "Barcelona",
      start: "2020",
      end: "2022",
      current: false,
      bullets: [
        "Migrated 200+ legacy reports to a governed dbt project",
        "Automated marketing attribution, replacing a 2-day manual process",
      ],
    },
  ],
  education: [
    { school: "UPM Madrid", degree: "M.S.", field: "Data Science", start: "2018", end: "2020" },
  ],
  skills: {
    groups: [
      { label: "Languages", items: ["python", "sql"] },
      { label: "Data & AI", items: ["airflow", "dbt", "spark", "kafka"] },
      { label: "Databases & Storage", items: ["snowflake", "postgresql", "s3"] },
      { label: "Cloud & DevOps", items: ["aws", "terraform", "docker"] },
    ],
  },
  projects: [],
  certifications: ["dbt Analytics Engineering Certification"],
  languages: ["Spanish", "English"],
  custom_sections: [],
};

const devopsContent: DocumentContent = {
  personal: {
    full_name: "Priya Nair",
    title: "DevOps Engineer",
    email: "priya.nair@example.com",
    phone: "+91 98470 24680",
    location: "Kochi, IN",
    links: ["github.com/priyanair", "linkedin.com/in/priyanair"],
  },
  summary:
    "DevOps engineer with 5 years running Kubernetes platforms for SaaS products. Focused on the unglamorous work that keeps systems alive: observability, safe deploys, and infrastructure as code.",
  experience: [
    {
      role: "DevOps Engineer",
      company: "CloudKendra",
      location: "Remote",
      start: "2021",
      end: "Present",
      current: true,
      bullets: [
        "Operate Kubernetes clusters serving 40+ microservices across 3 regions",
        "Cut deploy time from 40 minutes to 9 with parallelised CI and image caching",
        "Built Terraform modules standardising VPC, EKS, and RDS provisioning",
        "Reduced alert noise by 55% by rebuilding SLO-based alerting in Prometheus",
      ],
    },
    {
      role: "Systems Engineer",
      company: "HostServe",
      location: "Kochi",
      start: "2019",
      end: "2021",
      current: false,
      bullets: [
        "Administered 300+ Linux servers with Ansible automation",
        "Led the on-prem to AWS migration for the billing platform",
      ],
    },
  ],
  education: [
    { school: "CUSAT", degree: "B.Tech", field: "Information Technology", start: "2015", end: "2019" },
  ],
  skills: {
    groups: [
      { label: "Cloud & DevOps", items: ["kubernetes", "terraform", "aws", "docker", "ci/cd", "prometheus", "grafana"] },
      { label: "Languages", items: ["python", "bash", "go"] },
      { label: "Practices & Tools", items: ["linux", "ansible", "incident management"] },
    ],
  },
  projects: [],
  certifications: ["Certified Kubernetes Administrator (CKA)", "AWS Solutions Architect – Associate"],
  languages: ["English", "Malayalam", "Hindi"],
  custom_sections: [],
};

const graduateContent: DocumentContent = {
  personal: {
    full_name: "Tom Becker",
    title: "Computer Science Graduate",
    email: "tom.becker@example.com",
    phone: "+49 170 123 4567",
    location: "Berlin, DE",
    links: ["github.com/tombecker", "tombecker.dev"],
  },
  summary:
    "Computer science graduate with two internships and a final-year project in distributed systems. Looking for a first backend role; strongest in Python and Java, happiest close to the data layer.",
  experience: [
    {
      role: "Software Engineering Intern",
      company: "DataWerke",
      location: "Berlin",
      start: "2024",
      end: "2025",
      current: false,
      bullets: [
        "Built an internal dashboard used weekly by the 12-person support team",
        "Wrote integration tests raising module coverage from 40% to 78%",
      ],
    },
  ],
  education: [
    { school: "TU Berlin", degree: "B.Sc.", field: "Computer Science", start: "2022", end: "2025" },
  ],
  skills: {
    groups: [
      { label: "Languages", items: ["python", "java", "sql", "javascript"] },
      { label: "Frameworks & Libraries", items: ["fastapi", "react"] },
      { label: "Practices & Tools", items: ["git", "docker", "linux", "unit testing"] },
    ],
  },
  projects: [
    {
      name: "Distributed key-value store (final-year project)",
      description: "A Raft-based key-value store in Python with leader election and log replication.",
      bullets: ["Handles 5-node clusters with automatic failover", "Grade: 1.3 (top 10% of cohort)"],
    },
    {
      name: "Study-group finder app",
      description: "React + FastAPI app matching students into study groups by course and schedule.",
      bullets: ["300 registered users in the first semester"],
    },
  ],
  certifications: [],
  languages: ["German", "English"],
  custom_sections: [],
};

export const ROLE_EXAMPLES: RoleExample[] = [
  {
    slug: "backend-developer",
    role: "Backend Developer",
    headline: "Backend developer resume example",
    intro:
      "Backend resumes are scored on depth: the systems you owned, the scale you handled, and whether your skills section matches the stack in the posting — word for word. This sample shows a senior profile structured the way both ATS parsers and engineering managers read.",
    scoredOn: ["python", "fastapi", "postgresql", "redis", "docker", "kubernetes", "microservices", "rest api"],
    tips: [
      "Name the scale in every bullet you can: requests per day, data volume, team size. Backend value is scale-shaped.",
      "Group skills the way postings do — languages, frameworks, databases, cloud — so keyword matching finds them fast.",
      "Put your strongest stack in the summary's first sentence; many screeners read nothing else before deciding.",
    ],
    templateId: "classic",
    content: backendContent,
  },
  {
    slug: "frontend-developer",
    role: "Frontend Developer",
    headline: "Frontend developer resume example",
    intro:
      "Frontend hiring weighs outcomes (conversion, performance, accessibility) as much as frameworks. This sample pairs a modern framework stack with measurable product results — the combination that survives both keyword screens and portfolio-minded reviewers.",
    scoredOn: ["react", "typescript", "javascript", "next.js", "tailwind css", "accessibility", "jest"],
    tips: [
      "Quantify user-facing wins: conversion lifts, load-time cuts, bundle reductions. 'Built pages' scores nothing.",
      "Accessibility is a keyword and a differentiator — if you've shipped WCAG work, say so explicitly.",
      "Link your portfolio and GitHub directly under your name; frontend reviewers actually click.",
    ],
    templateId: "modern",
    content: frontendContent,
  },
  {
    slug: "data-engineer",
    role: "Data Engineer",
    headline: "Data engineer resume example",
    intro:
      "Data engineering postings name pipelines, warehouses, and orchestration tools with unusual precision — and screen for exactly those words. This sample is organised around the modern data stack, with reliability numbers doing the persuading.",
    scoredOn: ["python", "sql", "airflow", "dbt", "spark", "kafka", "snowflake"],
    tips: [
      "State data volumes and pipeline counts; in data roles, scale is the seniority signal.",
      "Reliability metrics (failure-rate cuts, freshness SLAs) separate engineers from script-writers.",
      "List warehouse and orchestration tools verbatim from the posting — dbt is not 'data modelling tools'.",
    ],
    templateId: "sidebar",
    content: dataContent,
  },
  {
    slug: "devops-engineer",
    role: "DevOps Engineer",
    headline: "DevOps engineer resume example",
    intro:
      "DevOps resumes live or die on platform specifics: which cloud, which orchestrator, how infrastructure is codified, and what your deploys and alerts look like now versus before you arrived. This compact sample packs five years into two tight pages.",
    scoredOn: ["kubernetes", "terraform", "aws", "docker", "ci/cd", "prometheus", "linux"],
    tips: [
      "Certifications genuinely matter in this field — CKA and AWS certs are keyword-screened. List them exactly as named.",
      "Before/after numbers are your whole case: deploy time, alert volume, recovery time.",
      "Name the IaC tool. 'Infrastructure as code' without Terraform/Pulumi/CloudFormation scores as a phrase, not a skill.",
    ],
    templateId: "compact-tech",
    content: devopsContent,
  },
  {
    slug: "graduate-engineer",
    role: "Graduate Engineer",
    headline: "Graduate software engineer resume example",
    intro:
      "With no full-time history, a graduate resume is scored on projects, internships, and whether the skills section mirrors the posting. This sample leads with education and substantial projects — evidence first, apologies never.",
    scoredOn: ["python", "java", "sql", "git", "docker", "unit testing"],
    tips: [
      "Projects are your experience section in disguise: give each one a name, a stack, and a result.",
      "Mirror the posting's skills list honestly — new-grad screens are the most keyword-driven of all.",
      "One page. Recruiters spend seconds on graduate resumes; density beats completeness.",
    ],
    templateId: "graduate",
    content: graduateContent,
  },
];

export function getTemplateInfo(id: string): TemplateInfo | undefined {
  return TEMPLATE_INFO.find((t) => t.id === id);
}

export function getRoleExample(slug: string): RoleExample | undefined {
  return ROLE_EXAMPLES.find((r) => r.slug === slug);
}

export function sampleContentForTemplate(templateId: string): DocumentContent {
  const info = getTemplateInfo(templateId);
  const role = info ? getRoleExample(info.sampleRole) : undefined;
  return role?.content ?? backendContent;
}
