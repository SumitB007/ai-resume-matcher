"use client";

// Resume builder — document list (Phase 13).
// Start paths per the roadmap: blank, from a template, import an upload,
// or duplicate an existing document.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, FilePlus2, Loader2, PenLine, Trash2, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";
import {
  EMPTY_CONTENT,
  TEMPLATE_IDS,
  TEMPLATE_LABELS,
} from "@/lib/api/types";

export default function BuilderListPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [template, setTemplate] = useState("classic");
  const [importResumeId, setImportResumeId] = useState<string>("");

  const documents = useQuery({ queryKey: ["documents"], queryFn: api.listDocuments });
  const resumes = useQuery({ queryKey: ["resumes"], queryFn: api.listResumes });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["documents"] });

  const create = useMutation({
    mutationFn: (templateId: string) =>
      api.createDocument({
        title: "Untitled resume",
        template_id: templateId,
        content: structuredClone(EMPTY_CONTENT),
        theme: { accent: "#1d4ed8", font: "sans", density: "normal" },
      }),
    onSuccess: (doc) => router.push(`/app/builder/${doc.id}`),
    onError: () => toast.error("Could not create the document."),
  });

  const importDoc = useMutation({
    mutationFn: (resumeId: number) => api.importDocument(resumeId),
    onSuccess: (doc) => {
      toast.success("Imported as a draft — review it in the editor.");
      router.push(`/app/builder/${doc.id}`);
    },
    onError: () => toast.error("Import failed."),
  });

  const duplicate = useMutation({
    mutationFn: (id: number) => api.duplicateDocument(id),
    onSuccess: invalidate,
    onError: () => toast.error("Duplicate failed."),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteDocument(id),
    onSuccess: invalidate,
    onError: () => toast.error("Delete failed."),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Resume Builder</h1>
        <p className="text-muted-foreground">
          Build a resume with ATS-safe templates, then sync it into the matcher.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-3 pt-6">
          <div className="space-y-2">
            <p className="text-sm font-medium">Start a new resume</p>
            <div className="flex gap-2">
              <Select value={template} onValueChange={(v) => setTemplate(v ?? "classic")}>
                <SelectTrigger className="w-52">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TEMPLATE_IDS.map((id) => (
                    <SelectItem key={id} value={id}>
                      {TEMPLATE_LABELS[id]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                className="bg-blue-700 hover:bg-blue-800"
                onClick={() => create.mutate(template)}
                disabled={create.isPending}
              >
                {create.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <FilePlus2 className="mr-2 h-4 w-4" />
                )}
                New resume
              </Button>
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Or import an uploaded resume</p>
            <div className="flex gap-2">
              <Select value={importResumeId} onValueChange={(v) => setImportResumeId(v ?? "")}>
                <SelectTrigger className="w-64">
                  <SelectValue placeholder="Select an upload" />
                </SelectTrigger>
                <SelectContent>
                  {(resumes.data ?? []).map((r) => (
                    <SelectItem key={r.id} value={String(r.id)}>
                      {r.file_name ?? `Resume #${r.id}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                onClick={() => importDoc.mutate(Number(importResumeId))}
                disabled={!importResumeId || importDoc.isPending}
              >
                {importDoc.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Import
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {documents.isLoading && <Skeleton className="h-32" />}
      {documents.data?.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No built resumes yet — start one above, or import an upload to edit it.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {documents.data?.map((doc) => (
          <Card key={doc.id}>
            <CardContent className="space-y-3 pt-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{doc.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {TEMPLATE_LABELS[doc.template_id] ?? doc.template_id} · Updated{" "}
                    {new Date(doc.updated_at).toLocaleDateString()}
                  </p>
                </div>
                {doc.resume_id ? (
                  <Badge variant="secondary">Synced to matcher</Badge>
                ) : (
                  <Badge variant="outline">Not synced</Badge>
                )}
              </div>
              <div className="flex gap-2">
                <Button size="sm" className="bg-blue-700 hover:bg-blue-800" onClick={() => router.push(`/app/builder/${doc.id}`)}>
                  <PenLine className="mr-1.5 h-3.5 w-3.5" /> Edit
                </Button>
                <Button size="sm" variant="outline" onClick={() => duplicate.mutate(doc.id)} disabled={duplicate.isPending}>
                  <Copy className="mr-1.5 h-3.5 w-3.5" /> Duplicate
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-destructive"
                  onClick={() => {
                    if (confirm(`Delete "${doc.title}"? This cannot be undone.`)) {
                      remove.mutate(doc.id);
                    }
                  }}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" /> Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
