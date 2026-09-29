from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import accounts, auth
from app.core.config import settings
from app.core.exceptions import BankError
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Basic Banking API",
    description="A beginner-friendly banking API with JWT authentication and transaction history.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BankError)
async def bank_error_handler(_request: Request, error: BankError):
    return JSONResponse(status_code=error.status_code, content={"detail": error.detail})


@app.exception_handler(Exception)
async def internal_error_handler(_request: Request, _error: Exception):
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred"})


app.include_router(auth.router)
app.include_router(accounts.router)