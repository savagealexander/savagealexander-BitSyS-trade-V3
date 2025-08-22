"""Application entrypoint."""

from fastapi import FastAPI

from .api import router as api_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
