# Redesign Receipt Table and Detail Modal (Numzy Project)

You're working on the Numzy Next.js app (App Router) which uses MUI v7 and the Devias Pro UI kit. We need to refactor the receipts UI (table and detail modal) to closely match Ramp’s design patterns, improving both functionality and aesthetics. Below are the relevant files and a breakdown of required changes for the Receipt Table and Receipt Detail Modal components. Please update the code accordingly, following MUI/Devias conventions and adding comments for clarity.

## Relevant files

- `app/dashboard/receipts/page.tsx` – Next.js page that sets up the Receipts dashboard. It renders the main content (<ReceiptsContent />) and a modal gate (<ReceiptModalGate /> for the detail modal).
- `components/dashboard/receipts/receipts-table.tsx` – The receipt table component that displays a paginated list of receipts (uses the custom `DataTable`).
- `components/dashboard/receipts/receipt-modal.tsx` (aka ReceiptDetailModal) – The receipt detail modal showing an individual receipt’s details and preview; rendered via `ReceiptModalGate`.
- Other related components (context; may need minor tweaks):
  - `components/dashboard/receipts/receipts-filters.tsx` – Status tabs, filters, sort dropdown.
  - `components/dashboard/receipts/receipts-selection-context.tsx` – Selected rows state.
  - `components/core/data-table.tsx` – Generic table used by `ReceiptsTable` (for sorting/responsiveness hooks).
  - `components/core/property-list.tsx`, `components/core/property-item.tsx` – Key/value display inside the modal.

## Receipt table redesign

Refactor `ReceiptsTable` to align with Ramp’s patterns and improve clarity.

### Stacked merchant & amount cell

- Combine merchant name and total into a single stacked cell.
- Merchant (vendor) name: use a clickable link to open the receipt preview, e.g., `variant="subtitle2"`.
- Amount: format as currency using `Typography` with `color="text.secondary"` and a smaller variant (`body2` or `caption`).
- If status is pending/processing, show a loading indicator below (e.g., `LinearProgress`).

### Status indicators with MUI chips

- Use MUI `<Chip>` for status: `Pending`, `Processing`, `Completed`, `Failed/Rejected`.
- Mapping examples: clock/timer icon with warning color for pending/processing; check icon with success color for completed; `X`/alert icon with error color for failures.
- Prefer concise labels and consistent casing; use `variant="outlined"` or soft/fill per theme.

### Responsive mobile layout (stacked card rows)

- On `xs` screens, render each row as a stacked card rather than a wide, scrollable table.
- Hide table headers on mobile and present rows as `Card`/`Box` with vertical layout.
- Show key info in this order: Merchant & Amount (top), Status, Date, Payment Method, etc.
- On larger screens, fall back to standard table layout. Use breakpoints like `sx={{ display: { xs: 'block', md: 'table-row' } }}`.
- Hide less critical columns (e.g., an “Open” icon) on narrow screens.

### Row selection and bulk action bar

- When one or more receipts are selected (via `ReceiptsSelectionProvider`), show a bulk actions toolbar.
- Display count (e.g., “3 selected”) and actions:
  - Download: bulk download ZIP if supported; otherwise trigger individual downloads.
  - Reprocess: `POST /receipts/:id/reprocess` for each selected; provide a toast/alert.
  - Optional Delete: only if aligned with product policy (existing selection delete can remain).
- Include a “Clear/Deselect All” control; style the bar distinctly (e.g., `Paper` with slight elevation). Consider fixed positioning.

### Filtering and sorting improvements

#### Per‑column sorting

- Allow sorting by Date, Merchant, Amount. Clickable headers or sort icons.
- If using the custom `DataTable`, add `sortable` on columns and an `onSort` handler.
- The existing `sortDir` (Newest/Oldest) can remain for mobile or be synchronized with header clicks.
- Use MUI’s `<TableSortLabel>` if available; highlight the sorted column and arrow direction.

#### Global search

- Add a search input in `ReceiptsFilters` to filter by merchant, ID, and other metadata.
- Debounce or apply on Enter to avoid excessive reloads.
- Implement via backend `search` param if available, else client-side filter over the current page.

#### Enhanced filters UI

- Keep status tabs (All/Completed/Pending/Processing/Failed) with counts at the top.
- Retain sort dropdown (Newest/Oldest) for convenience on narrow screens.

