import type { ReactNode } from "react";
import { ApiError } from "../api/client";

export function Loading({ what }: { what: string }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <span className="state__ball" aria-hidden="true" />
      <p>Loading {what}</p>
    </div>
  );
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  const title = error instanceof ApiError ? error.title : "Something went wrong";
  const detail = error instanceof ApiError ? error.message : "Reload the page, and if it keeps happening, check that the backend is running.";
  return (
    <div className="state state--error" role="alert">
      <h2 className="state__title">{title}</h2>
      <p>{detail}</p>
      {retry && <button type="button" className="btn" onClick={retry}>Try again</button>}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="state state--empty">{children}</div>;
}
