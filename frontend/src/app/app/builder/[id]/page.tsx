// Server wrapper: marks this dynamic route as on-demand (Next 16 Cache
// Components — `instant` is only valid in a Server Component module) and
// renders the client editor.
import BuilderEditorClient from "./editor-client";

export const instant = false;

export default function BuilderEditorPage() {
  return <BuilderEditorClient />;
}
