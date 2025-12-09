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
from tcli.models import TodoCreate, TodoRead, TodoUpdate
from tcli.output import print_json, print_todo_detail, print_todo_table

app = typer.Typer(help="CLI tool for managing todos via the Todo API")
console = Console()

# Known commands that should not be treated as todo titles
KNOWN_COMMANDS = {"list", "update", "delete", "get", "add", "edit", "done"}


def parse_date(date_str: str) -> datetime:
    """
    Parse a date string in various formats and return a datetime object.
    
    Supports:
    - ISO format with time: 2025-01-01T00:00:00, 2025-01-01T12:30:45
    - ISO format date-only: 2025-01-01
    - US format: 01/01/2025, 1/1/2025, 01-01-2025
    - ISO format with Z: 2025-01-01T00:00:00Z
    
    If only a date is provided (no time), defaults to midnight (00:00:00).
    """
    date_str = date_str.strip()
    
    # Try ISO format with time first (handles full ISO and Z suffix)
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        pass
    
    # Try ISO format date-only (YYYY-MM-DD)
    # Check if it looks like ISO format (starts with 4 digits)
    if len(date_str) == 10 and date_str.count("-") == 2 and date_str[0:4].isdigit():
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass
    
    # Try US format with slash (MM/DD/YYYY)
    if "/" in date_str:
        parts = date_str.split("/")
        if len(parts) == 3:
            try:
                return datetime.strptime(date_str, "%m/%d/%Y")
            except ValueError:
                pass
    
    # Try US format with dash (MM-DD-YYYY)
    # Only if it doesn't look like ISO format (doesn't start with 4 digits)
    if "-" in date_str and len(date_str) == 10 and not date_str[0:4].isdigit():
        try:
            return datetime.strptime(date_str, "%m-%d-%Y")
        except ValueError:
            pass
    
    # If all parsing attempts fail, raise an error
    raise ValueError(
        f"Invalid date format: {date_str}. "
        f"Supported formats: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, MM/DD/YYYY, MM-DD-YYYY"
    )


def get_client(config_path: Optional[Path] = None) -> APIClient:
    """Get an API client instance."""
    try:
        config = Config(config_path)
        return APIClient(config.base_url, config.api_key)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def _calculate_fuzzy_score(search_term: str, title: str) -> float:
    """
    Calculate a fuzzy matching score between search term and title.
    Returns a score from 0.0 to 100.0, with higher scores indicating better matches.
    """
    search_lower = search_term.lower().strip()
    title_lower = title.lower().strip()
    
    # Exact match (case-insensitive)
    if search_lower == title_lower:
        return 100.0
    
    # Starts with match
    if title_lower.startswith(search_lower):
        return 90.0
    
    # Contains match
    if search_lower in title_lower:
        return 80.0
    
    # Word-based matching: check if all words in search appear in title
    search_words = [w for w in search_lower.split() if w]
    title_words = [w for w in title_lower.split() if w]
    
    if search_words:
        matching_words = sum(1 for word in search_words if word in title_words)
        word_match_ratio = matching_words / len(search_words)
        
        # If all words match, give high score
        if word_match_ratio == 1.0:
            return 70.0
        
        # Partial word match
        if word_match_ratio > 0.5:
            return 50.0 + (word_match_ratio - 0.5) * 40.0
    
    # Character-based similarity (only as last resort, with strict threshold)
    # Ignore spaces and count unique characters
    search_chars = set(search_lower.replace(" ", ""))
    title_chars = set(title_lower.replace(" ", ""))
    common_chars = search_chars & title_chars
    
    if search_chars and len(search_chars) >= 3:  # Only use for longer search terms
        char_ratio = len(common_chars) / len(search_chars)
        # Require at least 70% character match to get any score
        if char_ratio >= 0.7:
            return char_ratio * 40.0
    
    return 0.0


