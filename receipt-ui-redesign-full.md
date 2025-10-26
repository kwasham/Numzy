

# Redesign: Receipt Table and Detail Modal

(Numzy Project)

You're working on the Numzy Next.js app (App Router) which uses MUI v7 and the Devias Pro UI kit. We need to refactor the receipts UI (table and detail modal) to closely match Ramp’s design patterns, improving both functionality and aesthetics. Below are the relevant files and a breakdown of required changes for the Receipt Table and Receipt Detail Modal components. Please update the code accordingly, following MUI/Devias conventions and adding comments for clarity.

## Relevant files

- `app/dashboard/receipts/page.tsx` – Next.js page that sets up the Receipts dashboard. It renders the main content (`<ReceiptsContent />`) and a modal gate (`<ReceiptModalGate />`) for the detail modal.
- `components/dashboard/receipts/receipts-table.tsx` – The receipt table component that displays a paginated list of receipts. Currently uses a custom DataTable with columns for date, merchant, amount, status, category, etc.
- `components/dashboard/receipts/receipt-modal.tsx` (also referred to as `ReceiptDetailModal`) – The receipt detail modal component that shows an individual receipt’s details and preview. It’s rendered via `ReceiptModalGate` when a receipt is selected.

Other related components (for context, may need minor adjustments):

- `components/dashboard/receipts/receipts-filters.tsx` – UI for filtering receipts (status tabs, search filters, sort dropdown).
- `components/dashboard/receipts/receipts-selection-context.tsx` – Provides state for selected rows in the table.
- `components/core/data-table.tsx` – The generic table component used by `ReceiptsTable` (if custom behavior is needed for sorting or responsiveness).
- `components/core/property-list.tsx` and `property-item.tsx` – Used in the modal to display key/value pairs of receipt details.

## Receipt table redesign

Refactor the `ReceiptsTable` component (`receipts-table.tsx`) to enhance its layout and interactivity, aligning with Ramp’s UI patterns:

## Stacked Merchant & Amount cell

- Combine the merchant name and total amount into a single stacked cell for a cleaner look. The merchant (vendor) name should be on one line (possibly using a bold or subtitle text style), and the amount on the line below in a smaller, secondary text style.

- For example, each row’s first column can show:

  - Merchant name (as a clickable link to open the receipt preview) — use a typography variant like `subtitle2` or similar.
  - Total amount — formatted as currency, using a `Typography` with `color="text.secondary"` (gray) and perhaps a smaller font (e.g., `body2` or `caption`).
  - If the receipt is still processing or pending, you can also show a loading indicator under the amount (e.g., a `LinearProgress` bar), as is done currently.

## Status indicators with MUI Chips

- For the Status column, use MUI `<Chip>` components with icons and colors to indicate each status (Pending, Processing, Completed, Failed, etc.), similar to Ramp’s pill-style statuses.
- You can leverage the existing mapping of status to icon/color (e.g., a Clock icon for pending/processing in amber, a CheckCircle for completed in green, X or warning icon for errors in red).
- Ensure the Chip’s style (e.g., `variant="outlined"` or filled/soft) matches the design system:

  - Pending/Processing: Use a warning-colored chip with a clock/timer icon.
  - Completed: Use a success-colored chip with a check icon.
  - Failed/Rejected: Use an error-colored chip with an X or alert icon.

- Use concise labels: e.g., “Pending”, “Completed”, “Failed”, etc., with appropriate casing.
- These chips make status easily scannable, akin to Ramp’s UI.

## Responsive mobile layout (stacked card rows)

- Introduce a responsive design so that on small screens (mobile widths), the table displays as a set of stacked cards (one card per receipt) instead of a horizontal scrollable table. This improves readability on mobile:

  - For mobile (`xs` breakpoint), each “row” should stack its cells vertically. You might achieve this by using CSS or MUI’s `Stack`/`Grid` components conditionally. For example, you could hide the table headers and present each row as a `<Card>` or `<Box>` with the data fields laid out in a column.
  - Each card (mobile row) can show the key info in order: Merchant & Amount (at top), then perhaps status chip, date, payment method, etc., each on its own line or grouped logically. Use typography variants and spacing to differentiate labels vs values if needed.
  - On larger screens, the component should fall back to the standard table layout with columns. Leverage MUI’s breakpoints or the Devias kit’s responsive utilities (e.g., `sx={{ display: { xs: 'block', md: 'table-row' } }}` or similar approaches) to conditionally style the rows.

