from fastapi import FastAPI
from app.config import settings
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


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
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}
    