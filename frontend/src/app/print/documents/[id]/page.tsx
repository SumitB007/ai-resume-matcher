// Server wrapper: per-user, per-document print view — always on demand.
// The client part (useParams) sits inside Suspense per Next 16 prerender rules.
import { Suspense } from "react";

import PrintDocumentClient from "./print-client";

export const instant = false;

export default function PrintDocumentPage() {
  return (
    <Suspense fallback={null}>
      <PrintDocumentClient />
    </Suspense>
  );
}