- Ensure no critical information is hidden on mobile. If necessary, some less important columns (like an “Open” action icon or certain metadata) can be hidden on narrow screens to reduce clutter.

## Row selection & bulk action bar

- Improve the row selection UX to include a bulk action toolbar, similar to Ramp’s multi-select actions:

  - The table already supports selecting rows (with checkboxes or row clicks) via the `ReceiptsSelectionProvider`. Extend this so that when one or more receipts are selected, a bulk actions bar appears. This can be a toolbar either above the table or fixed at the bottom/top of the page (choose a UX that aligns with the rest of the app or Devias patterns).
  - In this bulk action area, display the number of selected receipts (e.g., “3 selected”) and provide actions:
    - Download — a button to download the selected receipts. This could trigger a bulk download (e.g., fetch a ZIP of all selected receipt files) or multiple downloads. If a bulk download endpoint exists, use that; otherwise, loop through selected receipts and use their download links. This action should be disabled or hidden if no receipts are selected.
    - Reprocess — a button to re-run processing on selected receipts (particularly useful for receipts in error/failed state). This would call the appropriate API (e.g., `POST /receipts/:id/reprocess`) for each selected receipt. Provide user feedback (toast or alert) after initiating.
    - (Optional) Delete — if deletion of receipts is supported and aligns with Ramp’s UX. Given the current UI already has a Delete button in filters when selection is active, you can keep that or integrate it here.

  - Clear/Deselect all — a simple button to clear the selection (as exists now, possibly labeled “Clear Selection”).

- Style this bulk action bar distinctly (e.g., a `Paper` or `Box` with a slight elevation or different background) to make it obvious and keep it fixed if needed so it’s easily accessible. This is similar to how some admin UIs or Ramp highlight multi-select actions.

## Filtering and sorting improvements

- Enhance the table controls for better filtering and sorting:
  - Per-column sorting: Allow users to sort the receipts by key columns such as Date, Merchant, or Amount. Implement clickable column headers or sorting icons in the UI:
    - If using a custom `DataTable` component, add support for a `sortable` property on columns and handle an `onSort` event. For example, clicking the “Date” header could toggle sort direction (asc/desc) for date.
    - The current implementation uses a `sortDir` query param (Newest/Oldest via the dropdown). You can tie into that or replace it with clickable headers. Use MUI’s table sort icons (e.g., `<TableSortLabel>`) if available in the Devias kit.
    - Ensure that when a sort is applied, the data is refetched or resorted accordingly (likely via server or existing hooks). Keep the UI state (highlight the sorted column, show arrow direction).
  - Global search: Add a global search field to filter receipts across multiple fields (not just exact matches). This could be a text input in the filters section (perhaps in the `ReceiptsFilters` bar) that filters by merchant name, receipt ID, or other metadata in one go:
    - For example, a search input with placeholder “Search receipts…” that when typed, updates the list to show only receipts whose merchant name or ID (or other fields) match the query.
    - Implement this by either querying the backend with a `search` parameter or filtering client-side if the data set is small enough. You might reuse the existing filter logic (currently there are separate Merchant and ID filters; you can simplify by having the search box set both fields or a general query).
    - Make sure this search is debounced or applied on Enter to avoid excessive reloads.
  - Enhanced filters UI: Keep the existing filter functionality (status tabs, merchant filter, ID filter, date range if any) provided by `ReceiptsFilters`. You can integrate the new global search here or adjust layout so it fits nicely. Ensure that the status tabs (All, Completed, Pending, etc., with counts) remain at the top of the filter bar for quick status-based filtering (this is already similar to Ramp’s filtering by receipt status).

- Retain the sort dropdown (Newest/Oldest) for date sorting if column header sort is not implemented or for convenience on mobile. This can complement the interactive column sorting on desktop.

