# How the Raw Python Claude Code Clone Works

**Date:** 2026-03-12
**Time:** 11:57

## Overview

This project is a minimal reimplementation of Claude Code using the raw Anthropic Python SDK with Vertex AI. No frameworks, no abstractions — just the API calls and a while loop. It exists to make the core mechanic of agentic tool use completely transparent: **Claude decides when to call tools, and the host program executes them and returns the results.**

A companion project at `../claude_code_langgraph` implements the same thing with LangGraph and Langfuse, so you can compare what the framework abstracts away.

## The Two Files

- **`main.py`** — The REPL and agentic tool loop (~110 lines)
- **`tools.py`** — Tool definitions (JSON schemas) and execution functions (~150 lines)

That's it. The entire coding assistant is under 300 lines of Python.

## The Conversation Loop

The outer loop in `main.py` is a standard REPL:

1. Read user input
2. Append it to `messages` list
3. Run the agentic tool loop (inner loop)
4. Print the result
5. Repeat

The `messages` list is the conversation history — every user message, assistant response, and tool result is appended here. This is passed to the API on every call so Claude has full context.

## The Agentic Tool Loop

This is the core mechanic. After the user sends a message, we enter an inner loop:

```python
for tool_round in range(MAX_TOOL_ROUNDS):
    response = client.messages.create(
        model=model, max_tokens=8096,
        system=system_prompt, messages=messages, tools=TOOLS,
    )
    messages.append({'role': 'assistant', 'content': response.content})

    if response.stop_reason == 'end_turn':
        break  # Claude is done, no more tool calls

    # Execute each tool call and collect results
    tool_results = []
    for block in response.content:
        if block.type == 'tool_use':
            result = execute_tool(block.name, block.input)
            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': block.id,
                'content': result,
            })

    # Send results back as a user message
    messages.append({'role': 'user', 'content': tool_results})
```

Key details:

- **`stop_reason`**: When Claude responds with `'end_turn'`, it means it has nothing more to do — no tool calls, just text. When it responds with `'tool_use'`, it wants to call tools.
- **`tool_use` blocks**: Claude's response can contain a mix of text and tool_use blocks. Each tool_use block has a `name`, `input` (arguments), and `id`.
- **`tool_result` messages**: After executing tools, results go back to Claude as a `'user'` message containing `tool_result` content blocks. Each result is matched to its tool call via `tool_use_id`.
- **The loop continues**: Claude sees the tool results and decides what to do next — call more tools, or respond with text.
- **Max rounds**: Capped at 10 iterations to prevent runaway loops.

## Tool Definitions

Each tool has two parts in `tools.py`:

### 1. JSON Schema (sent to the API)

```python
{
    'name': 'read_file',
    'description': 'Read the contents of a file at the given path.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'path': {'type': 'string', 'description': 'The path to the file to read'}
        },
        'required': ['path'],
    },
}
```

Claude reads these descriptions to decide when and how to use each tool. The quality of the description directly affects how well Claude uses the tool.

### 2. Execution Function

```python
def _read_file(path):
    with open(path, 'r') as f:
        return f.read()
```

A plain Python function that does the actual work. The `execute_tool()` function dispatches by name:

```python
def execute_tool(name, input):
    if name == 'read_file':
        return _read_file(input['path'])
    elif name == 'write_file':
        return _write_file(input['path'], input['content'])
    ...
```

### The Six Tools

| Tool | What it does |
|---|---|
| `read_file` | Read a file's contents |
| `write_file` | Create or overwrite a file |
| `edit_file` | Find-and-replace a unique string in a file (surgical edit) |
| `grep` | Regex search across files, returns path:line:match |
| `glob` | Find files by glob pattern (e.g. `**/*.py`) |
| `run_command` | Run a shell command, return stdout/stderr |

`edit_file` is the most important one for understanding Claude Code. Rather than rewriting entire files, Claude sends an `old_string` (which must be unique in the file) and a `new_string` to replace it with. This is how it makes surgical edits.

## The Vertex AI Client

The project uses `AnthropicVertex` from the `anthropic` SDK instead of the base `Anthropic` client:

```python
from anthropic import AnthropicVertex
client = AnthropicVertex(project_id=project, region=region)
```

This routes API calls through Google Cloud Vertex AI instead of the direct Anthropic API. The API itself is identical — same message format, same tool schemas, same response structure. The only difference is authentication (GCP credentials via `gcloud auth` instead of an Anthropic API key).

## What This Teaches

1. **Tool use is just a protocol.** You send tool schemas with your request. Claude responds with `tool_use` blocks. You execute them and send `tool_result` blocks back. That's the entire mechanism.
2. **The host program is in control.** Claude never executes anything directly. It says "I want to call read_file with path=main.py" and your code decides whether and how to do it.
3. **Conversation history is everything.** The `messages` list accumulates the full context — user inputs, Claude's reasoning, tool calls, and tool results. Claude uses all of this to decide what to do next.
4. **The loop is simple.** The entire agentic behavior comes from a for loop that checks `stop_reason`. There is no planning system, no task queue, no state machine — just "call Claude, maybe run tools, repeat."
