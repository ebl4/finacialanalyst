# Quickstart: Financial Document Analysis

## Prerequisites

- Windows with PowerShell, Python 3.12 or newer, Node.js LTS with npm, and Docker Desktop.
- An organization-issued RS256 access token and its matching public key, issuer, and audience.
- An OpenAI API key for report analysis, question answering, and embeddings.

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
  quay.io/minio/minio server /data --console-address ":9001"
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

Set these values in `backend\.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://financial:localdevpassword@localhost:5432/financial
JWT_ISSUER=<issuer from your identity provider>
JWT_AUDIENCE=<audience configured for this application>
JWT_PUBLIC_KEY=<matching RS256 public key>
OPENAI_API_KEY=<your OpenAI API key>
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET=financial-reports
S3_ACCESS_KEY_ID=localminio
S3_SECRET_ACCESS_KEY=localminio123
```

Keep the other example values unless your organization uses different model settings. Replace every `<...>` value with the real value from your organization/provider. The token's public key, issuer, and audience must match; do not paste a private signing key into this file. Never commit `backend\.env`.

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

### 6. Connect and use the workspace

On the website's connection screen, paste a valid organization-issued RS256 access token and connect. The token must:

- Have a UUID value in its `sub` claim.
- Include `roles` as a list containing `analyst`, `approver`, or both, as permitted for that user.
- Be valid for the configured issuer and audience and not be expired.

The app does not include a local login page or a test-token generator. Ask your identity-provider administrator for a development token and the matching issuer, audience, and public key. Without them, the services can start, but authenticated screens and API actions will not work. Report analysis also requires a valid OpenAI API key.

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
