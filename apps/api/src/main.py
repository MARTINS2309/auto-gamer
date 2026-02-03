from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import os
import traceback
import sys

from .routers import runs, roms, ws, emulators, config, thumbnails, metadata, play
from .services.run_manager import manager as run_manager

app = FastAPI(title="Retro Runner", version="0.1.0")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\n[DEBUG] ========================================================")
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
    except:
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
app.include_router(thumbnails.router, prefix="/api", tags=["thumbnails"])
app.include_router(metadata.router, prefix="/api", tags=["metadata"])
app.include_router(play.router, prefix="/api", tags=["play"])
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
