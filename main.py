"""
A minimal Claude Code clone — an interactive REPL that talks to Claude via Vertex AI.

The core loop:
1. User types a message
2. Send message + conversation history + tool definitions to Claude
3. If Claude responds with text, print it
4. If Claude responds with tool calls, execute them and send results back to Claude
5. Repeat step 3-4 until Claude is done (responds with text only)
"""

import os
import sys

from anthropic import AnthropicVertex

from tools import TOOLS, execute_tool


def main():
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    region = os.environ.get("GOOGLE_CLOUD_REGION", "us-east5")
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    if not project:
        print("Error: set GOOGLE_CLOUD_PROJECT environment variable")
        sys.exit(1)

    client = AnthropicVertex(project_id=project, region=region)

    system_prompt = (
        "You are a helpful coding assistant. You are running inside a CLI tool "
        "on the user's machine. Help them with software engineering tasks. "
        "You have tools available to read files, write files, and run shell commands. "
        "Use them when needed to accomplish the user's task."
    )

    # Conversation history — every user and assistant message is appended here
    # so Claude has full context of the session.
    messages = []

    print("Claude Code (Python) — type 'quit' to exit")
    print()

    while True:
        try:
            user_input = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.strip().lower() in ("quit", "exit"):
            break

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        # --- The agentic tool loop ---
        # We keep calling Claude until it stops requesting tools.
        # Each iteration: send messages -> check response -> maybe execute tools -> repeat.
        while True:
            response = client.messages.create(
                model=model,
                max_tokens=8096,
                system=system_prompt,
                messages=messages,
                tools=TOOLS,
            )

            # Append Claude's full response (text + tool_use blocks) to history.
            messages.append({"role": "assistant", "content": response.content})

            # Print any text blocks Claude included in this response.
            for block in response.content:
                if block.type == "text":
                    print()
                    print(block.text)

            # If Claude didn't ask to use any tools, we're done — break out
            # and wait for the next user input.
            if response.stop_reason == "end_turn":
                print()
                break

            # Claude wants to use tools. Execute each tool call and collect results.
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n[tool: {block.name}({block.input})]")

                    result = execute_tool(block.name, block.input)
                    print(f"[result: {result[:200]}{'...' if len(result) > 200 else ''}]")

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            # Send tool results back to Claude. This is the key mechanic:
            # tool results go in a "user" message, and Claude will respond
            # with either more tool calls or a final text answer.
            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    main()
