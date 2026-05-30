"""Shared Pydantic base models.

API models serialize to camelCase (friendly for the TypeScript dashboard) while
still accepting snake_case input — `populate_by_name=True`.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ORMModel(APIModel):
    """Read model populated directly from ORM objects."""


class Page[T](APIModel):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size
