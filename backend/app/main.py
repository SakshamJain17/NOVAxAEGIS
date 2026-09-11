"""
AEGIS — Adaptive Execution & Guidance Intelligence System

Application entry point.

Responsibilities
----------------
- FastAPI application lifecycle
- Runtime initialization
- Graceful shutdown
- REST API
- WebSocket event streaming
- Health/readiness endpoints
- Tool discovery
- Global exception handling
- Runtime diagnostics

Architecture
------------
Electron
   ↓
React / Vite
   ↓
FastAPI
   ↓
AegisRuntime
   ├── Task Supervisor
   ├── Agent
   ├── Planner
   ├── Safety Engine
   ├── Action Gate
   ├── Tool Executor
   ├── Result Validator
   ├── Approval Manager
   └── WebSocket Manager
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.runtime.container import AegisRuntime, create_runtime
from app.api.websocket import websocket_endpoint


# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL = os.getenv("AEGIS_LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "AEGIS | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("aegis")


# ============================================================
# GLOBAL RUNTIME
# ============================================================

runtime: AegisRuntime | None = None


# ============================================================
# APPLICATION LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Own the complete lifecycle of the AEGIS runtime.

    Startup:
        Create runtime once.

    Shutdown:
        Capture the runtime locally.
        Detach the global reference.
        Shut down subsystems independently.

    This prevents one cleanup failure from causing the
    lifespan generator to fail during application shutdown.
    """

    global runtime

    logger.info("Initializing AEGIS runtime...")

    started_at = time.perf_counter()

    try:
        runtime = create_runtime()

        elapsed = (time.perf_counter() - started_at) * 1000

        logger.info(
            "AEGIS runtime initialized in %.2f ms",
            elapsed,
        )

        yield

    except Exception:
        logger.exception(
            "Fatal error during AEGIS application lifecycle."
        )
        raise

    finally:
        logger.info("Beginning AEGIS shutdown...")

        # ----------------------------------------------------
        # Detach global runtime FIRST.
        #
        # This prevents new requests from using a runtime
        # while shutdown is already underway.
        # ----------------------------------------------------

        current_runtime = runtime
        runtime = None

        if current_runtime is None:
            logger.info("No runtime to shut down.")
            return

        # ----------------------------------------------------
        # APPROVAL MANAGER
        # ----------------------------------------------------

        try:
            logger.info("Clearing pending approvals...")

            await current_runtime.approval_manager.clear()

            logger.info("Approval manager shutdown complete.")

        except Exception:
            logger.exception(
                "Approval manager shutdown failed."
            )

        # ----------------------------------------------------
        # WEBSOCKET MANAGER
        # ----------------------------------------------------

        try:
            logger.info("Shutting down WebSocket manager...")

            await current_runtime.websocket_manager.shutdown()

            logger.info(
                "WebSocket manager shutdown complete."
            )

        except Exception:
            logger.exception(
                "WebSocket manager shutdown failed."
            )

        # ----------------------------------------------------
        # FINAL
        # ----------------------------------------------------

        logger.info("AEGIS shutdown complete.")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AEGIS",
    description=(
        "Adaptive Execution & Guidance Intelligence System"
    ),
    version=settings.version,
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST TIMING MIDDLEWARE
# ============================================================

