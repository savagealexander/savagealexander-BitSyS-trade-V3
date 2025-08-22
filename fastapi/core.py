from __future__ import annotations

import asyncio
from typing import Any, Callable, List


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def Depends(func: Callable | None = None) -> Callable | None:
    return func


def Header(default: Any = None) -> Any:
    return default


class APIRouter:
    def __init__(self, prefix: str = "", tags: List[str] | None = None) -> None:
        self.prefix = prefix
        self.routes: List[tuple[str, str, Callable]] = []

    def add_api_route(self, path: str, func: Callable, methods: List[str]) -> None:
        self.routes.append((methods[0].upper(), self.prefix + path, func))

    def get(self, path: str, response_model: Any = None) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_api_route(path, func, ["GET"])
            return func

        return decorator

    def post(self, path: str, response_model: Any = None) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_api_route(path, func, ["POST"])
            return func

        return decorator

    def delete(self, path: str, response_model: Any = None) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_api_route(path, func, ["DELETE"])
            return func

        return decorator

    def put(self, path: str, response_model: Any = None) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_api_route(path, func, ["PUT"])
            return func

        return decorator

    def include_router(self, router: "APIRouter", prefix: str = "") -> None:
        for method, path, func in router.routes:
            self.routes.append((method, prefix + path, func))


class FastAPI(APIRouter):
    def __init__(self) -> None:
        super().__init__(prefix="")
        self.event_handlers: dict[str, list[Callable]] = {"startup": []}

    def add_event_handler(self, event: str, func: Callable) -> None:
        self.event_handlers.setdefault(event, []).append(func)

    def include_router(
        self, router: APIRouter, prefix: str = "", dependencies: List[Callable] | None = None
    ) -> None:
        super().include_router(router, prefix)
