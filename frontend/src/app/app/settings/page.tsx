"use client";

// Settings (Phase 8) — profile (the name field, G7) and the privacy
// control that matters: deleting your account deletes everything.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";

export default function SettingsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: () => api.me() });
  const [name, setName] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  useEffect(() => {
    if (me.data) setName(me.data.name ?? "");
  }, [me.data]);

  const saveName = useMutation({
    mutationFn: () => api.updateMe(name.trim() || null),
    onSuccess: () => {
      toast.success("Profile saved");
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    onError: () => toast.error("Could not save your profile. Try again."),
  });

  const deleteAccount = useMutation({
    mutationFn: () => api.deleteMe(),
    onSuccess: async () => {
      await api.logout();
      toast.success("Your account and all its data are deleted.");
      router.push("/");
      router.refresh();
    },
    onError: () => toast.error("Deletion failed. Try again."),
  });

  if (me.isLoading) return <Skeleton className="h-64" />;
  if (!me.data)
    return (
      <p className="text-sm text-muted-foreground">
        Couldn&apos;t load your profile. Refresh the page to try again.
      </p>
    );

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Your profile and your data controls.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Email</Label>
            <Input value={me.data.email} disabled />
            <p className="text-xs text-muted-foreground">
              Your sign-in email. It isn&apos;t shown anywhere public.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Jane Developer"
              maxLength={120}
            />
            <p className="text-xs text-muted-foreground">
              Your display name for the app. Optional — your email works fine on its own.
            </p>
          </div>
          <Button
            onClick={() => saveName.mutate()}
            disabled={saveName.isPending}
            className="bg-blue-700 hover:bg-blue-800"
          >
            {saveName.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save profile
          </Button>
        </CardContent>
      </Card>

      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base text-red-700">
            <TriangleAlert className="h-4 w-4" /> Delete account
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Deleting your account permanently deletes <strong>everything</strong>:
            your resumes and their extracted text, saved jobs, matches and
            reports, builder documents, cover letters, and ATS results. There
            is no undo and no soft-delete limbo — resumes are personal data
            and we treat deletion as deletion.
          </p>
          {!confirmingDelete ? (
            <Button variant="outline" onClick={() => setConfirmingDelete(true)}>
              Delete my account…
            </Button>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="destructive"
                onClick={() => deleteAccount.mutate()}
                disabled={deleteAccount.isPending}
              >
                {deleteAccount.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Yes, delete everything
              </Button>
              <Button variant="ghost" onClick={() => setConfirmingDelete(false)}>
                Keep my account
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
