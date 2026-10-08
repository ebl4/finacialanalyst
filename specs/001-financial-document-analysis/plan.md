# Implementation Plan: Financial Document Analysis

**Branch**: `001-financial-document-analysis` | **Date**: 2026-10-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification and approved session plan

## Summary

Build a responsive financial-analysis web application with a Python service layer and a React/TypeScript client. A persisted LangGraph workflow coordinates four bounded LangChain agents: planner, permission-filtered retrieval, analysis, and validation. PostgreSQL with vector search stores application data and workflow checkpoints; S3-compatible object storage retains report binaries. Sensitive recommendations are durably paused in a human approval queue and cannot be treated as approved until an authorized person records a decision.

## Technical Context

**Language/Version**: Python 3.12; TypeScript 5.x

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy, Alembic, LangChain, LangGraph, PostgreSQL/pgvector; React, Vite

**Storage**: PostgreSQL with pgvector for records, extracted text, knowledge-base content, embeddings, and workflow checkpoints; S3-compatible object storage for uploaded report files

**Testing**: pytest; Vitest and React Testing Library; API and workflow integration tests; browser-level end-to-end tests for primary flows

**Target Platform**: Cross-platform Python web service and responsive desktop/mobile browsers

**Project Type**: Full-stack web application

**Performance Goals**: For supported reports within the configured size limit, acknowledge submission within 2 seconds; return status and ordinary workspace views within 2 seconds at the 95th percentile under the initial single-organization test load. Long-running analysis reports progress instead of blocking a user request.

**Constraints**: Enforce access on every report, search result, citation, workflow, and approval operation; persist restart-safe workflow state and audit history; do not let an agent authorize or execute a sensitive decision; never represent missing, partial, or unvalidated evidence as a complete conclusion; keep credentials out of source control.

**Scale/Scope**: Initial single-organization deployment with analysts and designated approvers; common financial report formats and configured knowledge sources; responsive web workspace.

## Constitution Check

The checked-in constitution is an unfilled template, not ratified project policy. No additional project-specific gates can be derived from it. Feature-level gates are:

- Evidence traceability and explicit uncertainty for material claims.
- Access control at retrieval and presentation boundaries.
- Durable human approval for sensitive recommendations; no agent-side approval.
- Persisted workflow and review history; interrupted jobs remain recoverable.
- Responsive, accessible desktop and mobile workflows.

**Gate result**: Pass, subject to enforcing these constraints in contracts, data state transitions, and tests.

## Project Structure

```text
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/versions/
├── app/
│   ├── api/                 # report, query, analysis, and approval endpoints
│   ├── auth/                # identity and role enforcement
│   ├── domain/              # typed entities and state transitions
│   ├── agents/              # planner, retrieval, analysis, validation
│   ├── workflows/           # LangGraph orchestration and checkpoints
│   ├── persistence/         # SQL repositories, object storage, vector retrieval
│   └── services/            # report intake, query, approval, audit
└── tests/
    ├── unit/
    ├── integration/
    └── api/
frontend/
├── package.json
├── vite.config.ts
├── src/
│   ├── app/
│   ├── features/
│   │   ├── reports/
│   │   ├── analysis/
│   │   ├── questions/
│   │   └── approvals/
│   └── shared/
└── tests/
    ├── unit/
    └── e2e/
specs/001-financial-document-analysis/
├── contracts/openapi.yaml
├── data-model.md
├── plan.md
├── quickstart.md
├── research.md
└── tasks.md
```

**Structure Decision**: Use separate `backend/` and `frontend/` projects so Python agent orchestration and the browser experience can be tested and deployed independently. Shared API contracts are described in OpenAPI; domain behavior remains on the backend.

## Architecture and Safety Decisions

- Keep orchestration explicit and typed. Agents return validated structured proposals; application services own state transitions, authorization, and side effects.
- Retrieval filters by the requesting user's access scope before ranking and before returning sources. Citations resolve through an authorization-checked source endpoint.
- Validation rejects malformed outputs and flags absent, conflicting, or insufficient evidence. It does not manufacture missing facts.
- A sensitive result is persisted as `pending_approval`, assigned to an authorized approver, and checkpointed before pausing. Only the approval service can move it to `approved` or `rejected`.
- Use PostgreSQL as the record of truth. Store original binaries in S3-compatible storage and persist object identifiers and integrity metadata in PostgreSQL.
- Provider-specific identity, LLM, embedding, object storage, and external knowledge integrations are configuration boundaries. Production requires explicitly configured providers; tests inject deterministic fakes.
- Do not add transaction execution to this product.

## Complexity Tracking

No constitution violations or unjustified architecture layers.
