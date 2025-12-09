"""Pydantic models matching the OpenAPI schema."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TodoCreate(BaseModel):
    """Schema for creating a new todo item."""

    title: str = Field(..., description="The title of the todo item")
    description: Optional[str] = Field(None, description="Detailed description of the todo")
    due_at: Optional[datetime] = Field(None, description="Due date and time for the todo")
    estimated_minutes: Optional[int] = Field(
        None, ge=0, description="Estimated time to complete in minutes"
    )
    priority: int = Field(
        default=3, ge=1, le=5, description="Priority level (1=highest, 5=lowest)"
    )
    tags: Optional[list[str]] = Field(None, description="List of tags for categorizing the todo")


class TodoUpdate(BaseModel):
    """Schema for updating a todo item. All fields are optional."""

    title: Optional[str] = Field(None, description="The title of the todo item")
    description: Optional[str] = Field(None, description="Detailed description of the todo")
    due_at: Optional[datetime] = Field(None, description="Due date and time for the todo")
    estimated_minutes: Optional[int] = Field(
        None, ge=0, description="Estimated time to complete in minutes"
    )
    status: Optional[str] = Field(None, description="Status of the todo (e.g., 'todo', 'in_progress', 'done')")
    priority: Optional[int] = Field(
        None, ge=1, le=5, description="Priority level (1=highest, 5=lowest)"
    )
    tags: Optional[list[str]] = Field(None, description="List of tags for categorizing the todo")


class TodoRead(BaseModel):
    """Schema for reading a todo item with all fields including metadata."""

    id: UUID = Field(..., description="Unique identifier for the todo item")
    title: str = Field(..., description="The title of the todo item")
    description: Optional[str] = Field(None, description="Detailed description of the todo")
    due_at: Optional[datetime] = Field(None, description="Due date and time for the todo")
    estimated_minutes: Optional[int] = Field(
        None, ge=0, description="Estimated time to complete in minutes"
    )
    priority: int = Field(
        default=3, ge=1, le=5, description="Priority level (1=highest, 5=lowest)"
    )
    tags: Optional[list[str]] = Field(None, description="List of tags for categorizing the todo")
    created_at: datetime = Field(..., description="Timestamp when the todo was created")
    updated_at: Optional[datetime] = Field(None, description="Timestamp when the todo was last updated")

