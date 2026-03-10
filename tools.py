"""
Tool definitions and execution for the Claude Code clone.

Each tool has two parts:
1. A JSON schema definition that tells Claude what the tool does and what arguments it takes.
   This is passed to the API so Claude knows what tools are available.
2. A Python function that actually executes the tool when Claude decides to use it.
"""

import glob as glob_module
import os
import re
import subprocess


# --- Tool definitions (sent to the API) ---
# These follow the Anthropic tool schema format. Claude reads these descriptions
# to decide when and how to use each tool.

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file at the given path. Use this to examine existing code or files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to read",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file at the given path. Creates the file if it doesn't exist, overwrites if it does.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Make a surgical edit to a file by replacing an exact string match. "
            "The old_string must appear exactly once in the file (including whitespace and indentation). "
            "Use read_file first to see the current contents. "
            "Prefer this over write_file when modifying existing files — it only changes what needs to change."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact string to find and replace (must be unique in the file)",
                },
                "new_string": {
                    "type": "string",
                    "description": "The string to replace it with",
                },
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "grep",
        "description": (
            "Search for a regex pattern across files in a directory. "
            "Returns matching lines with file paths and line numbers. "
            "Use this to find where functions, variables, or patterns are used in the codebase."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "The directory to search in (defaults to current directory)",
                    "default": ".",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "glob",
        "description": (
            "Find files matching a glob pattern (e.g. '**/*.py' for all Python files). "
            "Returns a list of matching file paths. "
            "Use this to discover project structure and find files by name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match (e.g. '**/*.py', 'src/**/*.ts', '*.json')",
                },
                "path": {
                    "type": "string",
                    "description": "The directory to search in (defaults to current directory)",
                    "default": ".",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "run_command",
        "description": (
            "Run a shell command and return its output. "
            "Use this for tasks like running tests, installing packages, git operations, etc. "
            "Prefer grep and glob tools over shell grep/find commands."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run",
                }
            },
            "required": ["command"],
        },
    },
]


# --- Tool execution ---
# When Claude responds with a tool_use block, we look up the tool name here
# and call the corresponding function with the arguments Claude provided.


def execute_tool(name, input):
    """Execute a tool by name with the given input. Returns the result as a string."""
    if name == "read_file":
        return _read_file(input["path"])
    elif name == "write_file":
        return _write_file(input["path"], input["content"])
    elif name == "edit_file":
        return _edit_file(input["path"], input["old_string"], input["new_string"])
    elif name == "grep":
        return _grep(input["pattern"], input.get("path", "."))
    elif name == "glob":
        return _glob(input["pattern"], input.get("path", "."))
    elif name == "run_command":
        return _run_command(input["command"])
    else:
        return f"Unknown tool: {name}"


def _read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def _write_file(path, content):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def _edit_file(path, old_string, new_string):
    try:
        with open(path, "r") as f:
            content = f.read()

        # The old_string must appear exactly once to avoid ambiguous edits.
        count = content.count(old_string)
        if count == 0:
            return f"Error: old_string not found in {path}"
        if count > 1:
            return f"Error: old_string appears {count} times in {path} — must be unique"

        new_content = content.replace(old_string, new_string, 1)
        with open(path, "w") as f:
            f.write(new_content)
        return f"Successfully edited {path}"
    except Exception as e:
        return f"Error editing file: {e}"


def _grep(pattern, path):
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"Invalid regex: {e}"

    matches = []
    for root, dirs, files in os.walk(path):
        # Skip hidden dirs and common non-code dirs
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", ".venv")]
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, "r", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append(f"{filepath}:{i}: {line.rstrip()}")
            except (OSError, IsADirectoryError):
                continue

    if not matches:
        return "No matches found"
    return "\n".join(matches[:100])  # Cap at 100 results


def _glob(pattern, path):
    full_pattern = os.path.join(path, pattern)
    matches = glob_module.glob(full_pattern, recursive=True)
    # Filter out hidden dirs and common non-code dirs
    skip = {".git", ".venv", "node_modules", "__pycache__"}
    filtered = []
    for m in matches:
        parts = m.split(os.sep)
        if any(p in skip or (p.startswith(".") and p != ".") for p in parts):
            continue
        if os.path.isfile(m):
            filtered.append(os.path.relpath(m, path))

    if not filtered:
        return "No files found"
    return "\n".join(sorted(filtered))


def _run_command(command):
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        if result.returncode != 0:
            output += f"\n(exit code: {result.returncode})"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30 seconds"
    except Exception as e:
        return f"Error running command: {e}"
