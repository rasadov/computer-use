import logging
import uuid
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles


from backend.core.config import settings
from backend.core.logger import setup_logging
from backend.database.connection import engine, SessionLocal
from backend.services.connection_manager import connection_manager
from backend.router.session_router import router as session_router
from backend.router.health_router import router as health_router


setup_logging(log_path="logs/app.log", max_log_files=5, max_log_size=10_000_000)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
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

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Add request tracking and structured logging"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    extra = {
        "custom_attrs": {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else None
        }
    }
    
    logger.info("Request started", extra=extra)
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    extra.get("custom_attrs", {}).update({
        "status_code": response.status_code,
        "duration_ms": round(duration * 1000, 2)
    })
    
    logger.info("Request completed", extra=extra)
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(session_router, prefix=settings.API_V1_STR)

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
