"""Application entrypoint."""

from fastapi import FastAPI

from .api import router as api_router
from .balances import balance_service


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    app.add_event_handler("startup", balance_service.start)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
