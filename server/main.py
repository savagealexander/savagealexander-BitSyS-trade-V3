# server/main.py
from __future__ import annotations
from .balances import balance_service
import logging
import sys
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.cors import CORSMiddleware

# -----------------------------------------------------------------------------
# Logging: wire our app loggers to Uvicorn's console so INFO/DEBUG are visible.
# -----------------------------------------------------------------------------
def _setup_app_logging() -> None:
    """
    Make sure all `server.*` loggers print to the same console as uvicorn,
    and at DEBUG level. If uvicorn handlers are not ready yet, attach a
    temporary StreamHandler to root so logs still show up.
    """
    root = logging.getLogger()
    if root.level > logging.DEBUG:
        root.setLevel(logging.DEBUG)

    uvicorn_err = logging.getLogger("uvicorn.error")
    uv_handlers = list(uvicorn_err.handlers)

    # If uvicorn hasn't installed handlers yet and root has none, attach one.
    if not uv_handlers and not root.handlers:
        h = logging.StreamHandler(stream=sys.stdout)
        h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        root.addHandler(h)

    # Turn on DEBUG + connect to uvicorn handlers (or bubble to root as fallback)
    for name in (
        "server",
        "server.api",
        "server.leader_watcher",
        "server.connectors",
        "server.connectors.binance_sdk_connector",
        "server.balances",
        "server.copy_dispatcher",
        "server.accounts",
    ):
        lg = logging.getLogger(name)
        lg.setLevel(logging.DEBUG)
        if uv_handlers:
            lg.handlers = uv_handlers
            lg.propagate = False
        else:
            lg.propagate = True


_setup_app_logging()

# -----------------------------------------------------------------------------
# Import routers AFTER logging is configured so their module loggers are wired.
# -----------------------------------------------------------------------------
from .api import public_router, protected_router, verify_token  # noqa: E402

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(
    title="BitSyS Copy Trading API",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (adjust origins as you need)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # or specify front-end origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(public_router, prefix="/api")
app.include_router(protected_router, prefix="/api", dependencies=[Depends(verify_token)])

# -----------------------------------------------------------------------------
# Root & health
# -----------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    # Quick jump to Swagger UI
    return RedirectResponse(url="/docs")

@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}

# -----------------------------------------------------------------------------
# Exception handlers (make errors easy to see while debugging)
# -----------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("server").exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": str(exc)})

# -----------------------------------------------------------------------------
# Lifespan logs (optional)
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    logging.getLogger("server").info("🚀 Application startup complete")
    await balance_service.start()  # 启动并立即拉取一次余额，然后进入轮询

@app.on_event("shutdown")
async def on_shutdown() -> None:
    logging.getLogger("server").info("🛑 Application shutdown")

# -----------------------------------------------------------------------------
# Local runner (optional)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")
