// Server wrapper: per-user, per-letter print view — always on demand.
// The client part (useParams) sits inside Suspense per Next 16 prerender rules.
import { Suspense } from "react";

import PrintCoverLetterClient from "./print-client";

export const instant = false;

export default function PrintCoverLetterPage() {
  return (
    <Suspense fallback={null}>
      <PrintCoverLetterClient />
    </Suspense>
  );
}