> Implementation note: Preserve MUI components/theming. Use `Stack`/`Grid` for layout, Devias components like `DataTable`, `Option`, etc. Keep code type‑safe and comment non‑obvious logic.

## Receipt detail modal redesign

Refactor `receipt-modal.tsx` (ReceiptDetailModal) for a clean two‑column desktop layout and a responsive single‑column mobile layout.

### Wide two‑column layout (desktop)

- Increase dialog width (e.g., `maxWidth="lg"` or wider via `sx`).
- Inside `DialogContent`, use `Stack direction="row"` or `Grid` to split left/right panels on `md+`; stack on `xs`.
- A single scrollable content area is fine; avoid complex nested scrolling.

### Left: receipt preview panel

- Show image/PDF preview; maintain aspect ratio with `object-fit: contain`.
- Fallback to `<iframe>` or a message if preview fails.
- Add a small toolbar with icon buttons:
  - Zoom In/Out (CSS transform scale or open in new tab).
  - Rotate 90° (CSS transform rotate; track rotation in state).
  - Download (anchor with `href={downloadHref}` or programmatic download).
- Use appropriate icons (Phosphor or MUI) and `<Tooltip>` labels; avoid covering important image areas.
- Wrap preview in a `Card`/`Paper` with a light border/background. Allow the preview area to scroll if zoomed.

### Right: receipt details panel

- Basic info at top:
  - Merchant name (optionally avatar/icon).
  - Total amount (currency‑formatted).
  - Date.
  - Status chip (consistent with table).
- Categorization and payment:
  - Category/Sub‑category (display or optional edit control).
  - Payment method (e.g., “Visa •••• 1234” or brand logo + last4).
  - Filename/Receipt ID.
- Audit flags / errors:
  - If `auditMathError`, show `Alert` warning for math discrepancy.
  - If `amountOverLimit`, show info `Alert` or “Over Limit” chip.
  - If status is `failed`, show an error `Alert` with a “Reprocess” action.

### Line items

- Keep the line items table. Prefer full‑width section below the top two columns on desktop.
- Totals (subtotal, discount, shipping, receiving, taxes, total) right‑aligned; show a “Mismatch” chip if math discrepancy.

### Optional: tabs or accordions

- Add Tabs (e.g., “Details”, “Raw Data”, “Audit Log”) or accordions for advanced info.
- Default to “Details” for normal users; others are optional/enhanced views.

### Mobile view (single column)

- Stack preview first, then details; keep controls accessible (fixed small header or bottom bar if needed).
- Ensure vertical scrolling works smoothly.

> Styling note: Use `Typography` (`variant="h6"`, `subtitle1`), `Divider`, theme spacing, colors, and radii. Add comments like `// Left column: image preview` and `// Right column: details` for maintainability.

## Devias/MUI conventions and project structure

- Reuse existing components/patterns (`DataTable`, `PropertyList`, `FilterButton`, selection context).
- Respect theme palette and variants (`color="warning"` instead of hard‑coded colors, theme spacing, etc.).
- Icons: continue using Phosphor/MUI icons consistently (Zoom/Rotate/Download as needed).
- Structure: create helper subcomponents only if complexity warrants; otherwise keep conditional JSX local.
- Performance: avoid heavy per‑render computations; leverage existing data/hooks; be mindful with client‑side searching.
- Progressive enhancement: ship changes in steps; test table first, then modal.
- Comments: document non‑trivial logic and responsive layout decisions.

## Expected output format

- Provide code per modified file, each with a brief heading comment (e.g., `// File: receipts-table.tsx`).
- In‑file comments highlighting key additions (e.g., “Added bulk action bar”, “New responsive mobile layout”).
- Ensure the updated files compile together; verify imports and any new state/handlers.
- It’s fine to omit unrelated parts for brevity, but include enough surrounding context.
- Optionally add a short summary of how the implementation meets the redesign.

## End goal

Produce refactored `receipts-table.tsx` and `receipt-modal.tsx` (with small supporting tweaks) that deliver a Ramp‑style experience: a clean, modern table that collapses into cards on mobile, plus a detailed modal with side‑by‑side preview and info, clear status chips, and visible audit indicators.
