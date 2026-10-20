# Quickstart: Financial Document Analysis

## Prerequisites

- Windows with PowerShell, Python 3.12 or newer, Node.js LTS with npm, and Docker Desktop.
- A local demo mode can be used without an organization-issued access token.
- An OpenAI or Google Gemini API key is needed only for report analysis, question answering, and embeddings.

Docker is used below to run PostgreSQL/pgvector and MinIO locally. The app itself runs directly on your computer.

## Local setup

Follow these steps in PowerShell. Run the commands from the project root (`C:\Projects\DotNet\finacialanalyst`) unless a step tells you to change directories.

### 1. Start local database and object storage

Make sure Docker Desktop is running, then start PostgreSQL with pgvector:

```powershell
docker run -d --name financial-pgvector `
  -e POSTGRES_DB=financial `
  -e POSTGRES_USER=financial `
  -e POSTGRES_PASSWORD=localdevpassword `
  -p 5432:5432 `
  -v financial_pgdata:/var/lib/postgresql/data `
  pgvector/pgvector:pg16
```

Start MinIO, the local S3-compatible storage service:

```powershell
docker run -d --name financial-minio `
  -p 9000:9000 -p 9001:9001 `
  -e MINIO_ROOT_USER=localminio `
  -e MINIO_ROOT_PASSWORD=localminio123 `
  -v financial_minio:/data `
  pgsty/silo:RELEASE.2026-10-15T00-00-00Z-distroless server /data --console-address ":9001"
```

Open `http://localhost:9001`, sign in with `localminio` / `localminio123`, and create a bucket named `financial-reports`. These credentials and services are for local development only.

To check that both containers started, run:

```powershell
docker ps
```

### 2. Configure the backend

Copy the example environment file and open it for editing:

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

#### Optional: configure OpenAI or Gemini for financial analysis

You can sign in and explore the workspace without an AI API key. To analyze uploaded reports or ask questions, choose one provider and configure its API key. Set `AI_PROVIDER=openai` to use OpenAI, or `AI_PROVIDER=gemini` to use Google Gemini. Only the selected provider's key is required.

For OpenAI, create an API key in the [OpenAI Platform](https://platform.openai.com/) (a ChatGPT subscription alone does not include API usage). Set `OPENAI_API_KEY` and leave `AI_PROVIDER=openai`.

For Gemini, create an API key in [Google AI Studio](https://aistudio.google.com/app/apikey), set `AI_PROVIDER=gemini` and `GOOGLE_API_KEY`, and leave `OPENAI_API_KEY` blank. The defaults use `gemini-2.5-flash` for analysis and `gemini-embedding-001` for embeddings; the embedding output is configured to match the database's 1536-dimensional vector column.

Treat API keys like passwords: do not commit them, put them in frontend code, or share them in chat. Follow your organization's rules for model use and spending limits. Changing the embedding provider or model makes previously generated vectors incompatible; the app keeps them out of retrieval until they are re-indexed. Choose the provider before indexing reports and knowledge sources, or re-upload/re-index those sources after changing providers.

For local demo mode, set these values in `backend\.env`. Leave both provider keys blank if you only want to test guest login and navigate the workspace. For Gemini, change `AI_PROVIDER` to `gemini` and set `GOOGLE_API_KEY` instead:

```dotenv
APP_ENV=development
DEMO_MODE=true
DEMO_AUTH_SECRET=<a random secret with at least 32 characters>
AI_PROVIDER=openai
OPENAI_API_KEY=<API key for your OpenAI project>
GOOGLE_API_KEY=
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET=financial-reports
S3_ACCESS_KEY_ID=localminio
S3_SECRET_ACCESS_KEY=localminio123
```

To generate a strong demo signing secret, open PowerShell and run:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the printed value into `DEMO_AUTH_SECRET`. Keep `DEMO_MODE=true` only for local development or automated tests. The backend rejects demo mode in production. The demo accounts have fixed shared identities and are not private: anyone who can reach this local demo can use both the analyst and approver roles. Do not expose the demo server to the internet or upload real financial documents. Never commit `backend\.env`.

### 3. Install and prepare the Python backend

```powershell
Set-Location backend
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

The `python --version` output must be 3.12 or newer. If it is older, install a supported Python version and use that version to create the virtual environment.

### 4. Start the backend API

In this PowerShell window, still in `backend\`, run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Leave this window open. Check `http://127.0.0.1:8000/health` in your browser; it should display `{"status":"ok"}`. The API documentation is at `http://127.0.0.1:8000/docs`.

### 5. Install and start the web application

Open a **second** PowerShell window at the project root, then run:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Leave this window open too. Open the URL printed by Vite, normally `http://127.0.0.1:5173`.

### 6. Sign in and use the workspace

With `DEMO_MODE=true`, the connection screen offers two guest choices:

- **Guest analyst** — upload and review reports, ask questions, and create analyses.
- **Guest approver** — review and decide recommendations assigned to the demo approver.

Click either guest role to enter without a password or organization token. The backend issues a short-lived demo token automatically. To test approvals, first sign in once as **Guest approver**, sign out, then sign in as **Guest analyst** before submitting a report. Demo users share these fixed accounts and their data; do not use the demo for real decisions or confidential reports.

If demo mode is off, the app instead requires an organization-issued RS256 API access token and its matching issuer, audience, and public key. Contact your identity-provider administrator for those values. Report analysis and question answering require a key for the provider selected by `AI_PROVIDER`.

If report submission reports a missing provider key, set `OPENAI_API_KEY` (`AI_PROVIDER=openai`) or `GOOGLE_API_KEY` (`AI_PROVIDER=gemini`) in `backend\.env` and restart the backend API. Do not put keys in frontend settings or share them in chat.

### Stop local services

Press `Ctrl+C` in each PowerShell window running Uvicorn or Vite. To stop the database and object-storage containers but keep their data, run:

```powershell
docker stop financial-pgvector financial-minio
```

Start them again later with:

```powershell
docker start financial-pgvector financial-minio
```

## Validation scenarios

1. Submit a supported report as an analyst. Verify the report is retained and its visible state moves through queued/processing to complete, or reports a clear failure.
2. Open analysis findings and follow each citation. Verify citations resolve to the relevant page or passage and that access is checked again when opened.
3. Ask a question answerable from permitted sources, then ask one with no supporting evidence. Verify the first answer cites sources and the second clearly reports the evidence gap; reload the report and confirm the question history persists.
4. Generate a recommendation classified as sensitive. Verify its state is pending, it appears in the assigned approver's queue, and restarting the workflow does not lose it.
5. Attempt to decide the recommendation as an unauthorized user. Verify the server denies the action and creates an audit event; as the designated approver, approve or reject it and verify the status/history.
6. Test unreadable input and unavailable knowledge/object storage. Verify the UI reports limitations and never presents partial work as complete.
7. Complete the report-review and approval journeys at desktop and mobile viewport sizes. Verify evidence, status, and actions remain usable.

## Test commands

From `backend\`, run `.\.venv\Scripts\python.exe -m ruff check .` and `.\.venv\Scripts\python.exe -m pytest`. From `frontend\`, run `npm run build` and `npm test`. Integration tests require PostgreSQL/pgvector and an S3-compatible test service. Unit tests do not require production credentials.

See [the OpenAPI contract](./contracts/openapi.yaml) and [the data model](./data-model.md) for API and persistence expectations.
