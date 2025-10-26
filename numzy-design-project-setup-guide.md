# 🧭 Numzy Design Project Setup Guide

## Overview

This guide explains how to use the full Figma suite (Design, FigJam, Slides, Buzz, Site, Make) to collaboratively design, document, and ship the redesigned **Numzy** expense-management platform.

---

## 🧱 Project Structure

Create a new **Team** in Figma called `Numzy`. Inside it, create these files:

1. **Numzy UX Flow (FigJam)** — high-level user flows, wireframes, and feature maps.  
2. **Numzy Dashboard UI (Design)** — all final admin/employee screens, components, and prototypes.  
3. **Numzy Design System (Design)** — central library for colors, typography, and MUI v7 components.  
4. **Numzy Product Deck (Slides)** — presentations for stakeholders, demos, and investors.  
5. **Numzy Design Updates (Buzz)** — progress announcements and design changelogs.  
6. **Numzy Style Guide (Site)** — published design system for dev handoff and documentation.

---

## 👥 Team Roles

| Role | Figma Product | Responsibilities |
|------|----------------|------------------|
| **Product Designer** | Design / FigJam | Create wireframes → build high-fidelity screens |
| **Frontend Developer** | Design / Site | Inspect designs in Dev Mode; implement in Next.js 15 + MUI v7 |
| **Product Manager / Founder** | FigJam / Slides / Buzz | Feature flow planning, feedback, and investor presentations |
| **QA / Beta Tester** | Site | Validate final prototypes, report inconsistencies |

---

## ⚙️ Design Workflow

### 1️⃣ Ideation — *FigJam*

- Map Numzy’s key user journeys (receipt → OCR → approval → reimbursement).  
- Create low-fidelity wireframes and connect them with arrows.  
- Use color-coding for Admin (green) vs Employee (blue) flows.  
- Review collaboratively with comments and sticky notes.

### 2️⃣ Interface Design — *Figma Design*

- Create frames for all screens:  
  - `/admin/home`, `/admin/cards`, `/admin/analytics`, etc.  
  - `/employee/home`, `/employee/reimbursements`, etc.  
- Apply **Auto-layout**, **Grid**, and **Material Design 3** principles.  
- Prototype interactions (modals, drawers, hover states).  
- Switch to **Prototype mode** and test flows in Presentation view.

### 3️⃣ Systemization — *Design System File*

- Move reusable UI components into a shared **Library**.  
- Define tokens: `--primary-color`, `--font-sans`, `--radius-16`, `--spacing-8`.  
- Add component variants (Default / Hover / Disabled / Active).  
- Publish this library for use across all Figma files.

### 4️⃣ Collaboration & Feedback — *Buzz*

- Announce each design update with a summary and link.  
- Example: “✅ New Admin Analytics dashboard ready for review.”  
- Collect threaded comments and consolidate weekly changes.  
- Track changelog for your design system.

### 5️⃣ Presentation & Review — *Slides*

- Import live Figma frames directly into Slides.  
- Build pitch decks or internal sprint reviews.  
- Showcase before/after UI, feature walkthroughs, and style evolutions.  
- Export as PDF for investors or internal presentations.

### 6️⃣ Publish & Handoff — *Site*

- Publish your design system and component documentation.  
- Enable Dev Mode so developers can inspect and copy CSS/values.  
- Host your **Numzy Design System** on a live URL for your team.  
- Sync changes automatically when the design updates.

### 7️⃣ Automation & Dynamic Logic — *Make*

- Use Figma Make to simulate data (charts, receipts, spend tables).  
- Automate repetitive updates (color/theme changes, state toggles).  
- Prototype “live” dashboards for investor demos or UX testing.

---

## 🧩 Design-to-Dev Handoff Checklist

✅ Design tokens (color, typography, spacing) defined  
✅ All components named and grouped by category  
✅ Navigation routes labeled and consistent  
✅ Dev Mode enabled for all Figma Design files  
✅ Feedback documented in Buzz  
✅ Style Guide (Site) published and accessible  

---

## 📁 Recommended Folder Structure

/design
├── README.md
├── /wireframes (exported FigJam flows)
├── /ui (Figma design exports)
├── /system (tokens, palettes, MUI mappings)
├── /slides (presentations)
└── /exports (screenshots, PDFs)

---

## 🌟 Tips for Success

- Duplicate your **Numzy Dashboard UI** file before major revisions (v1.0 → v1.1).  
- Maintain consistent naming conventions (`Admin_Home`, `Employee_Reimbursements`).  
- Always publish component updates before sharing prototypes.  
- Use Figma Variables for easy Light/Dark theme toggling.  
- Link to backend API mock data (Make) for realistic demos.

---

### 🚀 Final Goal

By following this workflow, Numzy will have a fully integrated **design system**, **prototyping pipeline**, and **developer handoff ecosystem** — all powered by Figma’s collaborative suite.

---

*Created for the Numzy Redesign Project — October 2025.*
