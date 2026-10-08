# Tasks: Financial Document Analysis

**Input**: Design documents from `specs/001-financial-document-analysis/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story so each journey has an independent verification point.

## Phase 1: Setup

**Purpose**: Establish the full-stack project structure.

- [x] T001 Create backend, frontend, and test directories described in `specs/001-financial-document-analysis/plan.md`
- [x] T002 Initialize Python service dependencies and test configuration in `backend/pyproject.toml`
- [x] T003 Initialize React and TypeScript client scripts and dependencies in `frontend/package.json`
- [x] T004 Add development setup and environment variable guidance in `README.md` and `backend/.env.example`

## Phase 2: Foundational

**Purpose**: Implement shared data, state, configuration, and permission boundaries before story features.

- [x] T005 Define runtime settings and fail-fast provider configuration in `backend/app/core/config.py`
- [x] T006 Define SQLAlchemy entities and enums for users, reports, sources, analyses, findings, recommendations, and approvals in `backend/app/persistence/models.py`
- [x] T007 Configure database sessions, migrations, and vector extension setup in `backend/alembic/` and `backend/app/persistence/database.py`
- [x] T008 Implement authenticated user and role context plus ownership/approver authorization checks in `backend/app/auth/dependencies.py`
- [x] T009 Define shared API schemas, problem responses, request validation, and error handling in `backend/app/api/schemas.py` and `backend/app/main.py`
- [x] T010 Define typed LangGraph state, agent output schemas, and persisted checkpoint wiring in `backend/app/workflows/state.py` and `backend/app/workflows/graph.py`

## Phase 3: User Story 1 - Submit and understand a financial report (Priority: P1)

**Goal**: An analyst uploads a report, sees processing status, and reviews traceable findings.

**Independent Test**: Upload a supported report, verify persisted status and extracted text, then inspect findings with source page references; verify unreadable input ends in a visible failure state.

- [x] T011 [P] [US1] Test report upload validation and status transitions in `backend/tests/unit/test_upload_and_state.py`
- [x] T012 [P] [US1] Test document extraction and source-location retention in `backend/tests/unit/test_document_extraction.py`
- [x] T013 [US1] Implement S3-compatible report storage and integrity metadata in `backend/app/persistence/object_storage.py`
- [x] T014 [US1] Implement PDF extraction and page citations in `backend/app/services/document_extraction.py`
- [x] T015 [US1] Implement report submission, persistence, queued processing, and status endpoints in `backend/app/api/reports.py` and `backend/app/workflows/worker.py`
- [x] T016 [US1] Implement planner, analysis, and validation agent nodes and persist source-linked findings in `backend/app/agents/` and `backend/app/workflows/graph.py`
- [x] T017 [US1] Add report upload/status and evidence-linked finding views in `frontend/src/App.tsx`

## Phase 4: User Story 3 - Review recommendations and approve sensitive decisions (Priority: P1)

**Goal**: Sensitive recommendations are durably routed to authorized humans and cannot be treated as approved without their decision.

**Independent Test**: Create a sensitive recommendation; verify pending status and approver routing survive a workflow restart; deny an unauthorized decision and record the attempt; approve/reject as the designated approver and verify the immutable event.

- [x] T018 [P] [US3] Test approval authorization, pending-state invariants, and audit events in `backend/tests/api/test_approvals.py`
- [x] T019 [US3] Route recommendations to persisted pending approval and assign a designated approver in `backend/app/services/analysis_processing.py`
- [x] T020 [US3] Implement assigned approver queue and row-locked approve/reject endpoint in `backend/app/api/approvals.py`
- [x] T021 [US3] Implement recommendation rationale, evidence, limitations, and decision-history views in `frontend/src/App.tsx`

## Phase 5: User Story 2 - Find relevant supporting information (Priority: P2)

**Goal**: Analysts query permitted report and knowledge sources and receive cited answers or explicit evidence gaps.

**Independent Test**: Ask a question answerable from authorized sources and verify citations; ask an unanswerable question and verify insufficiency is explicit; verify disallowed sources are never returned.

- [ ] T022 [P] [US2] Test access-filtered retrieval, citation provenance, and insufficient-evidence responses in `backend/tests/integration/test_retrieval.py`
- [x] T023 [US2] Implement knowledge-source ingestion, chunk persistence, and vector indexing in `backend/app/api/knowledge.py` and `backend/app/persistence/vector_store.py`
- [x] T024 [US2] Implement permission-filtered retrieval agent and question/answer endpoint in `backend/app/agents/retrieval.py` and `backend/app/api/questions.py`
- [x] T025 [US2] Implement citation resolution with current access recheck in `backend/app/api/reports.py` and `backend/app/api/knowledge.py`
- [x] T026 [US2] Implement question, cited-answer, and evidence-gap views in `frontend/src/App.tsx`

## Phase 6: User Story 4 - Work in a clear, polished analysis workspace (Priority: P3)

**Goal**: Analysts and approvers can efficiently navigate a polished, responsive workspace.

**Independent Test**: Complete report discovery, citation inspection, and pending-approval discovery at desktop and mobile viewport sizes without losing essential actions or statuses.

- [ ] T027 [P] [US4] Test navigation, report status, evidence, and approval visibility on mobile layouts in `frontend/tests/e2e/workspace.spec.ts`
- [x] T028 [US4] Build responsive application shell, navigation, and report dashboard in `frontend/src/App.tsx` and `frontend/src/styles.css`
- [x] T029 [US4] Add responsive analysis and approval interactions in `frontend/src/App.tsx` and `frontend/src/styles.css`

## Phase 7: Polish and Cross-Cutting Concerns

**Purpose**: Verify the full workflow and provide reproducible setup.

- [ ] T030 [P] Add end-to-end submission, analysis, retrieval, and approval flow tests in `backend/tests/integration/` and `frontend/tests/e2e/`
- [x] T031 Add safe document-ingestion and hostile-instruction handling tests in `backend/tests/unit/test_agent_context.py`
- [ ] T032 Validate authorization on report, citation, workflow, and approval paths in `backend/tests/api/`
- [ ] T033 Run and document quickstart validation steps in `specs/001-financial-document-analysis/quickstart.md` and `README.md`
- [x] T034 Verify lint, type-check, offline migrations, and test commands in `backend/pyproject.toml` and `frontend/package.json`

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: No dependencies.
- **Foundational**: Depends on Setup and blocks all story work.
- **US1**: Depends on Foundational.
- **US3**: Depends on Foundational and US1 recommendation/workflow persistence.
- **US2**: Depends on Foundational; can proceed independently from US1 once retrieval interfaces exist.
- **US4**: Depends on the report, analysis, question, and approval API contracts needed by its screens.
- **Polish**: Depends on all selected user stories.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; delivers report intake and traceable analysis.
- **US3 (P1)**: Uses the recommendation and workflow records from US1; then provides approval and audit behavior.
- **US2 (P2)**: Starts after Foundational and adds knowledge-base/RAG question-answering.
- **US4 (P3)**: Integrates the completed user-facing API journeys into the responsive workspace.

### Parallel Opportunities

- Setup tasks can be split between backend and frontend.
- In US1, upload tests, extraction tests, and the frontend report surface are parallelizable once shared contracts are stable.
- In US2, retrieval tests and frontend question surface can proceed independently of the retrieval implementation.
- In US4, UI end-to-end test definition and responsive application shell can proceed in parallel against the agreed API contract.

## Implementation Strategy

Deliver an MVP centered on US1: persistent report upload and processing, source-linked findings, and clear failure states. Add US3 before exposing sensitive recommendations, then US2 retrieval and US4 workspace polish. At every increment, keep approval enforcement and source authorization on the server and preserve the current feature specification's explicit no-transaction-execution boundary.
