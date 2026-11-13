"use client";

// Renders the backend's AI feedback markdown. The LLM output follows a fixed
// section structure (### 1. Strengths … ### 4. Summary), so a small styled
// react-markdown renderer is enough — no typography plugin needed.

import ReactMarkdown from "react-markdown";

export function FeedbackView({ text }: { text: string }) {
  return (
    <div className="text-sm leading-relaxed">
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h3 className="mt-4 mb-2 text-base font-semibold first:mt-0">{children}</h3>
          ),
          h2: ({ children }) => (
            <h3 className="mt-4 mb-2 text-base font-semibold first:mt-0">{children}</h3>
          ),
          h3: ({ children }) => (
            <h3 className="mt-4 mb-2 text-base font-semibold first:mt-0">{children}</h3>
          ),
          p: ({ children }) => <p className="mb-2">{children}</p>,
          ul: ({ children }) => (
            <ul className="mb-2 list-disc space-y-1 pl-5">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-2 list-decimal space-y-1 pl-5">{children}</ol>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold">{children}</strong>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
