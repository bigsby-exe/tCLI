# tCLI - Todo API CLI Tool

A command-line interface tool for managing todos via the Todo API. Built with Python and the UV toolchain.

## Features

- **Create** todos with title, description, due dates, priority, and tags
- **List** todos with filtering and search capabilities
- **Get** individual todos by ID
- **Update** todo items with partial updates
- **Delete** todos
- **Health check** endpoint
- Beautiful table output with color coding
- JSON output option for scripting
- Config file and environment variable support

## Installation

### Prerequisites

- Python 3.11 or higher
- [UV](https://github.com/astral-sh/uv) package manager

### Install from source

```bash
# Clone the repository
git clone <repository-url>
cd tCLI

# Install dependencies and set up the project using UV
uv sync

# The CLI will be available in the UV environment
# Run commands using: uv run tcli <command>
# Or activate the environment: source .venv/bin/activate (Linux/Mac) or .venv\Scripts\activate (Windows)
```

### Install Pre-built Executable (Windows)

Pre-built Windows executables are automatically created on every push to the main branch. You can download them from:

1. **GitHub Actions Artifacts**: Go to the [Actions](https://github.com/your-username/tCLI/actions) tab, select the latest workflow run, and download the `tcli-windows-exe` artifact.
2. **GitHub Releases**: When a version tag (e.g., `v1.0.0`) is pushed, a release is automatically created with the executable attached.

The executable is a standalone `.exe` file that includes Python and all dependencies - no Python installation required!

### Build Executable Locally

To build the executable yourself:

```bash
# Install dependencies including PyInstaller
uv sync --dev

# Build the executable
uv run pyinstaller tcli.spec --clean --noconfirm

# The executable will be in the dist/ directory
# On Windows: dist/tcli.exe
```

## Configuration

tCLI supports configuration via a config file or environment variables.

### Config File

Create a config file at:
- **Windows**: `~/.tcli/config.yaml`
- **Linux/Mac**: `~/.config/tcli/config.yaml` (or `$XDG_CONFIG_HOME/tcli/config.yaml`)

Example `config.yaml`:

```yaml
api:
  base_url: "http://localhost:8000"
  api_key: "your-api-key-here"
```

### Environment Variables

You can override config file settings with environment variables:

- `TAPI_URL` - API base URL
- `TAPI_KEY` - API key

Environment variables take precedence over the config file.

## Usage

### Using the Executable

If you're using the pre-built executable, simply run:

```bash
tcli.exe <command>
```

### Using from Source

After running `uv sync`, you can use the CLI in two ways:
- **With UV**: `uv run tcli <command>` (recommended)
- **After activation**: Activate the virtual environment, then use `tcli <command>` directly

### Create a Todo

```bash
# Using executable
tcli.exe add "Complete project" --description "Finish the project documentation" --priority 2 --tags "work,urgent"

# Using from source
uv run tcli add "Complete project" --description "Finish the project documentation" --priority 2 --tags "work,urgent"
```

Options:
- `--title`, `-t`: Title of the todo (required)
- `--description`, `-d`: Description of the todo
- `--due-at`: Due date and time in ISO format (e.g., `2024-12-31T23:59:59`)
- `--priority`, `-p`: Priority level (1=highest, 5=lowest, default=3)
- `--tags`: Comma-separated list of tags
- `--estimated-minutes`, `-e`: Estimated time to complete in minutes
- `--json`: Output as JSON

### List Todos

```bash
# Using executable
tcli.exe list --status todo --limit 10

# Using from source
uv run tcli list --status todo --limit 10
```

Options:
- `--q`: Search query to filter by title (case-insensitive)
- `--tag`: Filter by a specific tag
- `--status`, `-s`: Filter by status (e.g., `todo`, `in_progress`, `done`)
- `--limit`, `-l`: Maximum number of todos to return (max: 1000)
- `--json`: Output as JSON

### Get a Todo

```bash
# Using executable
tcli.exe get <todo-id>

# Using from source
uv run tcli get <todo-id>
```

Options:
- `--json`: Output as JSON

### Update a Todo

```bash
# Using executable
tcli.exe update <todo-id> --status in_progress --priority 1

# Using from source
uv run tcli update <todo-id> --status in_progress --priority 1
```

Options:
- `--title`, `-t`: Update title
- `--description`, `-d`: Update description
- `--due-at`: Update due date and time (ISO format)
- `--status`, `-s`: Update status
- `--priority`, `-p`: Update priority
- `--tags`: Update tags (comma-separated)
- `--estimated-minutes`, `-e`: Update estimated minutes
- `--json`: Output as JSON

### Delete a Todo

```bash
# Using executable
tcli.exe delete <todo-id>

# Using from source
uv run tcli delete <todo-id>
```

### Health Check

```bash
# Using executable
tcli.exe health

# Using from source
uv run tcli health
```

Options:
- `--json`: Output as JSON

## Examples

### Create a todo with all fields

```bash
uv run tcli create \
  --title "Write API documentation" \
  --description "Create comprehensive API docs with examples" \
  --due-at "2024-12-31T23:59:59" \
  --priority 2 \
  --tags "work,documentation,urgent" \
  --estimated-minutes 120
```

### List todos with filters

```bash
# Search by title
uv run tcli list --q "project"

# Filter by tag
uv run tcli list --tag "work"

# Filter by status
uv run tcli list --status "in_progress"

# Combine filters
uv run tcli list --tag "work" --status "todo" --limit 20
```

### Update a todo

```bash
# Update status and priority
uv run tcli update <todo-id> --status done --priority 5

# Update multiple fields
uv run tcli update <todo-id> --title "Updated title" --description "New description" --tags "completed,reviewed"
```

### JSON output for scripting

```bash
# Get todos as JSON
uv run tcli list --json | jq '.[] | select(.priority == 1)'

# Create todo and get JSON response
uv run tcli create --title "New task" --json
```

## Error Handling

tCLI provides clear error messages for common issues:

- **401 Unauthorized**: Missing or invalid API key
- **403 Forbidden**: Invalid API key
- **404 Not Found**: Todo or endpoint not found
- **422 Validation Error**: Invalid input data

## Development

### Project Structure

```
tCLI/
├── pyproject.toml          # UV project configuration
├── tcli.spec               # PyInstaller configuration
├── README.md               # This file
├── .github/
│   └── workflows/
│       └── build.yml       # GitHub Actions CI/CD workflow
├── src/
│   └── tcli/
│       ├── __init__.py
│       ├── main.py         # CLI entry point
│       ├── api.py          # API client
│       ├── config.py       # Configuration management
│       ├── output.py        # Output formatting
│       └── models.py       # Pydantic models
```

### Dependencies

- `typer` - Modern CLI framework
- `httpx` - Async HTTP client
- `pydantic` - Data validation
- `pyyaml` - YAML config parsing
- `rich` - Rich text and table formatting

### Building Executables

The project uses PyInstaller to create standalone executables. The build process is automated via GitHub Actions:

- **Automatic builds**: Every push to `main`/`master` triggers a build
- **Release builds**: Pushing a version tag (e.g., `v1.0.0`) creates a GitHub release with the executable
- **Artifacts**: Build artifacts are available for 90 days in GitHub Actions

To build locally, ensure you have PyInstaller installed (via `uv sync --dev`) and run:

```bash
uv run pyinstaller tcli.spec --clean --noconfirm
```

## License

MIT

