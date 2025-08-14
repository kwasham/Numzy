# Master Implementation Checklist for Numzy Receipt Processing API

## 🏗️ Architecture Overview

Production-grade receipt processing API with extraction, auditing, evaluation, and cost analysis capabilities.

## ✅ Completed Components

### Core Infrastructure

- [x] **FastAPI Backend** - Modular architecture with proper separation of concerns
- [x] **PostgreSQL with JSONB** - For flexible receipt and rule storage
- [x] **SQLAlchemy ORM** - All models defined (User, Receipt, AuditRule, etc.)
- [x] **Alembic Migrations** - Database schema versioning
- [x] **Clerk Authentication** - OAuth integration with role-based access
- [x] **Pydantic Schemas** - Request/response validation
- [x] **OpenAPI Documentation** - Auto-generated API docs
- [x] **Neon PostgreSQL** - Cloud database configured and connected
- [x] **Docker Compose** - Multi-service orchestration
- [x] **Redis** - Message broker for background tasks ✅ FULLY WORKING

### Services Implemented

- [x] **ExtractionService** - OpenAI Vision API for receipt OCR and parsing
- [x] **AuditService** - Rule evaluation with structured decisions
- [x] **Basic RuleEngine** - Threshold, keyword, category, and time-based rules
- [x] **EvaluationService** - Model benchmarking and metrics
- [x] **CostService** - Financial impact analysis
- [x] **StorageService** - MinIO/S3 wrapper ✅ FULLY WORKING
- [x] **BillingService** - Usage tracking foundation

### API Endpoints

- [x] `/receipts` - Upload and retrieve receipts ✅ FULLY TESTED
- [x] `/receipts/{id}` - Get specific receipt ✅ WORKING
- [x] `/receipts/{id}/reprocess` - Requeue processing for an existing receipt ✅ NEW
- [x] `/receipts/{id}/audit` - Get audit decisions
- [x] `/audit_rules` - CRUD for audit rules
- [x] `/prompts` - Custom prompt management
- [x] `/evaluations` - Create and view evaluation runs
- [x] `/users/me` - User profile and usage
- [x] `/teams` - Organization management
- [x] `/health` - Health check endpoint
- [x] `/receipts/batch` - Multi-file upload (bulk)

### Background Processing ✅ FULLY OPERATIONAL

- [x] **Dramatiq with Redis** - Background task queue configured and running
- [x] **Async extraction** - Receipt processing in background workers
- [x] **Task execution** - Worker processes running successfully
- [x] **Error retry logic** - Automatic retries on failure (3 attempts)
- [x] **Dev mode user override** - Simplified testing in development
- [x] **Connection pooling** - Database reliability with pool_pre_ping
- [x] **Progress tracking** - Extraction and audit progress updates
- [x] **Processing metrics** - Duration tracking (avg 5-11 seconds)
- [x] **Environment configuration** - Proper env var handling ✅ NEW
- [x] **Worker resilience** - Survives container restarts ✅ NEW

### Testing & Quality

- [x] **Comprehensive Stress Tests** - 99.8% success rate under load
- [x] **Real Receipt Data** - 208 test images (21.1MB) + 13,700+ receipts in DB
- [x] **Performance Baseline** - 7-8 req/s sustained, 100% success rate
- [x] **End-to-end pipeline tested** - Upload → Process → Extract → Audit → Store
- [x] **Worker resilience tested** - Handles connection drops gracefully
- [x] **Manual integration testing** - Receipt upload and processing verified ✅ NEW

### Receipt Processing Pipeline ✅ PRODUCTION READY

- [x] **File upload to MinIO** - Receipts stored with unique paths
- [x] **OpenAI Vision extraction** - Reliable OCR with structured output
- [x] **Simple audit implementation** - $50 threshold checking
- [x] **Status progression** - PENDING → PROCESSING → COMPLETED
- [x] **Error handling** - Failed status with error messages
- [x] **Processing time tracking** - Millisecond precision
- [x] **Task ID tracking** - Dramatiq message IDs stored ✅ NEW
- [x] **User context passing** - user_id flows through pipeline ✅ NEW

