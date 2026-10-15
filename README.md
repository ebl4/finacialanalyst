# Financial Analyst

A responsive financial-report analysis workspace with a Python API, persisted agent workflow, cited findings, and human approval for sensitive recommendations.

## Project status

The product is being developed from the feature specification in `specs/001-financial-document-analysis/`. Production use requires configured identity, model, PostgreSQL/pgvector, and S3-compatible storage providers. Agent output is advisory; sensitive decisions must be approved by an authorized human.

## Project layout

- `backend/` — Python API, domain services, persistent workflow, and tests
- `frontend/` — React/TypeScript responsive workspace
- `specs/001-financial-document-analysis/` — requirements, design, and execution tasks

See the [step-by-step local setup guide](specs/001-financial-document-analysis/quickstart.md) to start the database, backend API, and web application on Windows.

For token-free local testing, the guide also explains how to enable the development-only guest analyst and guest approver accounts. Demo mode is disabled in production and must not be used with real financial data.
