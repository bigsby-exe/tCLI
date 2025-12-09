"""Main CLI entry point for tCLI."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console

from tcli.api import APIError, APIClient
from tcli.config import Config
from tcli.models import TodoCreate, TodoUpdate
from tcli.output import print_json, print_todo_detail, print_todo_table

app = typer.Typer(help="CLI tool for managing todos via the Todo API")
console = Console()

# Known commands that should not be treated as todo titles
KNOWN_COMMANDS = {"list", "update", "delete", "get", "add", "edit", "done"}


def get_client(config_path: Optional[Path] = None) -> APIClient:
    """Get an API client instance."""
    try:
        config = Config(config_path)
        return APIClient(config.base_url, config.api_key)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def _create_todo(
    title: str,
    description: Optional[str] = None,
    due_at: Optional[str] = None,
    priority: Optional[int] = None,
    tags: Optional[str] = None,
    estimated_minutes: Optional[int] = None,
    work: bool = False,
    json_output: bool = False,
    config_path: Optional[Path] = None,
):
    """Internal function to create a todo."""
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
    
    # Add 'work' tag if --work flag is present
    if work:
        if 'work' not in tag_list:
            tag_list.append('work')
    
    # Set tag_list to None if empty (to match API expectations)
    tag_list = tag_list if tag_list else None

    # Parse due_at
    due_at_dt = None
    if due_at:
        try:
            due_at_dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid date format. Use ISO format (e.g., 2024-12-31T23:59:59)")
            sys.exit(1)

    # Build TodoCreate, always include priority (default to 3 if not provided)
    todo_data = {
        "title": title,
        "description": description,
        "due_at": due_at_dt,
        "tags": tag_list,
        "estimated_minutes": estimated_minutes,
        "priority": priority if priority is not None else 3,
    }
    
    todo_create = TodoCreate(**todo_data)

    try:
        with get_client(config_path) as client:
            todo = client.create_todo(todo_create)
            if json_output:
                print_json(todo)
            else:
                console.print("[green]✓[/green] Todo created successfully!")
                print_todo_detail(todo)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@app.command()
def add(
    title: str = typer.Argument(..., help="Todo title"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description of the todo"),
    due_at: Optional[str] = typer.Option(None, "--due-at", help="Due date and time (ISO format)"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Priority (1=highest, 5=lowest, default=3)"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags"),
    estimated_minutes: Optional[int] = typer.Option(None, "--estimated-minutes", "-e", help="Estimated minutes"),
    work: bool = typer.Option(False, "--work", help="Add 'work' tag to the todo"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """Add a new todo item. Default priority is 3 and default status is 'todo'."""
    _create_todo(
        title=title,
        description=description,
        due_at=due_at,
        priority=priority,
        tags=tags,
        estimated_minutes=estimated_minutes,
        work=work,
        json_output=json_output,
        config_path=config_path,
    )


@app.command()
def list(
    q: Optional[str] = typer.Option(None, "--q", help="Search query to filter by title"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Maximum number of todos to return"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """List todos with optional filtering. By default excludes todos with status 'done'."""
    try:
        with get_client(config_path) as client:
            # If status is not explicitly provided, fetch all and filter out "done"
            if status is None:
                todos = client.list_todos(q=q, tag=tag, status=None, limit=limit)
                # Filter out todos with status "done"
                todos = [todo for todo in todos if getattr(todo, "status", "").lower() != "done"]
            else:
                todos = client.list_todos(q=q, tag=tag, status=status, limit=limit)
            
            if json_output:
                print_json(todos)
            else:
                if not todos:
                    console.print("[yellow]No todos found.[/yellow]")
                else:
                    print_todo_table(todos)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@app.command()
def get(
    item_id: str = typer.Argument(..., help="Todo ID (UUID)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """Get a todo by ID."""
    try:
        todo_id = UUID(item_id)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid UUID format: {item_id}")
        sys.exit(1)

    try:
        with get_client(config_path) as client:
            todo = client.get_todo(todo_id)
            if json_output:
                print_json(todo)
            else:
                print_todo_detail(todo)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@app.command()
def update(
    item_id: str = typer.Argument(..., help="Todo ID (UUID)"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Title of the todo"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description of the todo"),
    due_at: Optional[str] = typer.Option(None, "--due-at", help="Due date and time (ISO format)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Status (todo, in_progress, done)"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Priority (1=highest, 5=lowest)"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags"),
    estimated_minutes: Optional[int] = typer.Option(None, "--estimated-minutes", "-e", help="Estimated minutes"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """Update a todo item."""
    from datetime import datetime

    try:
        todo_id = UUID(item_id)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid UUID format: {item_id}")
        sys.exit(1)

    # Parse tags
    tag_list = None
    if tags is not None:
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else None

    # Parse due_at
    due_at_dt = None
    if due_at:
        try:
            due_at_dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid date format. Use ISO format (e.g., 2024-12-31T23:59:59)")
            sys.exit(1)

    todo_update = TodoUpdate(
        title=title,
        description=description,
        due_at=due_at_dt,
        status=status,
        priority=priority,
        tags=tag_list,
        estimated_minutes=estimated_minutes,
    )

    # Check if at least one field is provided
    if not any([title, description, due_at, status, priority, tags, estimated_minutes]):
        console.print("[yellow]Warning:[/yellow] No fields to update. Provide at least one field.")
        sys.exit(1)

    try:
        with get_client(config_path) as client:
            todo = client.update_todo(todo_id, todo_update)
            if json_output:
                print_json(todo)
            else:
                console.print("[green]✓[/green] Todo updated successfully!")
                print_todo_detail(todo)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@app.command()
def edit(
    item_id: str = typer.Argument(..., help="Todo ID (UUID)"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Title of the todo"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description of the todo"),
    due_at: Optional[str] = typer.Option(None, "--due-at", help="Due date and time (ISO format)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Status (todo, in_progress, done)"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Priority (1=highest, 5=lowest)"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags"),
    estimated_minutes: Optional[int] = typer.Option(None, "--estimated-minutes", "-e", help="Estimated minutes"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """Edit a todo item (alias for update)."""
    from datetime import datetime

    try:
        todo_id = UUID(item_id)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid UUID format: {item_id}")
        sys.exit(1)

    # Parse tags
    tag_list = None
    if tags is not None:
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else None

    # Parse due_at
    due_at_dt = None
    if due_at:
        try:
            due_at_dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid date format. Use ISO format (e.g., 2024-12-31T23:59:59)")
            sys.exit(1)

    todo_update = TodoUpdate(
        title=title,
        description=description,
        due_at=due_at_dt,
        status=status,
        priority=priority,
        tags=tag_list,
        estimated_minutes=estimated_minutes,
    )

    # Check if at least one field is provided
    if not any([title, description, due_at, status, priority, tags, estimated_minutes]):
        console.print("[yellow]Warning:[/yellow] No fields to update. Provide at least one field.")
        sys.exit(1)

    try:
        with get_client(config_path) as client:
            todo = client.update_todo(todo_id, todo_update)
            if json_output:
                print_json(todo)
            else:
                console.print("[green]✓[/green] Todo updated successfully!")
                print_todo_detail(todo)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@app.command()
def done(
    item_id: str = typer.Argument(..., help="Todo ID (UUID)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """Mark a todo as done."""
    try:
        todo_id = UUID(item_id)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid UUID format: {item_id}")
        sys.exit(1)

    todo_update = TodoUpdate(status="done")

    try:
        with get_client(config_path) as client:
            todo = client.update_todo(todo_id, todo_update)
            if json_output:
                print_json(todo)
            else:
                console.print("[green]✓[/green] Todo marked as done!")
                print_todo_detail(todo)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@app.command()
def delete(
    item_id: str = typer.Argument(..., help="Todo ID (UUID)"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """Delete a todo item."""
    try:
        todo_id = UUID(item_id)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid UUID format: {item_id}")
        sys.exit(1)

    try:
        with get_client(config_path) as client:
            client.delete_todo(todo_id)
            console.print("[green]✓[/green] Todo deleted successfully!")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)




def main():
    """Main entry point that routes to create, list, or other commands."""
    # Get arguments (skip script name)
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # If no arguments, list todos
    if not args:
        try:
            with get_client(None) as client:
                todos = client.list_todos(q=None, tag=None, status=None, limit=None)
                # Filter out todos with status "done"
                todos = [todo for todo in todos if getattr(todo, "status", "").lower() != "done"]
                
                if not todos:
                    console.print("[yellow]No todos found.[/yellow]")
                else:
                    print_todo_table(todos)
        except APIError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        return
    
    # Check if first argument is a known command
    first_arg = args[0].lower()
    if first_arg in KNOWN_COMMANDS:
        # Let Typer handle the command
        app()
        return
    
    # If we get here, it means an unknown command was provided
    # Show help or error message
    console.print(f"[red]Error:[/red] Unknown command '{first_arg}'. Use 'tcli add <title>' to create a todo or 'tcli list' to list todos.")
    console.print("Run 'tcli --help' for more information.")
    sys.exit(1)


if __name__ == "__main__":
    main()

