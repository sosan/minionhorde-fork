#!/usr/bin/env python3
"""Token-based PreToolUse guard for destructive Bash commands.

The guard parses the command with :mod:`shlex`, normalizes wrappers and
flags, and inspects each simple command separately. This avoids the
false positives of regex-over-text (``grep -r 'rm -rf' docs/``) and the
false negatives of prefix matching (``rm -r -f``).

Exit codes: 0 allow, 2 deny. On deny it prints the Claude Code
``permissionDecision`` JSON contract.

Example:
    $ echo '{"tool_name":"Bash","tool_input":{"command":"rm -r -f /"}}' | guard_pretooluse.py
    {"hookSpecificOutput": {... "permissionDecision": "deny" ...}}
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys

SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
INTERPRETERS = SHELLS | {"python", "python3", "perl", "ruby", "node"}
WRAPPERS = {
    "command",
    "builtin",
    "exec",
    "time",
    "nohup",
    "nice",
    "ionice",
    "stdbuf",
    "env",
    "xargs",
}
SQL_CLIENTS = {"psql", "mysql", "mariadb", "sqlite3", "mongo", "mongosh"}
SQL_RE = re.compile(r"(?i)^\s*(drop\s+(?:table|database)|delete\s+from|truncate(?:\s+table)?)\b")
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
DANGEROUS_PYTHON = (
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
    "os.system",
    "subprocess.",
    "pathlib.path.unlink",
    "verify=false",
    "rm -rf",
)
DANGEROUS_RUBY = ("fileutils.rm_rf", "file.delete", "system(", "`rm ")
DANGEROUS_NODE = ("fs.rm", "fs.unlink", "child_process", "exec(")


def tokenize(command: str) -> list[str]:
    """Split a shell command into tokens, keeping operators as tokens.

    Example:
        >>> tokenize("curl x | bash")
        ['curl', 'x', '|', 'bash']
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars="|;&()<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return command.split()


def simple_commands(tokens: list[str]) -> list[list[str]]:
    """Split tokens on shell control operators into simple commands.

    Example:
        >>> simple_commands(["a", "&&", "b"])
        [['a'], ['b']]
    """
    commands: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in {"|", "||", "&&", ";", "&", "(", ")"}:
            if current:
                commands.append(current)
                current = []
            continue
        current.append(token)
    if current:
        commands.append(current)
    return commands


def _basename(token: str) -> str:
    return os.path.basename(token)


def _short_flags(args: list[str]) -> set[str]:
    flags: set[str] = set()
    for arg in args:
        if arg.startswith("-") and not arg.startswith("--") and len(arg) > 1:
            flags.update(arg[1:])
    return flags


def _strip_assignment(command: list[str]) -> list[str]:
    while command and ASSIGNMENT_RE.match(command[0]):
        command = command[1:]
    return command


def _strip_wrapper_flags(args: list[str]) -> list[str]:
    while args and (args[0].startswith("-") or re.match(r"^\d+$", args[0])):
        args = args[1:]
    return args


def _git_subcommand(args: list[str]) -> tuple[str, list[str]]:
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-C", "-c", "--git-dir", "--work-tree"}:
            index += 2
            continue
        if arg.startswith("-"):
            index += 1
            continue
        return arg, args[index + 1 :]
    return "", []


def _check_git(args: list[str]) -> str | None:
    subcommand, rest = _git_subcommand(args)
    if "--no-verify" in args:
        return "git --no-verify bypasses hooks"
    if subcommand == "push":
        if any(arg in {"--delete", "-d"} for arg in rest):
            return "git push --delete removes a remote branch"
        if any(arg.startswith(":") and len(arg) > 1 for arg in rest):
            return "git push with an empty refspec deletes a remote branch"
        force = any(
            arg in {"-f", "--force", "--force-with-lease", "--mirror"}
            or (arg.startswith("+") and not arg.startswith("++"))
            for arg in rest
        )
        if force:
            return "git push --force/+refspec rewrites remote history"
    elif subcommand == "reset" and "--hard" in rest:
        return "git reset --hard discards working-tree changes"
    elif subcommand == "clean":
        flags = _short_flags(rest)
        if "f" in flags or "--force" in rest:
            return "git clean -f deletes untracked files"
    elif subcommand in {"checkout", "restore", "switch"}:
        if "--" in rest:
            paths = rest[rest.index("--") + 1 :]
            if any(path in {".", "*"} for path in paths):
                return "git checkout -- . discards working-tree changes"
        if any(arg in {".", "*"} for arg in rest):
            return "git checkout/restore . discards working-tree changes"
        if any(arg in {"-f", "--force", "--worktree"} for arg in rest):
            return "git checkout/restore --force discards changes"
    elif subcommand == "stash" and rest and rest[0] in {"drop", "clear"}:
        return "git stash drop/clear discards recovery points"
    elif subcommand == "branch":
        if any(arg == "-D" or (arg.startswith("-") and not arg.startswith("--") and "D" in arg) for arg in rest):
            return "git branch -D deletes a branch without merge check"
    elif subcommand == "tag" and any(arg in {"-d", "--delete"} for arg in rest):
        return "git tag -d deletes a tag"
    return None


def _check_rm(args: list[str]) -> str | None:
    flags = _short_flags(args)
    recursive = "r" in flags or "R" in flags or "--recursive" in args
    force = "f" in flags or "--force" in args
    if recursive or force:
        return "rm -r/-f is irreversible"
    return None


