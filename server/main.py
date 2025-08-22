"""Application entrypoint."""

from fastapi import Depends, FastAPI

from .api import public_router, protected_router, verify_token
from .balances import balance_service


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI()
    app.include_router(public_router, prefix="/api")
    app.include_router(
        protected_router, prefix="/api", dependencies=[Depends(verify_token)]
    )
    app.add_event_handler("startup", balance_service.start)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
