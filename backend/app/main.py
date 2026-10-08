import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from app.api.approvals import router as approvals_router
from app.api.knowledge import router as knowledge_router
from app.api.questions import router as questions_router
from app.api.reports import router as reports_router
from app.core.config import get_settings
from app.workflows.worker import recover_interrupted_jobs, worker_loop


@asynccontextmanager
async def lifespan(application: FastAPI):
    recover_interrupted_jobs()
    worker = asyncio.create_task(worker_loop())
    application.state.analysis_worker = worker
    try:
        yield
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Financial Document Analysis",
    version="1.0.0",
    description="Cited financial-report analysis with persisted human approval workflows.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(reports_router, prefix="/api/v1")
app.include_router(questions_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")


@app.exception_handler(StarletteHTTPException)
async def http_problem(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=exc.status_code,
        media_type="application/problem+json",
        content={
            "title": "Request could not be completed",
            "status": exc.status_code,
            "detail": exc.detail,
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_problem(request: Request, exc: RequestValidationError) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=422,
        media_type="application/problem+json",
        content={
            "title": "Request validation failed",
            "status": 422,
            "detail": jsonable_encoder(exc.errors()),
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
