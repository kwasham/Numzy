# Numzy Personal Plan — Development & Features

## Overview

The Personal Plan is the entry‑level paid tier for Numzy, replacing an ongoing free tier but offering a 14‑day free trial so individual users can experience the product before paying. It is designed for freelancers, consultants, and small business owners who need to capture and track expenses without corporate audit complexity. This plan focuses on core receipt extraction and light analytics while leaving advanced evaluation, prompt customization, and integrations to higher tiers.

## Features to Include

1. Receipt capture and processing

   - Upload methods: allow users to upload receipts via photo, PDF, or email. Implement intuitive drag‑and‑drop and mobile upload flows.
   - AI extraction: use the `extract_receipt_details` function to parse merchant, location, date, line items, and totals. Return structured outputs that users can review and edit.
   - Historical storage: store processed receipts in the user’s account for future reference, with search capability by date, merchant, or category.

2. Basic quality checks & alerts

   - Math discrepancy alert: flag when the sum of line items does not match the total.
   - Missing totals alert: notify the user when extracted totals appear incomplete or unusual (e.g., zero total). These checks use lightweight logic rather than the full evaluation framework.

3. Spending summary

   - Dashboard overview: provide an at‑a‑glance summary of total spending by category and merchant over selectable periods. Visualize data with simple charts or tables.
   - Filtering: allow users to filter spending reports by date range, merchant, or category.
   - Export: enable exporting receipt data to CSV or PDF for personal bookkeeping or tax preparation.

4. Account & support

   - Single user account: personal plans support only one user; there is no team management or role‑based access control.
   - Trial & subscription: grant a 14‑day free trial, after which users must subscribe to continue using the personal plan. Provide clear in‑app messaging about trial status and renewal.
   - Support channel: offer email or chat support during business hours; priority support is reserved for higher tiers.

5. Limits and exclusions
   - Usage cap: set a monthly cap on the number of receipts processed (e.g., 50–100 receipts) to control AI costs. Offer add‑on packages or upgrades for higher‑volume users.
   - Excluded features: do not include audit decision automation, advanced evaluators or prompt customization, cost modeling and ROI tools, team management, accounting software integrations, or API access. These remain premium features for business/enterprise plans.

## Development Tasks

<!-- markdownlint-disable MD033 -->

| Task                              | Description                                                                                                                                | Priority |
| :-------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------- | :------: |
| **Implement upload UI**           | Create responsive web components for uploading receipts via drag‑and‑drop and file picker;integrate mobile camera capture.                 |   High   |
| **Integrate AI<br>extraction**    | Wire up backend to call the `extract_receipt_details` model for each uploaded receipt and store results.<br>Handle error cases gracefully. |   High   |
| **Receipt history &<br>search**   | Develop a page to list processed receipts with search and filter options.<br>Support editing of extracted fields.                          |   High   |
| **Basic alerts logic**            | Add simple discrepancy checks for totals vs. line items and missing totals.<br>Display warnings to the user.                               |  Medium  |
| **Spending summary<br>dashboard** | Build charts and tables summarizing spending by category/merchant.<br>Use a lightweight charting library and ensure accessibility.         |  Medium  |
| **Export functionality**          | Implement CSV and PDF export of receipt data.<br>Ensure sensitive data is handled securely.                                                |  Medium  |
| **Trial management**              | Integrate subscription system to start a 14‑day trial on sign‑up, track remaining trial days, and enforce plan limits after expiry.        |   High   |
| **User support<br>integration**   | Add a help/contact form or chat widget for support.                                                                                        |   Low    |
| **Documentation &<br>onboarding** | Write guides for uploading receipts, understanding extracted data, and using the spending dashboard.                                       |  Medium  |

<!-- markdownlint-enable MD033 -->

## Conclusion

The Personal Plan should deliver a streamlined receipt processing and spending‑insight experience for individuals. By limiting advanced audit and evaluation features to higher tiers, Numzy can contain costs while providing a clear upgrade path for users whose needs evolve.
