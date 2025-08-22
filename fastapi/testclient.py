from __future__ import annotations

import asyncio
import inspect
from typing import Any, Dict

from .core import HTTPException


class Response:
    def __init__(self, status_code: int, data: Any) -> None:
        self.status_code = status_code
        self._data = data

    def json(self) -> Any:
        return self._data


class TestClient:
    def __init__(self, app) -> None:
        self.app = app
        for func in app.event_handlers.get("startup", []):
            if inspect.iscoroutinefunction(func):
                asyncio.run(func())
            else:
                func()

    def _match(self, template: str, path: str) -> tuple[bool, Dict[str, str]]:
        if "{" not in template:
            return template == path, {}
        prefix, rest = template.split("{", 1)
        name, suffix = rest.split("}", 1)
        if not path.startswith(prefix) or not path.endswith(suffix):
            return False, {}
        value = path[len(prefix) : len(path) - len(suffix)]
        return True, {name: value}

    def _find_route(self, method: str, path: str):
        for m, template, func in self.app.routes:
            if m != method:
                continue
            match, params = self._match(template, path)
            if match:
                return func, params
        raise KeyError(f"route {method} {path} not found")

    def _build_kwargs(self, func, params: Dict[str, str], json: Any | None):
        sig = inspect.signature(func)
        kwargs = {}
        for name, param in sig.parameters.items():
            if name in params:
                kwargs[name] = params[name]
            elif json is not None:
                ann = param.annotation
                if isinstance(ann, str):
                    ann = eval(ann, func.__globals__)
                if ann is inspect._empty:
                    kwargs[name] = json
                else:
                    kwargs[name] = ann(**json)
            elif param.default is not inspect._empty:
                kwargs[name] = param.default
        return kwargs

    def request(self, method: str, path: str, json: Any | None = None) -> Response:
        try:
            func, params = self._find_route(method.upper(), path)
            kwargs = self._build_kwargs(func, params, json)
            if inspect.iscoroutinefunction(func):
                data = asyncio.run(func(**kwargs))
            else:
                data = func(**kwargs)
            return Response(200, data)
        except HTTPException as exc:
            return Response(exc.status_code, {"detail": exc.detail})

    def post(self, path: str, json: Any | None = None) -> Response:
        return self.request("POST", path, json)

    def delete(self, path: str, json: Any | None = None) -> Response:
        return self.request("DELETE", path, json)

    def get(self, path: str, json: Any | None = None) -> Response:
        return self.request("GET", path, json)

    def put(self, path: str, json: Any | None = None) -> Response:
        return self.request("PUT", path, json)
