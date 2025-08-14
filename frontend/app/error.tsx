"use client";
import * as Sentry from "@sentry/nextjs";
import React from "react";

export default function ErrorBoundary({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  React.useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Something went wrong in this route.</h2>
      <p style={{ color: '#555' }}>{error.message}</p>
      <button
        onClick={() => reset()}
        style={{
          background: '#2563eb',
          color: '#fff',
          padding: '0.5rem 0.75rem',
          borderRadius: 4,
          border: 'none',
          cursor: 'pointer'
        }}
      >
        Retry
      </button>
    </div>
  );
}