def _resolve_task_identifier(
    identifier: str,
    client: APIClient,
) -> TodoRead:
    """
    Resolve a task identifier (UUID or name) to a TodoRead object.
    
    Supports:
    - UUID: Direct lookup by ID
    - Name: Fuzzy matching against all todos
    
    When multiple tasks match a name, displays them and prompts for selection.
    """
    # Try to parse as UUID first
    try:
        todo_id = UUID(identifier)
        return client.get_todo(todo_id)
    except ValueError:
        # Not a UUID, treat as name and do fuzzy matching
        pass
    
    # Fetch all todos for fuzzy matching
    try:
        all_todos = client.list_todos(q=None, tag=None, status=None, limit=1000)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    
    if not all_todos:
        console.print(f"[red]Error:[/red] No todos found in the system.")
        sys.exit(1)
    
    # Calculate fuzzy scores for all todos
    scored_todos = [
        (todo, _calculate_fuzzy_score(identifier, todo.title))
        for todo in all_todos
    ]
    
    # Filter out todos with low scores and sort by score (descending)
    # Only show matches with score >= 25.0 to avoid too many false positives
    MIN_SCORE_THRESHOLD = 25.0
    scored_todos = [(todo, score) for todo, score in scored_todos if score >= MIN_SCORE_THRESHOLD]
    scored_todos.sort(key=lambda x: x[1], reverse=True)
    
    if not scored_todos:
        console.print(f"[red]Error:[/red] No todos found matching '{identifier}'")
        sys.exit(1)
    
    # If only one match, return it
    if len(scored_todos) == 1:
        return scored_todos[0][0]
    
    # Multiple matches - show table and prompt for selection
    matching_todos = [todo for todo, score in scored_todos]
    console.print(f"\n[yellow]Multiple tasks found matching '{identifier}':[/yellow]")
    print_todo_table(matching_todos)
    
    # Prompt for selection
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            selection = typer.prompt(
                f"\nEnter the task ID or index (1-{len(matching_todos)}) to select",
                default="",
            ).strip()
            
            if not selection:
                console.print("[red]Error:[/red] Selection cannot be empty.")
                continue
            
            # Try to parse as UUID
            try:
                selected_id = UUID(selection)
                # Find matching todo by ID
                for todo in matching_todos:
                    if todo.id == selected_id:
                        return todo
                console.print(f"[red]Error:[/red] Task with ID {selection} not found in the matches above.")
                continue
            except ValueError:
                # Not a UUID, try as index
                pass
            
            # Try to parse as index
            try:
                index = int(selection)
                if 1 <= index <= len(matching_todos):
                    return matching_todos[index - 1]
                else:
                    console.print(
                        f"[red]Error:[/red] Index must be between 1 and {len(matching_todos)}"
                    )
                    continue
            except ValueError:
                console.print(
                    "[red]Error:[/red] Invalid input. Enter a valid UUID or index number."
                )
                continue
                
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Selection cancelled.[/yellow]")
            sys.exit(1)
    
    # If we get here, max attempts reached
    console.print(f"[red]Error:[/red] Maximum selection attempts reached.")
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
            due_at_dt = parse_date(due_at)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
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
    due_at: Optional[str] = typer.Option(None, "--due-at", help="Due date (supports: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, MM/DD/YYYY)"),
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
                todos = [todo for todo in todos if (getattr(todo, "status") or "").lower() != "done"]
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
    due_at: Optional[str] = typer.Option(None, "--due-at", help="Due date (supports: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, MM/DD/YYYY)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Status (todo, in_progress, done)"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Priority (1=highest, 5=lowest)"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags"),
    estimated_minutes: Optional[int] = typer.Option(None, "--estimated-minutes", "-e", help="Estimated minutes"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """Update a todo item."""
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
            due_at_dt = parse_date(due_at)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
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
    item_id: str = typer.Argument(..., help="Todo ID (UUID) or name (supports fuzzy matching)"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Title of the todo"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description of the todo"),
    due_at: Optional[str] = typer.Option(None, "--due-at", help="Due date (supports: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, MM/DD/YYYY)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Status (todo, in_progress, done)"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Priority (1=highest, 5=lowest)"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags"),
    estimated_minutes: Optional[int] = typer.Option(None, "--estimated-minutes", "-e", help="Estimated minutes"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """Edit a todo item (alias for update)."""
    # Parse tags
    tag_list = None
    if tags is not None:
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else None

    # Parse due_at
    due_at_dt = None
    if due_at:
        try:
            due_at_dt = parse_date(due_at)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
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
            # Resolve task identifier (UUID or name with fuzzy matching)
            todo = _resolve_task_identifier(item_id, client)
            todo = client.update_todo(todo.id, todo_update)
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
    item_id: str = typer.Argument(..., help="Todo ID (UUID) or name (supports fuzzy matching)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """Mark a todo as done."""
    todo_update = TodoUpdate(status="done")

    try:
        with get_client(config_path) as client:
            # Resolve task identifier (UUID or name with fuzzy matching)
            todo = _resolve_task_identifier(item_id, client)
            todo = client.update_todo(todo.id, todo_update)
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
    item_id: str = typer.Argument(..., help="Todo ID (UUID) or name (supports fuzzy matching)"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
):
    """Delete a todo item."""
    try:
        with get_client(config_path) as client:
            # Resolve task identifier (UUID or name with fuzzy matching)
            todo = _resolve_task_identifier(item_id, client)
            client.delete_todo(todo.id)
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
                todos = [todo for todo in todos if (getattr(todo, "status") or "").lower() != "done"]
                
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