- Implementation note: While making these changes, preserve the use of MUI components and theming. For example, use MUI’s `Grid`/`Stack` for layout, Buttons and Icons from MUI (or Phosphor icons as currently used) for actions, and the Devias-provided components (like `DataTable`, `Option`, etc.) where appropriate. Make sure to keep the code type-safe (TypeScript) and add comments describing each major change for clarity.

## Receipt detail modal redesign

Refactor `receipt-modal.tsx` (a.k.a. `ReceiptDetailModal`) to improve its layout and make it closer to Ramp’s receipt view. The goal is a cleaner, two-column design on desktop, with all relevant info clearly presented, and a responsive single-column layout on mobile. Key changes:

## Wide two-column layout (desktop)

- Change the modal from a small centered dialog to a wider dialog or panel, so we can display content in two columns side-by-side on larger screens:

  - Increase the `Dialog` width — for example, use `maxWidth="lg"` or `sx` overrides to make it perhaps ~800–900px wide (instead of the current `maxWidth="sm"`). This gives room for two columns. You may also allow the dialog to take a larger portion of the screen (or even full width on very large screens) as Ramp often uses a side panel or full-page modal for receipt details.
  - Use a responsive layout inside `DialogContent`: on desktop (`md`/up), use a container (like a `<Stack direction="row" spacing={2}>` or `<Grid container>`) to split content into a left and right section. On mobile (`xs`), stack these sections vertically (`direction="column"` or use CSS breakpoints on the Stack/Grid).
  - Ensure scroll behavior is handled nicely: possibly make the dialog content scrollable if it exceeds height, but also consider fixed elements if needed (for example, maybe the image preview could scroll independently from the details — but to keep it simple, a single scroll for the whole modal is fine).

## Left side — receipt preview panel

- Dedicate the left column to showing the receipt image or PDF preview:

  - If a receipt image is available (most receipts), display it in a container that uses most of the left column’s space. Maintain aspect ratio and allow it to scale (`object-fit: contain`) so the entire receipt is visible. For PDFs or if an image fails, you can use an `<iframe>` or a fallback message (“Preview not available”) as currently done.
  - Controls for Zoom/Rotate/Download: At the top of the preview area (or overlayed on the image in a corner), add a small toolbar of `IconButton`s:
    - Zoom in/out: Increase or decrease the zoom level of the image/PDF. Implementation-wise, you could wrap the image in a div and apply CSS transforms (`scale`) or simply open the file in a new tab for full-size viewing if true zoom is complex. Even a basic approach: clicking “Zoom In” could open the image in a new browser tab or trigger the browser’s download if needed. For a nicer UX, manage a state for zoom scale and apply to the image style.
    - Rotate: Rotate the image 90° per click (if images might be sideways). This can be done by applying a CSS `rotate` transform on the image element. Keep track of rotation state in component state.
    - Download: Provide a direct download button (perhaps a Download icon as the button). This should use the `downloadHref` (already fetched in state via the effect) to download the receipt file. You can simply set `href={downloadHref}` on an anchor or programmatically trigger a download.
    - Use appropriate MUI icons for these actions (e.g., Zoom In/Out could use `ZoomIn`/`ZoomOut` icons, Rotate could use `Rotate90DegreesCcw` or similar icon, Download uses a `Download` icon). Include tooltips on these buttons (using `<Tooltip>` from MUI) for clarity.
    - Make sure these controls are accessible and don’t overlap important parts of the image (you can place them above the image or in a small header above the preview).
  - The preview area should have a light border or background (to distinguish it from the page background) — you can use a MUI `Card` or `Paper` around the image for a framed look. Ensure the preview area is scrollable if the image is large or zoomed.

## Right side — receipt details panel

