import asyncio
import logging
import os
import subprocess
import sys
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .routers import (
    agents,
    config,
    emulators,
    filesystem,
    integration,
    metadata,
    play,
    roms,
    runs,
    thumbnails,
    ws,
)
from .services.play_manager import play_manager
from .services.run_manager import manager as run_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


app = FastAPI(title="Retro Runner", version="0.1.0")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    print("\n[DEBUG] ========================================================")
    print(f"[DEBUG] Request: {request.method} {request.url}")
    # print(f"[DEBUG] Headers: {dict(request.headers)}") # Uncomment for full headers

    try:
        response = await call_next(request)
        print(f"[DEBUG] Response status: {response.status_code}")
        return response
    except Exception as e:
        print(f"[DEBUG] Middleware caught exception: {e}")
        raise e


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"[ERROR] Validation error for {request.method} {request.url}")
    print(f"[ERROR] Details: {exc.errors()}")
    try:
        body = await request.body()
        print(f"[ERROR] Body: {body.decode('utf-8')}")
    except Exception:
        pass

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "Validation Error"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] Unhandled exception for {request.method} {request.url}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],  # Allow * for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
app.mount("/files", StaticFiles(directory=DATA_DIR), name="files")

# Routers
app.include_router(agents.router, prefix="/api", tags=["agents"])
app.include_router(runs.router, prefix="/api", tags=["runs"])
app.include_router(roms.router, prefix="/api", tags=["roms"])
app.include_router(emulators.router, prefix="/api", tags=["emulators"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(thumbnails.router, prefix="/api", tags=["thumbnails"])
app.include_router(metadata.router, prefix="/api", tags=["metadata"])
app.include_router(play.router, prefix="/api", tags=["play"])
app.include_router(filesystem.router, prefix="/api", tags=["filesystem"])
app.include_router(integration.router, prefix="/api", tags=["integration"])
app.include_router(ws.router, tags=["ws"])


async def generate_frontend_types():
    """Generate TypeScript types from OpenAPI spec for frontend."""
    await asyncio.sleep(0.5)  # Wait for server to be fully ready

    # Find the web directory relative to api
    # __file__ = apps/api/src/main.py
    # apps_dir = apps/
    apps_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    web_dir = os.path.join(apps_dir, "web")

    if not os.path.exists(web_dir):
        logger.warning(f"[TypeGen] Web directory not found: {web_dir}")
        return

    try:
        result = subprocess.run(
            ["pnpm", "generate-types"],
            cwd=web_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("[TypeGen] Frontend types regenerated successfully")
        else:
            logger.warning(f"[TypeGen] Type generation failed: {result.stderr}")
    except FileNotFoundError:
        logger.warning("[TypeGen] pnpm not found, skipping type generation")
    except subprocess.TimeoutExpired:
        logger.warning("[TypeGen] Type generation timed out")
    except Exception as e:
        logger.warning(f"[TypeGen] Type generation error: {e}")


@app.on_event("startup")
async def startup_event():
    # Pass the running loop to managers so threads can schedule coroutines
    loop = asyncio.get_running_loop()
    run_manager.set_loop(loop)
    play_manager.set_loop(loop)

    # Kill orphaned training processes from previous server session
    await asyncio.to_thread(run_manager.cleanup_orphans)

    # Generate frontend types only in dev mode (when --reload is active)
    if os.environ.get("UVICORN_RELOAD"):
        asyncio.create_task(generate_frontend_types())


@app.on_event("shutdown")
async def shutdown_event():
    await asyncio.to_thread(run_manager.cleanup_all)


@app.get("/")
def root():
    return {"message": "Retro Runner API"}