## 🚧 In Progress / Needs Implementation

### Critical Path Items

#### 1. Background Task Enhancements

- [x] **Task status tracking** - Task IDs stored and queryable ✅ DONE
- [ ] **Result webhooks** - Notify when processing complete
- [ ] **Batch processing** - Handle multiple receipts in one task
- [ ] **Priority queues** - Fast lane for Pro users
- [ ] **Dead letter queue** - Handle permanently failed tasks
- [ ] **Task cancellation** - Allow users to cancel pending tasks

#### 2. File Storage Completion

- [x] **MinIO integration** - Upload/download fully working ✅ DONE
- [x] **Presigned URL generation** for secure downloads ✅ DONE
- [ ] **File lifecycle policies** - Retention based on plan
- [ ] **Thumbnail generation** for dashboard preview
- [ ] **CDN integration** for fast image serving
- [ ] **Multi-format support** - PDF receipts

#### 3. Extended Rule Engine

- [x] **Threshold rules** - Working with configurable limits
- [ ] **Fix async audit service** - Resolve event loop issues
- [ ] **Pattern rules** - Regex matching implementation
- [ ] **ML/Anomaly rules** - Integrate scikit-learn or similar
- [ ] **Python rules** - Sandboxed expression evaluation
- [ ] **LLM rules** - Natural language rule evaluation
- [ ] **Cross-receipt patterns** - Multi-receipt analysis
- [ ] **Rule testing interface** - Preview rule effects

#### 4. Natural Language Features

- [x] **MCP Prompt Server** - Running but needs integration
- [ ] **Connect MCP to main API** - Currently isolated
- [ ] **NL Rule Creation** - Parse "Flag receipts over $100 on weekends"
- [ ] **Rule explanation** - Convert structured rules to human-readable
- [ ] **Prompt caching** - Store generated prompts as templates
- [ ] **Multi-language support** - Extract from non-English receipts

### Frontend Requirements

#### 5. Next.js 15 Dashboard

- [x] **Project setup** with TypeScript
- [x] **Tailwind v4** configuration
- [x] **Shadcn/ui** component library
- [x] **Tremor** for analytics charts
- [x] **TanStack Query** for state management ✅ DONE

#### 6. Core UI Features

- [x] **Basic receipt upload interface** (upload working)
- [x] **Receipt upload interface** with drag-and-drop ✅ DONE
- [x] **Batch uploads** — Parallel and batch modes with progress ✅ NEW
- [x] **Receipt viewer** with extracted data display (modal)
- [ ] **Rule builder** - Visual and natural language
- [ ] **Analytics dashboard** - Spending trends, categories
- [ ] **Evaluation results** - Metrics and confusion matrices
- [ ] **Cost analysis** - What-if scenarios
- [x] **Processing status** - Real-time updates (list + modal polling with progress)
- [ ] **Receipt search** - Filter by date, merchant, amount

#### 7. Design Implementation

- [ ] **Glassmorphism aesthetic** - Frosted panels, gradients
- [ ] **Dark mode support**
- [ ] **Responsive design** - Mobile friendly
- [ ] **Loading states** and optimistic updates
- [ ] **Error boundaries** and fallbacks

### Production Readiness

#### 8. Billing Integration

- [ ] **Stripe subscription setup**
- [ ] **Metered billing** for overages
- [ ] **Usage tracking** and quotas
- [ ] **Invoice generation**
- [ ] **Payment webhooks**
- [ ] **Plan upgrade/downgrade flows**

#### 9. Performance Optimization

- [x] **Connection pooling** - Sync SQLAlchemy with pool_pre_ping
- [ ] **Redis caching** - Frequent queries
- [ ] **Image preprocessing** optimization
- [x] **Batch API endpoints** for bulk operations ✅ DONE
- [ ] **Rate limiting** per user/tier
- [x] **Rate limiting** per user/tier
- [x] **Database indexes** for common queries
- [ ] **Query optimization** - N+1 prevention

