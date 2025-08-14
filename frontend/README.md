
# Numzy Frontend

This is a [Next.js](https://nextjs.org/) App Router project (using `src/app`).

## Getting Started

Run the development server:

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the root page by modifying `src/app/page.tsx` (or `src/app/(group)/page.tsx`). The page auto-updates as you edit the file.

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

App Router API routes live under `src/app/api/*`.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js/) - your feedback and contributions are welcome!

## Instrumentation / Observability

Sentry is initialized once via `src/app/instrumentation.ts`. Provide environment variables:

```bash
NEXT_PUBLIC_SENTRY_DSN=...
SENTRY_TRACES_SAMPLE_RATE=0.2
SENTRY_PROFILES_SAMPLE_RATE=0.1
SENTRY_RELEASE=frontend@1.0.0
```

If `NEXT_PUBLIC_SENTRY_DSN` is absent, instrumentation safely no-ops.

## Deploy

Follow standard Next.js deployment docs (Vercel or custom). Ensure build-time env vars above are set for release tagging & source maps (add an upload step later).
