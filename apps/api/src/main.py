from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import os

from .routers import runs, roms, ws, emulators, config
from .services.run_manager import manager as run_manager

app = FastAPI(title="Retro Runner", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"], # Allow * for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
app.mount("/files", StaticFiles(directory=DATA_DIR), name="files")

# Routers
app.include_router(runs.router, prefix="/api", tags=["runs"])
app.include_router(roms.router, prefix="/api", tags=["roms"])
app.include_router(emulators.router, prefix="/api", tags=["emulators"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(ws.router, tags=["ws"])

@app.on_event("startup")
async def startup_event():
    # Pass the running loop to run_manager so threads can schedule coroutines
    loop = asyncio.get_running_loop()
    run_manager.set_loop(loop)

@app.on_event("shutdown")
async def shutdown_event():
    # Cleanup active runs?
    pass

@app.get("/")
async def root():
    return {"message": "Retro Runner API"}
