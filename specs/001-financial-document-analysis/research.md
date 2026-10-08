# Research: Financial Document Analysis

## Decisions

### Python web service and browser client

- **Decision**: Use FastAPI/Pydantic for the Python service and React/TypeScript with Vite for the responsive browser client.
- **Rationale**: The API layer supports typed boundaries around the Python workflow; a dedicated browser application supports the requested polished, mobile-ready analyst and approver experience.
- **Alternatives considered**: Server-rendered Python pages would reduce the initial frontend toolchain, but provide less separation for an interactive evidence review and approval workspace.

### Stateful agent orchestration

- **Decision**: Use LangChain for agent/model integrations and LangGraph for explicit, checkpointed orchestration.
- **Rationale**: The required workflow has distinct agent responsibilities, durable progress, failures, and a human approval pause/resume point. A state graph makes those transitions inspectable and testable rather than leaving control flow to an unconstrained agent.
- **Alternatives considered**: A single agent loop or stateless chain would not express the required persisted approval wait and multi-step resume behavior as clearly.

### Durable storage

- **Decision**: Use PostgreSQL with pgvector for structured state, extracted content, knowledge metadata, vector retrieval, and workflow checkpoints; store original document binaries in compatible object storage.
- **Rationale**: This matches the approved persistence decision while keeping large files separate from transactional records. PostgreSQL remains the source of truth for metadata, permissions, statuses, and audit history.
- **Alternatives considered**: Store all data and binaries in one database (simpler operational inventory but mixes large object storage with transactional data); defer provider choice (less actionable for migrations and integration tests).

### Human authorization

- **Decision**: Approval is a server-owned state transition, never an agent tool. Sensitive decisions persist as pending, are assigned to an approver, and can be changed only by an authorized approval operation.
- **Rationale**: Agent prompts and outputs are not security boundaries. A persisted state transition is necessary to enforce the feature's core human oversight requirement across restarts and retries.
- **Alternatives considered**: Ask an agent to approve or rely on client-side status display; both fail to provide enforceable authorization.

### Integration configuration

- **Decision**: Keep LLM, embeddings, object storage, identity, and external knowledge providers behind explicit configuration and narrow interfaces; fail clearly when production-required configuration is absent.
- **Rationale**: The user has not selected vendors or deployment infrastructure. This supports a runnable test suite without credentials while preventing a fake success path in a deployed service.
- **Alternatives considered**: Hard-code a single provider, or silently substitute a local/demo response when provider configuration is missing.

## Outstanding deployment decisions

- Select production identity provider and organization/user provisioning model.
- Select LLM and embedding providers, model versions, and data processing region.
- Define supported report formats, maximum upload sizes, retention/deletion rules, and sensitivity thresholds.
- Select the production object-storage provider and deployment target.
