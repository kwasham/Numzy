# Task: Create/modify a Next.js App Router page/route

## Constraints

- Prefer Server Components; mark client components with `"use client"`.
- Keep server actions in the same file or a sibling `actions.ts`.
- Use TypeScript when the existing file is TS.
- Respect existing design tokens; integrate with Sentry if needed.

## Steps

1) Outline route tree and file locations.
2) Implement server component (fetch on server; stream if large).
3) Add client boundary only for interactive bits.
4) Add minimal tests (render + critical behavior).

## Output

- Diff + usage example + accessibility note.
