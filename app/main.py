from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.config import settings
from app.api.session_router import router as session_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print("FastAPI Computer Use Backend starting...")
    yield
    print("FastAPI Computer Use Backend shutting down...")

app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI backend for Claude Computer Use with session management and real-time streaming",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router, prefix=settings.API_V1_STR)

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
