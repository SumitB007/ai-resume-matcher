import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = { title: "Log in" };

export default function LoginPage() {
  // AuthForm reads useSearchParams, which needs a Suspense boundary in Next 16.
  return (
    <Suspense>
      <AuthForm mode="login" />
    </Suspense>
  );
}