- Use the right column to display all the extracted data and metadata for the receipt in organized sections:
  - Basic info section: At the top of the right side, show key info like:
    - Merchant name (possibly with an icon or avatar if available, and maybe clickable if it links to a merchant record — optional).
    - Amount/Total — formatted currency total of the receipt.
    - Date of the transaction or receipt.
    - Status — show the status chip here as well (e.g., a “Completed” chip or “Pending” chip), consistent with the table.
    - These could be laid out as a small grid or list. For example, use a two-column grid of `PropertyItem`s or simply a vertical list with bold labels and values. Given Devias’s `PropertyList`/`PropertyItem` components are already used, you can continue to use them but perhaps break them into subsections.
  - Categorization and payment: Next, include fields like:
    - Category/Sub-category — the expense category of the receipt (if available). If the category is editable (as it appears in the table via a dropdown), you might allow editing here too or simply display it. For now, displaying the category is fine.
    - Payment method — e.g., show the payment method used (Visa, Mastercard, last4 of card, etc.). This could include the card brand logo as in the table’s Payment Method column, or simply text like “Visa •••• 1234”.
    - Filename or Receipt ID — if useful, show the original filename or an ID for reference (this is currently displayed).
  - Audit flags / errors: If there are any audit findings or errors:
    - For example, if the receipt’s totals don’t match (math error) or it’s over a policy limit, highlight these. Use MUI `Alert` components or badges to draw attention:
      - If `auditMathError` (math inconsistency) is true, show an `<Alert severity="warning">Math discrepancy in totals</Alert>` or a small warning indicator next to the total.
      - If `amountOverLimit` (exceeds some limit) is true, perhaps show an `<Alert severity="info">Amount over allowed limit</Alert>` or a chip labeled “Over Limit” (as currently done). You could consolidate multiple flags in one Alert with a list or show separate small alerts for each.
      - If the receipt status is “failed” (processing failed), consider an error `Alert` at the top of the details panel explaining that extraction failed, and perhaps prompt the user to reprocess (with a button).
    - The goal is to make any issues very visible, similar to how Ramp might show an alert if something needs attention on an expense.
  - Line items (if applicable): If the receipt has individual line items (like an itemized bill), ensure the Line Items table is still displayed. In the current implementation, line items are shown below the details (with a subtotal, taxes, total calculation). You should retain this, but in a two-column layout, you need to decide how to place it:
    - You could span the full width of the modal with the line items section below both columns (i.e., after a divider, show the line items table). This might be simplest: the top of modal has two columns (preview & summary details), then below, one column layout for line items and totals.
    - Alternatively, if the modal is very wide, you might keep line items in the right column if they fit. But likely they won’t fit nicely in half width, so showing them below in full width might be better.
    - Style the line items table similarly to before (maybe as a small table or list with a subtle border). Ensure the totals (subtotal, taxes, total, etc.) are clearly aligned to the right as they are now. If any value has an issue (e.g., total mismatch), highlight it (the code currently adds a “Mismatch” chip if `mathMismatch`).
  - Tabs or accordions for additional data (optional): If there is extra data not always needed in the main view (such as raw JSON of the receipt extraction or an audit log of changes):
    - Consider adding Tabs at the top of the right section (or modal) for switching between “Details” and “Raw Data” or “Audit Log”. For example, a second tab could show a JSON pretty-print of the receipt’s raw data (for developers or advanced users), and another tab could list an audit log of any actions/edits on the receipt.
    - If using tabs, use MUI’s `<Tabs>` and `<Tab>` components. Ensure the default tab is “Details” for regular users, and the others are optional.
    - Alternatively, use an `Accordion` component to hide/show the raw JSON or logs at the bottom of the modal. For instance, an Accordion titled "Audit Log" that can expand to show events, and one for "Raw JSON Data" to show a code block of JSON.
    - Mark these sections as optional/enhanced features — the primary focus is the improved UI, but adding these will move the design closer to Ramp (which often provides detailed logs or raw views for auditing).
  - Preserve edit and reprocess actions: The modal currently has an “Edit” button (to edit receipt details) and a “Reprocess” button (shown for failed receipts). Keep these actions accessible:
    - The Edit button (which likely navigates to a different page or form for editing the receipt) should remain, possibly styled as a secondary action in the top-right of the details section.
    - The Reprocess button for failed receipts should be prominent if the receipt is in an error state. You might convert this to a more visible action in the details panel (e.g., an `Alert` with a “Reprocess” action, or a button with an icon).
    - If possible, include a Download Receipt action for the single receipt in the modal as well (especially if not covered by the preview’s download control). This could simply be another button near “Edit” like “Download PDF”.
  - Mobile view (single column): On smaller screens, ensure the modal content becomes a single column stacked view:
    - The preview should come first (taking full width), and the details come after (full width). You may collapse spacing or use accordions to make it manageable on a phone screen.
    - The controls (zoom/download) should still be accessible (maybe as a bottom bar over the image or a fixed small header that scrolls).
    - Test that the content can scroll vertically without breaking layout. Using a flex column inside `DialogContent` with `overflowY: auto` could help.

  - Throughout this modal redesign, follow MUI and Devias styling conventions — use the theme’s spacing, typography variants, and components rather than custom CSS when possible. For example, use `<Typography variant="h6">` or `variant="subtitle1"` for section headings, use MUI `<Divider>` to separate sections (e.g., between the details and the line items), and maintain the same theming (colors, border radius, etc.) as the rest of the app. Add comments in the code to explain layout sections (e.g., `// Left column: image preview`, `// Right column: details`, etc.) to aid future maintainers.

