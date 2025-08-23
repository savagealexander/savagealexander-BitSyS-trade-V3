from __future__ import annotations

from typing import Any


def Field(default: Any = None, **kwargs: Any) -> Any:  # validation ignored
    return default


class BaseModel:
    def __init__(self, **data: Any) -> None:
        for name in self.__annotations__:
            setattr(self, name, data.get(name))

    def model_dump(self) -> dict:
        return {
            name: getattr(self, name)
            for name in self.__annotations__
            if hasattr(self, name)
        }
