// Builder editor state (Zustand) — the first true *client* state in the app:
// a nested document tree edited at keystroke frequency, plus dirty/saving
// flags for autosave. This is exactly the job §11.6 deferred Zustand for;
// server state (the saved document) still belongs to TanStack Query, and the
// store is initialised from — and saved back through — the API.

import { create } from "zustand";

import type { DocumentContent, DocTheme, ResumeDocument } from "@/lib/api/types";

interface EditorState {
  document: ResumeDocument | null;
  dirty: boolean;
  saving: boolean;
  lastSavedAt: Date | null;
  init: (document: ResumeDocument) => void;
  setTitle: (title: string) => void;
  setTemplate: (templateId: string) => void;
  setTheme: (theme: DocTheme) => void;
  /** Apply a mutator to a deep copy of the content (simple, safe at this scale). */
  updateContent: (mutate: (draft: DocumentContent) => void) => void;
  setSaving: (saving: boolean) => void;
  markSaved: () => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  document: null,
  dirty: false,
  saving: false,
  lastSavedAt: null,

  init: (document) => set({ document, dirty: false, lastSavedAt: null }),
  setTitle: (title) =>
    set((s) => (s.document ? { document: { ...s.document, title }, dirty: true } : s)),
  setTemplate: (template_id) =>
    set((s) =>
      s.document ? { document: { ...s.document, template_id }, dirty: true } : s,
    ),
  setTheme: (theme) =>
    set((s) => (s.document ? { document: { ...s.document, theme }, dirty: true } : s)),
  updateContent: (mutate) =>
    set((s) => {
      if (!s.document) return s;
      const draft = structuredClone(s.document.content) as DocumentContent;
      mutate(draft);
      return { document: { ...s.document, content: draft }, dirty: true };
    }),
  setSaving: (saving) => set({ saving }),
  markSaved: () => set({ dirty: false, saving: false, lastSavedAt: new Date() }),
}));
