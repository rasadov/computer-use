from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles


from backend.config import settings
from backend.database import engine, SessionLocal
from backend.router.session_router import router as session_router
from backend.services.connection_manager import connection_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Create engine ONCE
    app.state.engine = engine
    app.state.async_session = SessionLocal
    app.state.connection_manager = connection_manager
    yield
    await app.state.engine.dispose()
    await app.state.connection_manager.disconnect()

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
