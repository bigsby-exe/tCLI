"""API client for interacting with the Todo API."""

from typing import Optional
from uuid import UUID

import httpx

from tcli.models import TodoCreate, TodoRead, TodoUpdate


class APIError(Exception):
    """Base exception for API errors."""

    pass


class APIClient:
    """Client for interacting with the Todo API."""

    def __init__(self, base_url: str, api_key: str):
        """Initialize the API client."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key},
            timeout=30.0,
        )

    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 401:
            raise APIError("Unauthorized - Missing or invalid API key")
        elif response.status_code == 403:
            raise APIError("Forbidden - Invalid API key")
        elif response.status_code == 404:
            raise APIError("Not found")
        elif response.status_code == 422:
            error_detail = response.json().get("detail", [])
            error_messages = [
                f"{err.get('loc', [])}: {err.get('msg', '')}" for err in error_detail
            ]
            raise APIError(f"Validation Error: {'; '.join(error_messages)}")
        elif not response.is_success:
            raise APIError(f"API error: {response.status_code} - {response.text}")

        if response.status_code == 204:  # No content
            return {}

        return response.json()

    def create_todo(self, todo: TodoCreate) -> TodoRead:
        """Create a new todo item."""
        response = self.client.post("/todos/", json=todo.model_dump(exclude_none=True))
        data = self._handle_response(response)
        return TodoRead(**data)

    def list_todos(
        self,
        q: Optional[str] = None,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[TodoRead]:
        """List todos with optional filtering."""
        params = {}
        if q is not None:
            params["q"] = q
        if tag is not None:
            params["tag"] = tag
        if status is not None:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit

        response = self.client.get("/todos/", params=params)
        data = self._handle_response(response)
        return [TodoRead(**item) for item in data]

    def get_todo(self, item_id: UUID) -> TodoRead:
        """Get a todo by ID."""
        response = self.client.get(f"/todos/{item_id}")
        data = self._handle_response(response)
        return TodoRead(**data)

    def update_todo(self, item_id: UUID, todo: TodoUpdate) -> TodoRead:
        """Update a todo item."""
        response = self.client.patch(
            f"/todos/{item_id}", json=todo.model_dump(exclude_none=True)
        )
        data = self._handle_response(response)
        return TodoRead(**data)

    def delete_todo(self, item_id: UUID) -> None:
        """Delete a todo item."""
        response = self.client.delete(f"/todos/{item_id}")
        self._handle_response(response)

    def health_check(self) -> dict:
        """Check API health status."""
        response = self.client.get("/health")
        return self._handle_response(response)

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

