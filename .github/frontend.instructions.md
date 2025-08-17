---
applyTo: "frontend/**/*.tsx,frontend/**/*.ts"
---

# Frontend Stack Defaults (Numzy)

- **Framework**: Next.js App Router (TypeScript, Server Components by default)
- **UI Kit**: **MUI v7** (no Tailwind/shadcn)
- **Icons**: Material Symbols / MUI icons
- **Animation**: Framer Motion (client components only)
- **State**: keep server-first; use React state minimally; avoid global state unless needed
- **A11y**: semantic HTML + MUI’s built-in a11y; ensure keyboard support

# Code Editing Rules

- **Plan → Edit → Summarize**: brief plan, minimal diff, short rationale.
- **Boundaries**: Prefer Server Components; add `"use client"` only for interactivity.
- **Styling**: Theme + sx/`styled` (Emotion). No Tailwind utilities.
- **Components**: small, reusable; forwardRef where props suggest focus/menus.
- **Data**: fetch on server; stream if large; cache per Next.js docs.
- **Testing**: react-testing-library + Vitest/Jest style; cover a11y/keyboard.
- **Perf**: stable keys, memo only when needed; defer non-critical JS to client edges.

# Verbosity & Eagerness

- Keep text output concise. Avoid over-exploration; act once concrete edits are clear.
- Proceed under uncertainty with the safest assumption; note it after the diff.