def _check_find(args: list[str]) -> str | None:
    if "-delete" in args:
        return "find -delete removes files recursively"
    if "-exec" in args or "-execdir" in args:
        index = args.index("-exec") if "-exec" in args else args.index("-execdir")
        if index + 1 < len(args) and _basename(args[index + 1]) in {"rm", "shred", "unlink"}:
            return "find -exec rm removes files"
    return None


def _check_chmod(args: list[str]) -> str | None:
    modes = [arg for arg in args if not arg.startswith("-")]
    if any(mode in {"777", "0777", "a+rwx"} for mode in modes):
        return "chmod 777 makes files world-writable"
    return None


def _check_python(args: list[str]) -> str | None:
    if "-c" not in args:
        return None
    index = args.index("-c")
    if index + 1 >= len(args):
        return None
    code = args[index + 1].lower()
    if any(token in code for token in DANGEROUS_PYTHON):
        return "python -c executes destructive filesystem code"
    return None


def _check_ruby(args: list[str]) -> str | None:
    if "-e" not in args:
        return None
    index = args.index("-e")
    if index + 1 >= len(args):
        return None
    code = args[index + 1].lower()
    if any(token in code for token in DANGEROUS_RUBY):
        return "ruby -e executes destructive filesystem code"
    return None


def _check_node(args: list[str]) -> str | None:
    if not any(arg in {"-e", "--eval", "-p", "--print"} for arg in args):
        return None
    code = " ".join(args).lower()
    if any(token in code for token in DANGEROUS_NODE):
        return "node -e executes destructive filesystem code"
    return None


def _check_pipeline(tokens: list[str]) -> str | None:
    for index, token in enumerate(tokens):
        if token in {"|", "||"} and index + 1 < len(tokens):
            if _basename(tokens[index + 1]) in INTERPRETERS:
                before = " ".join(tokens[:index]).lower()
                if "curl" in before or "wget" in before or "http://" in before or "https://" in before:
                    return "piping curl/wget into an interpreter executes remote code"
    if any(_basename(token) in SHELLS for token in tokens) and any(
        token in {"<", "("} for token in tokens
    ):
        joined = " ".join(tokens).lower()
        if "curl" in joined or "wget" in joined:
            return "process substitution feeds remote code into a shell"
    return None


def _check_simple(command: list[str]) -> str | None:
    for token in command:
        lowered = token.lower()
        if (
            lowered in {
                "node_tls_reject_unauthorized=0",
                "pythonhttpsverify=0",
                "verify=false",
                "--privileged",
                "0.0.0.0",
            }
            or lowered.startswith("--privileged=")
        ):
            return f"security-weakening token: {token}"

    command = _strip_assignment(command)
    if not command:
        return None

    program = _basename(command[0])
    args = command[1:]

    if program == "sudo":
        return "sudo escalates privileges"
    if program in WRAPPERS:
        if program == "env":
            args = _strip_assignment(args)
        inner = _strip_wrapper_flags(args)
        return _check_simple(inner) if inner else None
    if program in SHELLS and "-c" in args:
        index = args.index("-c")
        if index + 1 < len(args):
            return evaluate(args[index + 1])[1] or None
    if program == "eval":
        return evaluate(" ".join(args))[1] or None
    if program == "git":
        return _check_git(args)
    if program == "rm":
        return _check_rm(args)
    if program == "find":
        return _check_find(args)
    if program == "chmod":
        return _check_chmod(args)
    if program in {"python", "python3"}:
        return _check_python(args)
    if program in {"perl", "ruby"}:
        return _check_ruby(args)
    if program == "node":
        return _check_node(args)
    if program in {"curl", "wget"}:
        if any(arg in {"-k", "--insecure", "--no-check-certificate"} for arg in args):
            return "TLS verification disabled"
    if program == "dd":
        if any(arg.startswith("of=/dev/") for arg in args):
            return "dd writing to a block device is irreversible"
    if program in {"mkfs", "shred", "wipefs", "fdisk", "parted"} or program.startswith("mkfs."):
        return f"{program} destroys disk data"
    if program in SQL_CLIENTS and any(SQL_RE.search(arg) for arg in args):
        return "destructive SQL statement"
    if program in {"drop", "delete", "truncate"} and SQL_RE.search(" ".join([program, *args])):
        return "destructive SQL statement"
    if program == "umask" and any(arg in {"000", "0"} for arg in args):
        return "umask 000 makes new files world-writable"
    return None


def evaluate(command: str) -> tuple[bool, str]:
    """Return ``(blocked, reason)`` for a shell command.

    Example:
        >>> evaluate("rm -r -f /")[0]
        True
        >>> evaluate("git log --grep=sudo")[0]
        False
    """
    if not command or not command.strip():
        return False, ""
    unquoted = re.sub(r"'[^']*'", "", command)
    for inner in re.findall(r"`([^`]*)`", unquoted):
        blocked, reason = evaluate(inner)
        if blocked:
            return True, reason
    tokens = tokenize(command)
    pipeline_reason = _check_pipeline(tokens)
    if pipeline_reason:
        return True, pipeline_reason
    for simple in simple_commands(tokens):
        reason = _check_simple(simple)
        if reason:
            return True, reason
    return False, ""


def main() -> int:
    payload = sys.stdin.read()
    if not payload.strip():
        return 0
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    command = data.get("tool_input", {}).get("command", "")
    blocked, reason = evaluate(command)
    if not blocked:
        return 0
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Blocked by guard_pretooluse: {reason}. "
                "Use the explicit approval flow (CORE Inv 2)."
            ),
        }
    }
    sys.stdout.write(json.dumps(output))
    print(output["hookSpecificOutput"]["permissionDecisionReason"], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