@app.middleware("http")
async def request_timing_middleware(
    request: Request,
    call_next,
):
    """
    Lightweight request observability.

    Records request duration without interfering with
    application behavior.
    """

    started = time.perf_counter()

    try:
        response = await call_next(request)

        elapsed = (
            time.perf_counter() - started
        ) * 1000

        response.headers[
            "X-AEGIS-Latency-ms"
        ] = f"{elapsed:.2f}"

        logger.debug(
            "%s %s → %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )

        return response

    except Exception:
        elapsed = (
            time.perf_counter() - started
        ) * 1000

        logger.exception(
            "%s %s failed after %.2f ms",
            request.method,
            request.url.path,
            elapsed,
        )

        raise


# ============================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    """
    Prevent raw internal exceptions from leaking to clients.

    Full exception remains available in server logs.
    """

    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": (
                "AEGIS encountered an internal error."
            ),
        },
    )


# ============================================================
# RUNTIME ACCESS
# ============================================================

def get_runtime() -> AegisRuntime:
    """
    Return the active AEGIS runtime.

    Raises:
        HTTPException:
            When the application has not completed startup.
    """

    if runtime is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "runtime_unavailable",
                "message": (
                    "AEGIS runtime is not available."
                ),
            },
        )

    return runtime


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root() -> dict[str, Any]:
    """
    Basic service information.
    """

    return {
        "service": "AEGIS",
        "codename": (
            "Adaptive Execution & Guidance "
            "Intelligence System"
        ),
        "version": settings.version,
        "status": (
            "operational"
            if runtime is not None
            else "starting"
        ),
        "architecture": {
            "reasoning": "bounded",
            "execution": "policy-gated",
            "validation": "enabled",
            "recovery": "enabled",
            "realtime": (
                "enabled"
                if runtime is not None
                else "initializing"
            ),
            "voice": "initializing",
        },
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health() -> dict[str, Any]:
    """
    Liveness endpoint.

    Used by Electron to determine whether the Python
    backend is alive.
    """

    return {
        "status": "ok",
        "service": "AEGIS",
        "version": settings.version,
    }


# ============================================================
# READINESS
# ============================================================

@app.get("/ready")
async def readiness() -> dict[str, Any]:
    """
    Readiness endpoint.

    Unlike /health, this confirms that the AEGIS runtime
    has actually been initialized.
    """

    if runtime is None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "runtime": False,
            },
        )

    return {
        "status": "ready",
        "runtime": True,
        "service": "AEGIS",
        "version": settings.version,
    }


# ============================================================
# RUNTIME STATUS
# ============================================================

@app.get("/api/runtime")
async def runtime_status() -> dict[str, Any]:
    """
    Runtime diagnostics for the frontend command center.
    """

    active_runtime = get_runtime()

    return {
        "service": "AEGIS",
        "version": settings.version,
        "environment": settings.environment,
        "runtime": "online",
        "model": {
            "provider": settings.model_provider,
            "name": settings.model_name,
        },
        "subsystems": {
            "task_supervisor": "online",
            "safety_engine": "online",
            "approval_manager": "online",
            "tool_executor": "online",
            "result_validator": "online",
            "websocket": "online",
            "voice": "initializing",
            "memory": "initializing",
        },
        "active_tasks": len(
            active_runtime.task_supervisor.active_tasks()
        ),
    }


# ============================================================
# TOOLS
# ============================================================

@app.get("/api/tools")
async def tools() -> dict[str, Any]:
    """
    Return tools currently registered with AEGIS.
    """

    active_runtime = get_runtime()

    registry = active_runtime.tool_registry

    try:
        descriptions = registry.descriptions()
    except AttributeError:
        descriptions = {}

    try:
        names = registry.names()
    except AttributeError:
        names = list(descriptions.keys())

    return {
        "count": len(names),
        "tools": descriptions,
    }


# ============================================================
# WEBSOCKET
# ============================================================

@app.websocket("/ws")
async def websocket_route(
    websocket: WebSocket,
):
    """
    Real-time AEGIS event stream.

    Frontend connects here to receive:

        task events
        state transitions
        tool events
        safety decisions
        approvals
        validation
        interruption
        recovery
        speech events
    """

    if runtime is None:
        await websocket.close(
            code=1011,
            reason="AEGIS runtime unavailable",
        )
        return

    await websocket_endpoint(
        websocket,
        runtime.websocket_manager,
    )


# ============================================================
# DEVELOPMENT DIAGNOSTICS
# ============================================================

@app.get("/api/diagnostics")
async def diagnostics() -> dict[str, Any]:
    """
    Development diagnostics.

    Useful for the desktop command center and debugging.
    """

    active_runtime = get_runtime()

    active_tasks = (
        active_runtime
        .task_supervisor
        .active_tasks()
    )

    pending_approvals = []

    try:
        pending_approvals = (
            await active_runtime
            .approval_manager
            .pending()
        )
    except Exception:
        logger.exception(
            "Failed to retrieve pending approvals."
        )

    return {
        "service": "AEGIS",
        "status": "operational",
        "runtime": True,
        "tasks": {
            "active": len(active_tasks),
        },
        "approvals": {
            "pending": len(pending_approvals),
        },
        "configuration": {
            "environment": settings.environment,
            "model_provider": settings.model_provider,
            "model_name": settings.model_name,
        },
    }


# ============================================================
# APPLICATION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=LOG_LEVEL.lower(),
    )