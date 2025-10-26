
# Prompt: Redesign Receipt Table and Detail Modal (Numzy Project)

You're working on the **Numzy** Next.js app (App Router) which uses **MUI v7** and the **Devias Pro** UI kit. We need to **refactor the receipts UI** (table and detail modal) to closely match **Ramp’s** design patterns, improving both functionality and aesthetics.

---

## 🎯 Objective

Upgrade the `Receipts` dashboard to provide:
- A **modernized, responsive UI**
- Enhanced functionality
- Alignment with **Ramp-style** UX patterns (as seen in their Help Center documentation)

---

## 📁 Relevant Files

- `app/dashboard/receipts/page.tsx`  
  → Page-level container with `ReceiptsContent` and `ReceiptModalGate`
- `components/dashboard/receipts/receipts-table.tsx`  
  → Displays the list of receipts in a paginated table
- `components/dashboard/receipts/receipt-modal.tsx`  
  → Displays receipt details (opened via URL slug or action)
- Related components:  
  - `receipts-filters.tsx` – for status tabs, search, and filters  
  - `receipts-selection-context.tsx` – for row selection state  
  - `core/data-table.tsx` – shared DataTable logic  
  - `core/property-list.tsx`, `property-item.tsx` – key/value rendering

---

## 🧩 Receipt Table – Redesign Plan

### Layout

- Replace flat row layout with **stacked content blocks**:
  - Top: Merchant Name + Amount (bold, stacked)
  - Bottom: Date, Category, Payment Method
- Convert the `status` column to **MUI `<Chip>`**:
  - Use color and icons (e.g., Pending → yellow, Completed → green)
- Enable column-level sorting with `TableSortLabel`
- Support **global search** (by merchant, amount, category)

### Mobile Support

- On small screens, switch to a **stacked card layout**
- Collapse columns into expandable details
- Touch-friendly row actions (icon-only if needed)

### Bulk Selection + Action Bar

- Allow checkbox selection of rows
- When >1 row is selected, show **bulk actions bar**:
  - Download
  - Reprocess
  - Clear Selection

---

## 🧾 Receipt Detail Modal – Redesign Plan

### Layout

- On **desktop**:
  - **Left pane**: PDF/image preview with:
    - Zoom, rotate, download buttons
  - **Right pane**: key-value display of:
    - Merchant, Amount, Date, Status
    - Category, Matching card, Notes
    - Line item breakdown (table)
- On **mobile**:
  - Single-column scrollable layout
  - Toolbar floats or collapses for PDF controls

### Extras

- Use `Alert`, `Chip`, or icons for:
  - Flags (e.g., missing memo, duplicate match)
  - Errors (OCR failure, vendor mismatch)
- Add expandable tabs for:
  - Audit logs (if available)
  - Raw JSON payload (if debug mode enabled)

---

## 🧱 Dev Guidelines

- Use **Devias + MUI v7** patterns
- Respect global theme spacing + typography
- Follow modular design:
  - Extract new components if logic exceeds ~80 LOC
- Use existing icons or `@phosphor-icons/react`
- Label every section clearly in code with comments

---

## ✅ Deliverables

- `receipts-table.tsx` redesigned with:
  - Stacked content cells
  - Responsive layout
  - Status chips
  - Bulk selection
- `receipt-modal.tsx` redesigned with:
  - Two-column responsive layout
  - Image preview + controls
  - Organized extracted data
  - Flags and audit indicators

---

## 💬 Notes for GPT-5 Codex

You're working in a solo developer environment using VS Code and Copilot Chat with `gpt-5-codex`. Be specific in prompt messages and use inline comments to scaffold complex components progressively.
