"""Run a shell command and return its output, working directory locked to project root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TOOL_SPEC = {
    "name": "shell_command",
    "description": (
        "Run a shell command and return its stdout, stderr, and exit code. "
        "The command runs with the project root as the working directory. "
        "On Windows, commands run via cmd.exe. On Linux/macOS, via /bin/sh. "
        "Use for running scripts, checking tool versions, listing directory contents, "
        "compiling code, etc. Timeout is 60 seconds. "
        "Avoid commands that require interactive input."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (1-120). Default 60.",
            },
        },
        "required": ["command"],
    },
}

_BLOCKED = (
    "rm -rf /",
    "format ",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",  # fork bomb
)


def run(args: dict, context: dict) -> dict:
    project_root = Path(context.get("project_root", Path.cwd())).resolve()
    command = str(args["command"]).strip()
    timeout = min(max(1, int(args.get("timeout", 60))), 120)

    if not command:
        return {"error": "command must not be empty"}

    # Reject obviously destructive patterns
    cmd_lower = command.lower()
    for blocked in _BLOCKED:
        if blocked in cmd_lower:
            return {"error": f"Command blocked for safety: contains '{blocked}'"}

    if sys.platform == "win32":
        shell_args = ["cmd.exe", "/c", command]
    else:
        shell_args = ["/bin/sh", "-c", command]

    try:
        proc = subprocess.run(
            shell_args,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "error": f"Command timed out after {timeout}s",
            "command": command,
        }
    except OSError as exc:
        return {"error": f"Failed to start process: {exc}", "command": command}

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    # Truncate very long output to protect context window
    _MAX = 8_000
    truncated = False
    if len(stdout) > _MAX:
        stdout = stdout[:_MAX] + "\n[...output truncated...]"
        truncated = True
    if len(stderr) > _MAX:
        stderr = stderr[:_MAX] + "\n[...output truncated...]"
        truncated = True

    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": truncated,
    }
