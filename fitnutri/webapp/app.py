from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import ALLOWED_ORIGINS, APP_VERSION, SESSION_SECRET
from .routes_auth import router as auth_router
from .routes_cases import router as cases_router
from .routes_legacy import router as legacy_router
from .routes_processing import router as processing_router

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(
    title="FitNutri Web API",
    version=APP_VERSION,
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/api/docs",
    redoc_url=None,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="fitnutri_session",
    max_age=8 * 60 * 60,
    same_site="strict",
    https_only=os.getenv("ENVIRONMENT", "production") == "production",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; img-src 'self' data:; frame-src 'self'; "
        "object-src 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(processing_router)
app.include_router(legacy_router)
