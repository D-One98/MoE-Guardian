from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router as api_router
from contextlib import asynccontextmanager
from app.core.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Pre-publication brand-governance platform powered by VERITY MoE. "
        "Provides deterministic RuleGuard validation, baseline ClaimGuard evidence matching, "
        "canonical document block anchoring, fail-closed rewrite revalidation, and HMAC-signed audit snapshots."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)