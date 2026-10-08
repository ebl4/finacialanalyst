# Data Model: Financial Document Analysis

## Entities

### User and Access Scope

- `User`: stable identity, display name, active status.
- `Role`: analyst or approver permissions associated with a user and organization.
- `AccessScope`: organization/owner and any source-specific restrictions used to authorize report, knowledge, citation, and approval operations.
- Validation: all access checks are server-side; no access scope is accepted as authoritative from a client request.

### Financial Report

- `Report`: owner/access scope, original object reference, file name, media type, byte size, content digest, submission time, and lifecycle status.
- Statuses: `queued`, `processing`, `complete`, `failed`.
- `ExtractedContent`: text and source locations (page/section/offset), tied to a report and extraction revision.
- Validation: unsupported, unreadable, or failed extraction is visible as failed and cannot be marked complete.

### Information Source and Evidence

- `KnowledgeSource`: authorized source identity, type, access scope, indexing revision, and availability status.
- `EvidenceChunk`: extracted content, source location, access scope, and retrieval metadata. Embedding data is associated with an evidence chunk.
- `Citation`: stable source reference attached to a finding, answer, or recommendation.
- Validation: retrieval filters by access scope; citation resolution rechecks current authorization.

### Analysis Workflow

- `AnalysisRun`: report, requester, workflow status, timestamps, stage, error/limitation details, and checkpoint reference.
- Statuses: `queued`, `running`, `waiting_for_approval`, `complete`, `failed`.
- `WorkflowCheckpoint`: durable, versioned workflow state needed to resume processing safely.
- Validation: retries are idempotent for the same run and do not duplicate approval decisions or expose stale results as complete.

### Finding, Question, and Answer

- `Finding`: kind, normalized value where applicable, narrative, uncertainty, source citations, and analysis-run reference.
- `Question`: requesting user, authorized report/source scope, text, and request time.
- `Answer`: response, evidence citations, limitations, and question/analysis association.
- Validation: factual claims must be associated with citations or explicitly labeled as unsupported/uncertain.
- Questions and answers are retained with their report and requester so analysts can revisit earlier evidence-backed queries.

### Recommendation and Approval Decision

- `Recommendation`: proposal, rationale, assumptions, uncertainty, supporting evidence, sensitivity classification, assigned approver, and state.
- States: `draft`, `pending_approval`, `approved`, `rejected`, `superseded`.
- `ApprovalEvent`: recommendation, decision maker, outcome, reason, time, and audit metadata.
- Validation: only authorized approvers can decide; pending recommendations are never displayed as authorized decisions; state changes are recorded as append-only events.

## Relationships

- A user submits reports and questions; users can hold one or more roles within access scopes.
- A report has extracted content and can have multiple analysis runs.
- A knowledge source has access-scoped evidence chunks.
- An analysis run produces findings and recommendations and may pause for approval.
- Findings, answers, and recommendations reference one or more evidence citations.
- A recommendation may have multiple historical approval events but only one current decision state.

## Core state transitions

- Report: `queued -> processing -> complete | failed`.
- Analysis: `queued -> running -> waiting_for_approval | complete | failed`; after a final decision, resume to `complete`.
- Recommendation: `draft -> pending_approval -> approved | rejected`; a superseding revision marks an earlier recommendation `superseded` while preserving its audit trail.
- Approval event creation and recommendation state transition occur atomically.