#### 10. Monitoring & Observability

- [ ] **OpenTelemetry** instrumentation
- [ ] **Sentry** error tracking
- [x] Initial SDK integration (frontend Next.js App Router + backend FastAPI/worker) verified in dev
- [x] Remove legacy frontend SDK files; use `app/instrumentation.ts` exclusively
- [x] Add release tagging in frontend (`NEXT_PUBLIC_SENTRY_RELEASE`) and enable source map upload via `withSentryConfig`
- [ ] Configure CI secrets and release wiring for source map upload
- [ ] Set `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`, `SENTRY_RELEASE`
- [ ] Set `NEXT_PUBLIC_SENTRY_DSN` and `NEXT_PUBLIC_API_URL` in CI/hosting env
- [ ] Export `NEXT_PUBLIC_SENTRY_RELEASE` during build to match server/client release
- [ ] Ensure consistent environment/release tags across frontend, API, and worker (set `SENTRY_RELEASE` for backend/worker)
- [ ] Verify CI sourcemap upload associates artifacts with the release in Sentry
- [ ] Runtime verification: trigger frontend `/api/sentry-test` and backend `/debug/sentry`, and force a worker error; confirm events appear with correct release/environment
- [ ] Add alert rules (new issue, spike, regression) and routing to team
- [ ] Tune sampling (traces/profiles) per environment (e.g., lower in prod)
- [ ] Configure PII scrubbing and inbound filters (ignore noisy/benign errors)
- [ ] Optional: enable Sentry tunnel in Next.js to avoid ad-blockers in prod
- [ ] **Datadog/New Relic** metrics
- [x] **Structured logging** - Worker logs with context
- [x] **Health check endpoints** - Basic health endpoint
- [ ] **Performance dashboards**
- [ ] **Uptime monitoring**
- [x] **Worker health monitoring** - Via Docker logs ✅ PARTIAL

#### 11. Security Hardening

- [ ] **API key rotation** mechanism
- [ ] **Sandbox Python expressions** securely
- [ ] **Input sanitization** for all user content
- [ ] **PII handling** compliance
- [ ] **CORS configuration** for production
- [ ] **Rate limiting** by IP and user
- [ ] **Security headers** (CSP, HSTS, etc.)
- [ ] **File upload validation** - Virus scanning

#### 12. DevOps & Deployment

- [x] **Docker development images** - Working compose setup
- [x] **Multi-service orchestration** - API, workers, Redis, MinIO, MCP
- [ ] **Docker production images** - Optimized builds
- [ ] **Kubernetes manifests** (Helm/Kustomize)
- [x] **CI/CD pipeline** - GitHub Actions ✅ DONE (CI added; Sentry/CD pending)
- [ ] **Database backup** strategy
- [ ] **Zero-downtime deployment**
- [ ] **Environment management** (dev/staging/prod)
- [ ] **Secrets management** - Vault or similar

## 📋 Next Steps Priority Order

### Phase 1: Frontend Foundation (Week 1)

1. **Initialize Next.js 15 project**
2. **Set up authentication flow** with Clerk
3. **Create basic receipt upload/view UI**
4. **Display extracted data and audit results**
5. **Show processing status and progress**

### Phase 2: Core UI Features (Week 2)

1. **Rule management interface**
2. **Receipt history and search**
3. **Basic analytics dashboard**
4. **User profile and settings**

### Phase 3: Advanced Features (Week 3)

1. **Fix async audit service integration**
2. **Implement remaining rule types**
3. **Natural language rule creation** via MCP
4. **Advanced analytics and reports**
5. **Team management UI**

### Phase 4: Production Prep (Week 4)

1. **Stripe billing integration**
2. **Performance optimization**
3. **Security audit**
4. **Monitoring setup**
5. **Production deployment**

### Phase 5: Launch Ready (Week 5)

1. **Load testing at scale**
2. **Documentation completion**
3. **Beta user onboarding**
4. **Marketing site**

## 🎯 Definition of Done

### MVP Launch Criteria

