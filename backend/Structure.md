# Production‑Grade Receipt‑Inspection API: System Design & Technical Evaluation

## Introduction

The goal of this project is to evolve the experimental notebook from the OpenAI **receipt\_inspection** example into a robust SaaS platform. Users should be able to upload receipts, extract structured data, apply custom audit rules, evaluate models and calculate cost trade‑offs. The backend must be modular and scalable, while the frontend should offer a pleasant dashboard for both individual users and teams.

During this evaluation we examined your `receipt-processing-api` repository, which already integrates the **OpenAI Agents SDK** for extraction and auditing as well as **OpenAI Evals** for systematic model evaluation. The `ExtractionService` in the repo shows how to create an agent with an `output_type` pointing to a Pydantic model (`ReceiptDetails`) and then call it via `Runner.run` with a message containing an `input_image` and an instruction[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/get_agent_context.md#L86-L197). The `AuditService` uses a similar pattern: it builds an agent with a prompt that includes few‑shot examples and calls the agent to return a structured `AuditDecision`[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/audit.py#L166-L178). The Evals integration constructs evaluation records, runs graders and produces business metrics such as accuracy, F1 and ROI. This report incorporates those capabilities into the system design and refines the architecture to be production ready.

## 1. Review of the Prototype

The notebook you followed demonstrates how to extract receipt details using an OpenAI model, define audit prompts, create evals to measure extraction accuracy, and calculate cost trade‑offs. It defines Pydantic models for receipt details, a basic extraction prompt and an evaluation pipeline. However, the code is monolithic and oriented around demonstration; it lacks a production‑ready API, proper data storage, user management, and modularity.

## 2. Proposed API Architecture

A clean separation of concerns is critical for a sustainable codebase. Below is an improved directory layout based on the original sketch:

```
receipt‑processing‑api/
├── app/
│   ├── api/
│   │   ├── main.py               # FastAPI app instance and router registration
│   │   ├── dependencies.py       # common dependencies (DB session, auth, rate limits)
│   │   └── routes/
│   │       ├── receipts.py       # upload, list, get receipt details/audits
│   │       ├── audit_rules.py    # CRUD for audit rules, rule types
│   │       ├── prompts.py        # CRUD for custom prompt templates
│   │       ├── evaluations.py    # create & inspect evaluation runs and cost analyses
│   │       ├── cost_analysis.py  # cost analysis endpoints
│   │       └── users.py          # profile, billing and team management
│   ├── core/
│   │   ├── config.py             # environment variables, plan definitions
│   │   ├── security.py           # auth integration with Auth0/Clerk, roles
│   │   ├── database.py           # SQLAlchemy engine and session management
│   │   └── tasks.py              # Celery app and background task registration
│   ├── models/
│   │   ├── tables.py             # SQLAlchemy ORM models (User, Receipt, Rule…)
│   │   ├── schemas.py            # Pydantic request/response models (ReceiptDetails, AuditDecision, EvaluationRecord)
│   │   └── enums.py              # enumerations for rule types, plans, statuses
│   ├── services/
│   │   ├── extraction_service.py # asynchronous extraction using OpenAI Agents
│   │   ├── audit_service.py      # evaluate receipts against user rules using OpenAI Agents
│   │   ├── rule_engine.py        # parse/execute dynamic rule configurations
│   │   ├── evaluation_service.py # run evals, compute metrics and business analytics
│   │   ├── cost_service.py       # cost calculation
│   │   ├── storage_service.py    # MinIO/S3 file uploads and presigned URLs
│   │   └── billing_service.py    # integrate with Stripe, enforce limits per plan
│   ├── utils/
│   │   ├── prompts.py            # default extraction/audit prompts (few‑shot examples)
│   │   ├── metrics.py            # common grading functions (string_check, similarity)
│   │   └── helpers.py            # general helpers (date parsing, time windows)
│   └── worker.py                 # Celery/Dramatiq worker entry point
├── migrations/                   # Alembic migrations for database schema
├── tests/                        # unit and integration tests
├── requirements.txt              # pinned dependencies
├── docker-compose.yml            # local development environment (app, worker, db, redis, minio)
└── .env                          # configuration for secrets, database URLs
```

### 2.1 Domain Models

* **User / Organization** – stores the auth identifier, plan level (free, pro, business, enterprise), subscription metadata and quota counters. Business and enterprise plans can have an Organization table with members and roles (admin, reviewer, viewer).
* **Receipt** – holds metadata about the uploaded file (file name, storage path, image hash), processing status, extracted data (JSONB), audit decision (JSONB) and timestamps.
* **AuditRule** – belongs to a user or organization. Contains a `type` (threshold, keyword, category, time, cross‑receipt, ML, python), a `config` JSON with rule parameters, an `active` flag and metadata.
* **PromptTemplate** – allows users to override default prompts for extraction or auditing. Contains a name, type (`extraction`, `audit`, `evaluation`, `cost_analysis`) and text content.
* **Evaluation** – represents a benchmark run. Stores the model name (e.g. `gpt‑4o-mini`), the dataset path or receipt IDs, the grading configuration, summary metrics and status.
* **EvaluationItem** – each receipt processed in an evaluation run; stores predicted details and audit decisions, reference data, and per‑grader scores.
* **CostAnalysis** – stores parameters (false positive rate, false negative rate, per‑receipt processing cost, audit cost and missed audit cost) and computed totals. Linked to an evaluation.

### 2.2 Key Services

1. **Extraction Service (OpenAI Agents)** – accepts a receipt upload, stores the file in MinIO/S3 and enqueues a background job. The worker reads the file, preprocesses it, encodes it to base64 and creates an **Agent** with the `ReceiptDetails` Pydantic model as its `output_type`. It then calls `Runner.run` with a message that includes the base64‑encoded image (as an `input_image`) and an instruction to extract details[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/get_agent_context.md#L86-L197). The Agents SDK automatically returns structured output, so there is no need for manual JSON parsing[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/get_agent_context.md#L200-L207). The result is stored and the audit service is invoked.

2. **Audit Service (OpenAI Agents)** – applies all active rules for the receipt's owner. It constructs a prompt that embeds few‑shot examples and dynamic rule descriptions. An agent is created with the `AuditDecision` model as its `output_type` and called via `Runner.run` with the receipt JSON[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/audit.py#L166-L178). The structured decision (flags and reasoning) is returned and the rule engine interprets the user‑configured rule results. The rule engine types remain the same:

   * *Threshold rules* compare numeric fields (e.g. total amount > `$50`). They support nested fields and arrays (e.g. sum of item totals).
   * *Keyword rules* flag receipts containing certain strings in descriptions.
   * *Category rules* look for specific item categories (e.g. alcohol, travel, office supplies).
   * *Time‑based rules* use the receipt timestamp to detect weekends, after‑hours, or date ranges.
   * *Pattern rules* (business tier) operate across multiple receipts—for example, flagging repeated purchases from the same merchant within a week.
   * *ML/anomaly rules* (business tier) use unsupervised models to detect outliers.
   * *Custom Python rules* (business tier) allow advanced users to provide a restricted Python expression evaluated with safe libraries such as `asteval`. Expressions operate on the parsed receipt data and must run in a sandboxed environment to prevent security issues.
   * *LLM rules* (enterprise tier) prompt a language model with the receipt details and a user‑provided instruction; the model returns a boolean decision and reasoning.

3. **Evaluation Service (OpenAI Evals)** – orchestrates evaluations using the OpenAI Evals API. It builds a dataset of evaluation records by running the extraction and audit services on each receipt, loads ground truth from reference files and constructs `EvaluationRecord` objects. It then creates an eval configuration with custom graders and runs it through `openai.evals.runs.create`. The service caches eval configurations to avoid duplication and returns the run ID and report URL for each evaluation[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/evaluation_pipeline.py#L79-L111). Metrics like accuracy, precision, recall, F1‑score and false positive/negative rates are computed, and a cost analysis can be executed on top using the cost service.

4. **Cost Service** – calculates the financial impact of audit accuracy. Given the false positive rate (FP), false negative rate (FN), per‑receipt processing cost and cost of human audits/missed audits, it estimates annual cost:

```python
audit_cost  = total_audits * audit_cost_per_receipt
missed_cost = missed_audits * missed_audit_penalty
total_cost  = audit_cost + missed_cost + (receipt_count * per_receipt_cost)
```

This is similar to the function in the notebook. Users can adjust the cost parameters to run what‑if scenarios.

5. **Billing Service** – integrates with Stripe to manage subscriptions, enforce quotas and apply per‑receipt overage charges. It resets monthly counters and upgrades/downgrades plans. It should also support metered billing for additional API calls or receipts. When Evals and cost analyses are requested, it can charge based on evaluation size and compute time.

6. **Storage Service** – wraps MinIO/S3 with presigned upload/download URLs. A small image proxy can generate thumbnails for the dashboard.

#### OpenAI Agents & Evals Notes

The repository uses the **OpenAI Agents SDK** and **OpenAI Evals API** to simplify model integration and evaluation. When building your production API you should adhere to the following practices derived from the repository:

* **Use the Agents SDK for structured output** – create an `Agent` with a name, instructions (prompt) and an `output_type` pointing to a Pydantic model. Running the agent with `Runner.run` returns a `final_output` that is automatically parsed into the model[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/get_agent_context.md#L86-L197). This pattern is used in the `ExtractionService` and `AuditService` and eliminates manual JSON parsing[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/get_agent_context.md#L200-L207)[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/audit.py#L166-L178).
* **Send images using `input_image` messages** – encode receipt images to base64 data URLs and wrap them in a message with `"type": "input_image"` and `"detail": "auto"` or `"high"` for better OCR[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/get_agent_context.md#L156-L165). Follow this format to ensure the Responses API processes images correctly.
* **Leverage Evals for quality assurance** – build `EvaluationRecord` objects with predicted and reference data and submit them to `openai.evals.runs.create`. Use custom graders to score extraction accuracy, audit decisions and reasoning quality. The evaluation pipeline caches eval configurations to avoid duplication and returns report URLs for the OpenAI dashboard[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/evaluation_pipeline.py#L79-L111).
* **Cache evals and manage quotas** – maintain an in‑memory or database cache of eval configurations keyed by the grader set. Expose endpoints to check evaluation status and usage counts. Charge customers for large evaluations or cost analysis runs.

### 2.3 API Endpoints

| Endpoint | Method | Description | Plan Constraints |
| --- | --- | --- | --- |
| `/receipts` | `POST` | Upload a receipt image (multipart) with optional prompt ID. Returns receipt ID. Processing occurs asynchronously. | All plans; rate‑limited based on monthly receipt quota. |
| `/receipts/{id}` | `GET` | Fetch receipt metadata, extraction status and results. | All plans. |
| `/receipts/{id}/audit` | `GET` | Retrieve audit decision and reasoning. | All plans; custom rules only for Pro and above. |
| `/audit_rules` | `GET/POST` | List existing rules or create a new rule. Rule definition includes type and config. | Create limited by plan: 0 for Free (default rules only), ≤10 for Pro. Unlimited for Business/Enterprise. |
| `/audit_rules/{id}` | `PUT/DELETE` | Update or delete a rule. | Pro and above. |
| `/prompts` | `GET/POST` | Manage custom prompt templates for extraction/audit. | Pro tier can create limited prompts; Business/Enterprise unlimited. |
| `/evaluations` | `POST` | Create an evaluation run by uploading a dataset or selecting receipts. Returns evaluation ID. | Business plan and above. |
| `/evaluations/{id}` | `GET` | Retrieve evaluation summary and metrics. | Business/Enterprise. |
| `/evaluations/{id}/items` | `GET` | Paginated access to per‑receipt evaluation records. | Business/Enterprise. |
| `/evaluations/{id}/cost` | `POST` | Perform cost analysis on an evaluation using custom FP/FN/processing costs. | Enterprise plan. |
| `/users/me` | `GET` | Returns user profile, plan, and usage statistics. | All plans. |
| `/teams` | `POST/GET` | Create or list organizations; invite members and manage roles. | Business/Enterprise. |
| `/auth/callback` | `GET` | OAuth callback for Auth0/Clerk. Not counted against API usage. | – |

### 2.4 Workflow

1. **Upload & Extraction** – A user uploads a receipt via the API or frontend. The API stores the file and returns a job ID immediately. In the background, the worker calls the extraction model using the selected or default prompt. Upon completion it stores the structured result.
2. **Auditing** – Once extraction completes, the audit service evaluates the data using all active rules for that user. It sets boolean flags per rule and stores an overall decision and reasoning.
3. **Dashboard** – The frontend polls the API for the job status. When finished, it displays the extracted fields and audit outcomes. Users on paid plans can interactively add rules and re‑audit their receipts.
4. **Evaluations & Cost Analysis** – Business and enterprise users can upload labelled datasets (ground truth) and create evaluation runs. After the run finishes, the API returns metrics and allows cost analysis based on chosen parameters.

## 3. Tech‑Stack Analysis and Recommendations

### 3.1 Backend

**FastAPI** – FastAPI is still one of the most popular Python web frameworks. It builds on Starlette and Pydantic to offer async routing, automatic OpenAPI docs and great performance. It remains under active development and supports modern features such as dependency injection and background tasks. The planned API layout fits well into FastAPI's router‑based design.

**PostgreSQL** – An excellent choice for relational data with JSON support (JSONB). The official lifecycle chart shows version 16 supported through 2028[postgresql.org](https://www.postgresql.org/support/versioning/#:~:text=Releases%20%3B%2017%2C%2017,14%2C%202023%2C%20November%209%2C%202028). Version 16 introduces performance improvements, advanced partitioning and better logical replication. Using JSONB for storing extraction results and rule configs gives flexibility without sacrificing queryability.

**Redis + Celery** – Redis 7/8 provides a fast in‑memory store and message broker. The community edition continues to evolve, with Redis 8 bringing performance improvements and RESP3 support[redis.io](https://redis.io/blog/whats-new-in-two-may-2025/#:~:text=I%27m%20thrilled%20to%20announce%20the,faster%20commands). Celery remains the de‑facto task queue in Python; however, alternatives like **Dramatiq** or **RQ** may offer simpler configuration. If your workload involves millions of tasks, consider **Redis Streams** or Kafka for more robust queuing. For small to medium loads Celery with Redis is appropriate.

**MinIO/S3** – Storing images in object storage is industry standard. MinIO's S3 API compatibility allows easy migration to AWS S3 or GCP Cloud Storage in production. Ensure to configure lifecycle policies for data retention based on plan limits.

**LLM Providers & Langchain** – The prototype uses OpenAI's image models. OpenAI's GPT‑4o family supports image input and improved performance. The official OpenAI API is stable; support for **AsyncOpenAI** is built into the `openai` package used in the notebook. For additional vendors, you can integrate Anthropic's Claude or Cohere via Langchain. Store prompts and results to enable A/B testing. Use Weights & Biases to log model responses and track evaluation metrics across iterations.

### 3.2 Frontend

**Next.js 15** – Next.js 15 is stable (released October 2024) and adds several features relevant to your project: support for React 19, improved caching semantics, a static indicator during development and a new instrumentation API for server lifecycle observability[nextjs.org](https://nextjs.org/blog/next-15#:~:text=Next,js%2015%20today). It also adds a built‑in codemod CLI to ease upgrading from earlier versions[nextjs.org](https://nextjs.org/blog/next-15#:~:text=,times%20and%20Faster%20Fast%20Refresh). The default caching for GET requests is disabled[nextjs.org](https://nextjs.org/blog/next-15#:~:text=With%20Next,into%20caching), which means API responses should implement their own caching strategy (e.g. use HTTP headers or React Query's stale time). Considering your data is dynamic, disabling caching by default is beneficial.

**TypeScript** – Provides type safety and better developer experience. Modern Next.js projects almost universally use TypeScript.

**Tailwind CSS v4.1** – Tailwind v4.0 introduces a new high‑performance engine and modern CSS features like cascade layers, registered custom properties and color‑mix[tailwindcss.com](https://tailwindcss.com/blog/tailwindcss-v4#:~:text=Tailwind%20CSS%20v4,web%20platform%20has%20to%20offer). Installation has been simplified and it includes first‑party Vite and PostCSS plugins[tailwindcss.com](https://tailwindcss.com/blog/tailwindcss-v4#:~:text=,to%20bundle%20multiple%20CSS%20files). Version 4.1 released in April 2025 adds text‑shadow utilities, mask APIs, and improved browser compatibility[tailwindcss.com](https://tailwindcss.com/blog/tailwindcss-v4-1#:~:text=I%20wasn%27t%20sure%20it%20would,shadow%60%20utilities). Upgrading to v4 will improve build times and provide container queries out of the box. Ensure your component library is compatible with v4 (Shadcn and Tremor both migrated in 2025).

**shadcn/ui** – The shadcn library provides accessible, unstyled Radix UI components and a CLI to copy components into your project. Its July 2025 changelog shows continuous development: universal registry items allow sharing components across frameworks and local file support enables zero‑setup workflows[ui.shadcn.com](https://ui.shadcn.com/docs/changelog#:~:text=July%202025%20,Items). Shadcn recently migrated to the new `radix-ui` package[ui.shadcn.com](https://ui.shadcn.com/docs/changelog#:~:text=June%202025%20). For your dashboard, shadcn/ui combined with Tailwind CSS offers high‑quality building blocks.

**Tremor** – Tremor is a Tailwind‑first React library for charts and dashboards. The March 2025 release updated all components (AreaChart, BarChart, ComboChart, etc.) to Tailwind v4 and released v1.0 of many components[tremor.so](https://tremor.so/changelog#:~:text=). Using Tremor or Recharts will let you quickly implement analytics views.

**React Query / TanStack Query** – For managing server state, **React Query** (now called TanStack Query) offers caching, background synchronization, optimistic updates and pagination[dev.to](https://dev.to/rigalpatel001/react-query-or-swr-which-is-best-in-2025-2oa3#:~:text=React%20Query%20is%20a%20powerful,synchronization%2C%20pagination%2C%20and%20optimistic%20updates). SWR is a lighter alternative optimized for simple reads[dev.to](https://dev.to/rigalpatel001/react-query-or-swr-which-is-best-in-2025-2oa3#:~:text=SWR%20%28Stale,for%20a%20seamless%20user%20experience). Since your application requires mutations (rule creation), caching and optimistic updates, TanStack Query is the better choice. Pair it with Zustand for lightweight client state (e.g. UI preferences).

**UI & glassmorphism** – The Nexux example you linked showcases a glassmorphism design: elements sit on translucent panels over colourful backgrounds with blur and subtle shadows. To recreate this look in your Next.js dashboard:

* Use **Tailwind CSS utilities** like `bg-gradient-to-b from-white/60 to-white/30`, `backdrop-blur-lg`, `border-[1px] border-white/30` and `shadow-xl` to create frosted panels. The dev.to tutorial on glassmorphism notes that a translucent fill, a frosty blur and a subtle border are essential for the frosted glass effect[dev.to](https://dev.to/logrocket/how-to-implement-glassmorphism-with-css-19g1#:~:text=Let%27s%20understand%20the%20basic%20concepts,the%20look%20of%20frosted%20glass). The example uses a form element styled with these classes to achieve the desired look[dev.to](https://dev.to/logrocket/how-to-implement-glassmorphism-with-css-19g1#:~:text=The%20next%20step%20is%20to,lg%60%20utility).
* Ensure there is a **vibrant or contrasting background** behind the glass panels, as glassmorphic objects are almost invisible on plain backgrounds[dev.to](https://dev.to/logrocket/how-to-implement-glassmorphism-with-css-19g1#:~:text=Background%20color). A gradient or hero image similar to the Nexux landing page will make the frosted panels stand out.
* Create a **sense of depth and hierarchy** by adding drop shadows and a slight border shine; this elevates panels above the background and makes the interface feel layered[dev.to](https://dev.to/logrocket/how-to-implement-glassmorphism-with-css-19g1#:~:text=Let%27s%20understand%20the%20basic%20concepts,the%20look%20of%20frosted%20glass).
* Customise **shadcn/ui components** by adding these Tailwind classes. For example, wrap cards or modals in a `div` with the frosted classes, or override the component styles using the shadcn CLI.
* For interactive animations, integrate **framer‑motion** or the new `@framer` library. They pair naturally with Next.js 15 and allow you to animate card transitions and hover effects to match the Nexux site.
* Provide a **dark mode** that adjusts translucency and contrast. The tutorial warns that frosted glass becomes invisible on very dark backgrounds; use lighter translucency (e.g. white/40) and adjust shadows accordingly[dev.to](https://dev.to/logrocket/how-to-implement-glassmorphism-with-css-19g1#:~:text=Background%20color)[dev.to](https://dev.to/logrocket/how-to-implement-glassmorphism-with-css-19g1#:~:text=First%2C%20because%20glassmorphic%20objects%20require,everything%20is%20readable%20and%20accessible).

### 3.3 Infrastructure & Observability

**Docker & Kubernetes** – Containerization via Docker Compose for local development and Helm/Kustomize for production is standard. A managed Kubernetes service (EKS, GKE, or AKS) simplifies scaling. Use separate pods for API, worker, and UI. Configure horizontal pod autoscaling based on queue length and API latency.

**Stripe** – Handles subscription billing. Use Stripe's metered billing to charge per extra receipt. Webhooks can update plan limits and usage counters.

**Auth0/Clerk** – Provide user authentication via OAuth and SSO. Clerk has a developer‑friendly API and built‑in user management UIs. Either solution integrates with Next.js via middleware.

**Monitoring** – Use Sentry for error tracking and Datadog/New Relic for metrics. Track queue lag, extraction latency, audit failures and subscription events.

### 3.4 Suggested Enhancements or Alternatives

1. **Replace Celery with Dramatiq** – Dramatiq uses RabbitMQ or Redis and requires less configuration. It supports automatic retries and result storage. If you find Celery heavy, evaluate Dramatiq.
2. **Consider Postgres Row Level Security (RLS)** – For multi‑tenant SaaS, enabling RLS ensures that users can only access their own data. Combine with SQLAlchemy to automatically inject `user_id` conditions.
3. **Use PgBouncer or Supabase Realtime** – To handle high connection counts, a lightweight connection pooler helps. Supabase's Realtime API can push updates to the dashboard so users don't need to poll receipt status.
4. **OpenTelemetry** – Instrument FastAPI and Celery tasks with OpenTelemetry to get traces across services. Datadog and New Relic support OTel ingestion.
5. **Security** – Validate all user‑supplied rules. Sandbox custom Python expressions to prevent arbitrary code execution. Limit model prompts and ensure PII is handled securely.

## 4. Pricing Model Evaluation

Your proposed tiers are generous relative to market offerings. As a benchmark, Mindee's Starter plan (500 pages per month) costs €44/month with €0.05 per extra page[mindee.com](https://www.mindee.com/pricing#:~:text=Starter) and the Pro plan (2,500 pages) costs €179/month[mindee.com](https://www.mindee.com/pricing#:~:text=Pro). Your **Pro** plan offers 500 receipts/month for $29–49, which is competitive, especially considering custom audit rules, analytics and integrations. The **Business** plan (5,000 receipts for $149–299) sits between Mindee's Pro and Business tiers (2.5k and 10k pages) and includes advanced features like team management, ML‑based rules and cross‑receipt patterns. The **Enterprise** tier is comparable to Mindee's custom Enterprise plan with unlimited pages[mindee.com](https://www.mindee.com/pricing#:~:text=584%E2%82%AC%2Fmonth).

**Recommendations**:

* **Clarify overage pricing** – specify whether additional receipts are billed per scan or per page and whether unused credits roll over. Consider a smaller jump between Pro and Business (e.g. 2,500 receipts at $99) to match competitor tiers.
* **Free trial limitations** – a 7‑day data retention and 50 receipts/month is reasonable. To drive conversions, highlight extraction accuracy and show where custom rules would have saved money.
* **Audit rule limits** – 10 custom rules for Pro is adequate. Allow rule bundles or templates to speed adoption. For Business, unlimited rules are a selling point.
* **Evaluation & Cost Analysis** – Reserve these features for Business and Enterprise tiers. They require additional computation and provide significant value.
* **Team pricing** – For Business, include up to 10 users by default and charge per additional user to cover support costs. Enterprise can include unlimited users with negotiated pricing.

## 5. Implementation Phases

1. **Phase 1 – MVP**: implement receipt upload, extraction, default audit rules and a simple dashboard. Build the rule engine with threshold, keyword, category and time‑based rules. Support Free and Pro tiers. Integrate billing with Stripe and authentication with Auth0/Clerk. Use Celery/Redis for background tasks and MinIO for storage.

2. **Phase 2 – Team & Analytics**: add organizations, roles and multi‑user support. Build analytics dashboards using Tremor (spending by category, merchants, trends). Offer CSV/Excel exports and basic integrations (QuickBooks, Xero). Launch Business tier with unlimited custom rules, ML‑based anomaly detection and cross‑receipt pattern rules. Migrate components to Tailwind v4 and upgrade to Next.js 15 to leverage improved caching and React 19 support[nextjs.org](https://nextjs.org/blog/next-15#:~:text=Next,js%2015%20today)[tailwindcss.com](https://tailwindcss.com/blog/tailwindcss-v4#:~:text=Tailwind%20CSS%20v4,web%20platform%20has%20to%20offer).

3. **Phase 3 – Eval Framework & Cost Analysis**: implement evaluation runs and cost analysis endpoints. Allow enterprise customers to run A/B tests across different models (OpenAI, Anthropic) and measure performance. Expose ROI calculators and what‑if scenarios. Add human‑in‑the‑loop workflows and custom KPIs. Offer on‑prem deployments with dedicated infrastructure. Provide white‑label options and BI integrations.

## Conclusion

The proposed architecture transforms the prototype into a modular, scalable platform that supports receipt extraction, dynamic auditing, evaluations and cost analysis. Integrating the **OpenAI Agents SDK** means your extraction and audit services can be concise and reliable: `Agent` objects with `output_type` definitions produce structured output automatically, and the `Runner.run` helper handles message formatting and retries[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/get_agent_context.md#L86-L197)[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/audit.py#L166-L178). Using **OpenAI Evals** allows you to benchmark models and audit prompts at scale and to quantify business impact.[GitHub](https://github.com/kwasham/receipt-processing-api/blob/main/src/services/evaluation_pipeline.py#L79-L111)

FastAPI, PostgreSQL and Redis provide a solid backend foundation, while Next.js 15, Tailwind v4 and shadcn/ui/Tremor enable a modern frontend. Tailwind's `backdrop-blur` utilities make it straightforward to implement the glassmorphism aesthetic seen in the Nexux demo[dev.to](https://dev.to/logrocket/how-to-implement-glassmorphism-with-css-19g1#:~:text=Let%27s%20understand%20the%20basic%20concepts,the%20look%20of%20frosted%20glass)[dev.to](https://dev.to/logrocket/how-to-implement-glassmorphism-with-css-19g1#:~:text=The%20next%20step%20is%20to,lg%60%20utility), and shadcn/ui components can be wrapped in these classes to achieve the frosted‑glass effect. The tech stack is validated by recent updates: Next.js 15 introduces performance and caching improvements[nextjs.org](https://nextjs.org/blog/next-15#:~:text=Next,js%2015%20today), Tailwind v4 delivers a faster engine and modern CSS features[tailwindcss.com](https://tailwindcss.com/blog/tailwindcss-v4#:~:text=Tailwind%20CSS%20v4,web%20platform%20has%20to%20offer), and shadcn/ui and Tremor have adopted Tailwind v4[ui.shadcn.com](https://ui.shadcn.com/docs/changelog#:~:text=July%202025%20,Items)[tremor.so](https://tremor.so/changelog#:~:text=). Competitor pricing suggests your plans are well‑positioned[mindee.com](https://www.mindee.com/pricing#:~:text=Starter)[mindee.com](https://www.mindee.com/pricing#:~:text=Pro). With careful implementation of rule evaluation, sandboxing for custom code, and robust observability, the platform can deliver a user‑friendly and cost‑effective receipt inspection service.