## Devias/MUI conventions and project structure

As you implement the above changes, keep these guidelines in mind to ensure consistency and maintainability:

- Use existing components and patterns: The project likely has custom components (e.g., `DataTable`, `PropertyList`, `FilterButton`) that wrap MUI elements. Use these where appropriate rather than reinventing. For instance, continue using `PropertyList`/`PropertyItem` for listing out fields, just arrange them in the new layout. Use the `ReceiptsSelectionContext` for selection state (which you already do).
- Theming: Respect the MUI theme provided by Devias Pro kit. That means using the palette (e.g., use `color="warning"` rather than hard-coding an amber color, use theme spacing values, etc.), and using the variant styles (Devias’s design might have custom variants or styles for Buttons, Chips, etc.).
- Icons: The project uses Phosphor icons (e.g., `PlusIcon`, `CheckCircleIcon` from Phosphor) and MUI icons. You can continue with those for consistency. Ensure any new icons (Zoom, Rotate, Download) are imported either from Phosphor or MUI’s Material Icons (whichever is consistent in this codebase).
- File structure: Place any new helper components or extensive logic in appropriate files if needed. For example, if the responsive card view for mobile is complex, you could create a sub-component (e.g., `ReceiptCardItem`) in the same file or a new file, but since this is a relatively contained change, it might be handled with conditional JSX within `ReceiptsTable`.
- Performance considerations: The receipts list can be large, so try not to introduce heavy computations on each render. Leverage existing data (the `rows` prop and hooks). For example, for global search, if the backend doesn’t support a query, consider adding one, or be mindful when filtering on the client side (perhaps limit to filtering already loaded page).
- Progressive enhancement: It may be wise to implement these changes step-by-step. The code output should ideally show each section updated, so a developer can integrate and test gradually (e.g., first updating the table layout and verifying, then the modal layout).
- Comments: Include clear comments in the code for any non-trivial logic or layout decisions. For instance, comment on why we use a `Stack` with certain breakpoints for responsive design, or notes on the usage of certain MUI components for clarity.

## Expected output format

When writing the updated code, structure it for readability since a solo developer will be copying it into the project and testing it:

- Provide the code for each modified file (or code block) separately, prefaced by a brief comment or heading indicating the file name (for example, `// File: receipts-table.tsx`).
- Within each file’s code, highlight the changes with comments if possible (e.g., `// Added bulk action bar`, `// New responsive layout for mobile`) at the relevant sections.
- Ensure the code compiles and works together. The prompt should result in a cohesive refactor, so double-check imports (for new icons or MUI components), and that any new state or handlers are defined.
- It's fine to omit unrelated parts of the file for brevity, but include enough context so the developer knows where changes go (especially around the areas being refactored).
- After providing code, if helpful, briefly summarize how the new implementation achieves the redesign (this can reinforce the approach for the developer).

## End goal

The GPT-5 Codex should produce a refactored `receipts-table.tsx` and `receipt-modal.tsx` (and minor tweaks to other components if needed) that implement the above changes. The new UI should closely resemble Ramp’s receipts interface — with a modern, clean table that collapses into cards on mobile, and a detailed modal with side-by-side preview and info, status chips, and clear indicators for any issues.
