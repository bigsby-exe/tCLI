"""Output formatting for tCLI."""

import json
from datetime import datetime
from typing import Optional, Union

from rich.console import Console
from rich.table import Table
from rich.text import Text

from tcli.models import TodoRead

console = Console()


def format_datetime(dt: Optional[Union[str, datetime]]) -> str:
    """Format datetime string or datetime object for display."""
    if not dt:
        return "—"
    
    # If it's already a datetime object, format it directly
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    
    # Otherwise, parse the string
    try:
        dt_str = str(dt)
        dt_obj = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt_obj.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt)


def format_priority(priority: Optional[int]) -> Text:
    """Format priority with color coding."""
    if priority is None:
        return Text("—", style="dim")
    if priority <= 2:
        return Text(str(priority), style="bold red")
    elif priority == 3:
        return Text(str(priority), style="yellow")
    else:
        return Text(str(priority), style="green")


def format_status(status: Optional[str]) -> Text:
    """Format status with color coding."""
    if not status:
        return Text("—", style="dim")
    status_lower = status.lower()
    if status_lower == "done":
        return Text(status, style="bold green")
    elif status_lower == "in_progress":
        return Text(status, style="bold yellow")
    else:
        return Text(status, style="cyan")


def format_tags(tags: Optional[list[str]]) -> str:
    """Format tags list."""
    if not tags:
        return "—"
    return ", ".join(tags)


def print_todo_table(todos: list[TodoRead]) -> None:
    """Print todos in a table format."""
    table = Table(title="Todos", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=36)
    table.add_column("Title", style="bold", width=30)
    table.add_column("Status", width=12)
    table.add_column("Priority", width=8, justify="center")
    table.add_column("Due Date", width=16)
    table.add_column("Tags", width=20)

    for todo in todos:
        # Extract status if it exists in the model (it might be in the response but not in schema)
        status = getattr(todo, "status", None)
        table.add_row(
            str(todo.id),
            todo.title[:30] + "..." if len(todo.title) > 30 else todo.title,
            format_status(status),
            format_priority(todo.priority),
            format_datetime(todo.due_at),
            format_tags(todo.tags),
        )

    console.print(table)


def print_todo_detail(todo: TodoRead) -> None:
    """Print a single todo in detailed format."""
    status = getattr(todo, "status", None)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan", width=20)
    table.add_column("Value", width=60)

    table.add_row("ID", str(todo.id))
    table.add_row("Title", todo.title)
    if todo.description:
        table.add_row("Description", todo.description)
    table.add_row("Status", format_status(status))
    table.add_row("Priority", format_priority(todo.priority))
    if todo.due_at:
        table.add_row("Due Date", format_datetime(todo.due_at))
    if todo.estimated_minutes:
        table.add_row("Estimated Minutes", str(todo.estimated_minutes))
    if todo.tags:
        table.add_row("Tags", format_tags(todo.tags))
    table.add_row("Created At", format_datetime(todo.created_at))
    if todo.updated_at:
        table.add_row("Updated At", format_datetime(todo.updated_at))

    console.print(table)


def print_json(data: list[TodoRead] | TodoRead | dict) -> None:
    """Print data as JSON."""
    if isinstance(data, list):
        json_data = [item.model_dump(mode="json") for item in data]
    elif isinstance(data, TodoRead):
        json_data = data.model_dump(mode="json")
    else:
        json_data = data

    print(json.dumps(json_data, indent=2, default=str))

