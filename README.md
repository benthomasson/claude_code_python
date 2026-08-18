# claude-code-python

A minimal Python reimplementation of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) using the Vertex AI API. Built as a learning tool to understand how Claude Code works under the hood — specifically how an LLM uses tools in an agentic loop to accomplish coding tasks.

## Why this exists

Claude Code is a powerful but opaque tool. This project strips it down to the bare essentials so you can see exactly what's happening:

- How the conversation loop works (send message, check for tool calls, execute tools, repeat)
- How tools are defined and passed to the API
- How tool results are fed back into the conversation
- How a simple system prompt shapes the assistant's behavior

By reading and running this code, you should come away understanding the core mechanic that makes Claude Code work: **Claude doesn't just generate text — it decides when and how to use tools, and the host program executes those tools and returns the results.**

## What it does

An interactive CLI tool that:

- Starts a conversation loop where you describe coding tasks
- Sends your messages to Claude on Vertex AI
- Gives Claude access to tools (read/write files, run shell commands) so it can explore and modify your codebase
- Prints Claude's responses and tool calls to your terminal

## Prerequisites

- Python 3.11+
- A Google Cloud project with the Vertex AI API enabled
- `gcloud` CLI installed and authenticated (`gcloud auth application-default login`)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your Google Cloud project and region:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_REGION="us-east5"  # or your preferred region
```

## Usage

```bash
python main.py
```

Then type your request at the `> ` prompt. Type `quit` or `exit` to end the session.

## Models

Set the `MODEL` environment variable to choose a backend. Defaults to Vertex AI with `claude-sonnet-4-20250514`.

```bash
# Vertex AI (default) — requires GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_REGION
MODEL=claude-sonnet-4-20250514 python main.py

# Ollama (local) — requires Ollama running (default: localhost:11434)
MODEL=ollama:llama3.1 python main.py
MODEL=ollama:qwen3:8b python main.py

# Ollama on a remote host
OLLAMA_HOST=http://192.168.1.100:11434 MODEL=ollama:llama3.1 python main.py

# Direct Anthropic API — requires ANTHROPIC_API_KEY
MODEL=api:claude-sonnet-4-20250514 python main.py
```

## How it works

1. Your input is sent to Claude via the Vertex AI Anthropic endpoint
2. Claude can call tools to read files, write files, and run shell commands
3. Tool results are sent back to Claude so it can continue working
4. The conversation history is maintained for the duration of the session

## Project structure

```
main.py           # Entry point and conversation loop
tools.py          # Tool definitions and execution
```

## What's intentionally left out

This project is about understanding the core loop, not building a production tool. Things the real Claude Code does that this doesn't:

- **Permission prompts** — the real tool asks before writing files or running commands
- **Streaming** — the real tool streams tokens as they arrive
- **Context window management** — the real tool summarizes/compresses history when it gets long
- **Specialized tools** — the real tool has many more tools (glob, grep, git, etc.)
- **Error recovery** — the real tool handles failures gracefully

Each of these would be a good exercise to add if you want to go deeper.