- [x] Users can upload receipts and see extracted data ✅ DONE
- [x] Basic audit rules work (threshold rules at $50) ✅ DONE
- [ ] Dashboard shows receipt history and basic analytics
- [ ] Free and Pro tiers are enforced
- [ ] Billing works for Pro subscriptions
- [x] System handles 10+ concurrent users ✅ TESTED
- [ ] Documentation is complete
- [x] Background processing is reliable ✅ DONE

### Production Launch Criteria

- [ ] All rule types implemented
- [ ] Natural language features working
- [ ] Team/organization support
- [ ] Evaluation framework complete
- [ ] 99%+ uptime SLA achievable
- [ ] Monitoring and alerting active
- [ ] Security audit passed
- [ ] Load tested to 100+ concurrent users

## 📊 Current Status Summary

**Backend**: ~85% complete ✅ +5%

- Core API working
- Authentication done
- Basic rules implemented
- Background processing working end-to-end
- Receipt extraction pipeline complete
- File storage fully operational
- Needs: Advanced rules, billing, production hardening

**Frontend**: ~25% complete ✅ +25%

- Upload working
- Recent receipts list with auto-refresh
- Detail modal with extracted data, audit results, live progress bars, and reprocess
- Needs: search/history, analytics, rule builder, query/cache layer

**Infrastructure**: ~70% complete ✅ +10%

- Local dev environment working
- Cloud database connected
- Background workers running reliably
- MinIO storage integrated
- Redis message broker configured
- All services containerized
- Needs: Production deployment, monitoring, scaling

**Overall Project**: ~60% complete ✅ +10%

## 🎉 Recent Achievements

- ✅ Successfully debugged and fixed Dramatiq Redis connection issues
- ✅ Receipt upload → extraction → audit pipeline fully operational
- ✅ Environment variable configuration properly handled
- ✅ Worker persistence across container restarts
- ✅ File storage with MinIO working perfectly
- ✅ Task ID tracking implemented for status queries
- ✅ User context properly passed through async pipeline
- ✅ Manual testing verified end-to-end functionality
- ✅ Frontend: Receipt detail modal with live progress bars and reprocess action
- ✅ Frontend: Recent receipts list auto-refresh without page reload

## 🐛 Known Issues

- [ ] Async audit service has event loop conflicts - using sync workaround
- [ ] LLM audit rules need prompt template repository fix
- [ ] Some audit rules have malformed configs (e.g., "string" rule)
- [x] ~~SSL connection drops occasionally~~ - handled by retry mechanism ✅ RESOLVED
- [ ] MCP server running but not integrated with main API
- [ ] Dramatiq middleware warnings (duplicate middleware) - cosmetic issue

## 🚀 Immediate Next Steps

1. **Sentry follow-ups**
	- [x] Remove legacy frontend Sentry config files and rely on `app/instrumentation.ts`
	- [ ] Configure release versioning and source map upload in CI
	- [ ] Set CI/host secrets: `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`, `SENTRY_RELEASE`, `NEXT_PUBLIC_SENTRY_DSN`, `NEXT_PUBLIC_API_URL`
	- [ ] Export `NEXT_PUBLIC_SENTRY_RELEASE` during build; ensure backend/worker use `SENTRY_RELEASE`
	- [ ] Verify runtime: no Next.js `headers()` warning on `/`; trigger frontend `/api/sentry-test` and backend `/debug/sentry`; confirm events with correct release/env
	- [ ] Verify CI run uploads sourcemaps to the same release and resolves stack traces
	- [ ] Create alert rules (new issue, spike, regression) and routing
	- [ ] Tune error/performance sampling for each environment
	- [ ] Add PII scrubbing and inbound filters; consider enabling Sentry tunnel in prod
2. **Resolve metrics port conflict** - Fix or disable duplicate Prometheus exposition in worker (dev)
3. **Integrate MCP Server** - Connect NL features into main API when ready

185381ae748d942dc3f621da24e6d09d17922c7cabc8d30ef94afae4b06345e1