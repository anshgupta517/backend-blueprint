from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Sequence

T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Standard query parameters for any paginated endpoint.
    FastAPI reads these directly from the URL:
    GET /users?page=2&page_size=20
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        """Convert page number to SQL offset."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PagedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response wrapper.
    Every list endpoint returns this shape — no exceptions.

    Generic[T] means PagedResponse[UserResponse] is valid,
    and the items field will be typed as list[UserResponse].
    """

    items: Sequence[T]
    total: int  # Total records in database (not just this page)
    page: int  # Current page number
    page_size: int  # Items per page
    pages: int  # Total number of pages

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        params: PaginationParams,
    ) -> "PagedResponse[T]":
        """
        Factory method — builds the response from items + total + params.
        Usage:
            return PagedResponse.create(users, total_count, pagination)
        """
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=max(1, -(-total // params.page_size)),  # Ceiling division
        )
