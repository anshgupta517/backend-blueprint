from pydantic import BaseModel, Field

from app.models.post import Visibility


class PostCreate(BaseModel):
    title: str
    content: str = Field(min_length=10)
    author: str
    visibility: Visibility = Visibility.PUBLIC


class PostUpdate(BaseModel):
    id: int
    title: str
    content: str
    visibility: Visibility = Visibility.PUBLIC


class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    is_published: bool
    visibility: Visibility = Visibility.PUBLIC
