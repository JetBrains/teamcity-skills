#!/usr/bin/env python3
"""Expose a scoped, authenticated TeamCity CLI to an eval agent.

The evaluation lifecycle owns a TeamCity token, but the target checkout and
the coding agent must never inherit it.  This bridge keeps the token in the
runner process and exposes a small wrapper that forwards only approved
first-class CLI commands.  Writes are limited to the temporary eval project.
"""

import json
import os
import pathlib
import secrets
import shutil
import socketserver
import subprocess
import sys
import threading
from typing import Callable, Iterable, Optional


class BridgeError(RuntimeError):
    """The bridge could not start or rejected an unsafe operation."""


def _flag_value(arguments: list, *names: str) -> Optional[str]:
    for index, argument in enumerate(arguments):
        for name in names:
            if argument == name and index + 1 < len(arguments):
                return arguments[index + 1]
            if argument.startswith(name + "="):
                return argument.split("=", 1)[1]
    return None


def _positional(arguments: list) -> list:
    """Return positional tokens while skipping common flag values."""
    values = []
    skip_next = False
    value_flags = {
        "--project", "-p", "--file", "-f", "--vcs-root", "--output",
        "--schema", "--branch", "--branch-spec", "--url", "--auth",
        "--connection-id", "--name", "--agent", "--interval", "-i",
        "--timeout", "--path", "--artifact", "--job", "--limit", "-n",
    }
    for argument in arguments:
        if skip_next:
            skip_next = False
            continue
        if argument in value_flags:
            skip_next = True
            continue
        if argument.startswith("-"):
            continue
        values.append(argument)
    return values


class CommandPolicy:
    """Allow the CLI surface needed by the eval while constraining writes."""

    def __init__(
        self,
        target_project: str,
        checkout: pathlib.Path,
        allow_build_writes: bool,
        pipeline_ids: Callable[[], Iterable[str]],
        job_ids: Callable[[], Iterable[str]],
    ):
        self.target_project = target_project
        self.checkout = checkout.resolve()
        self.allow_build_writes = allow_build_writes
        self.pipeline_ids = pipeline_ids
        self.job_ids = job_ids

    def _require_target_project(self, arguments: list) -> None:
        project = _flag_value(arguments, "--project", "-p")
        if project != self.target_project:
            raise BridgeError(
                "the eval CLI bridge permits writes only in the temporary target project"
            )

    def _require_known_pipeline(self, arguments: list) -> None:
        positionals = _positional(arguments)
        pipeline_id = positionals[2] if len(positionals) > 2 else None
        if not pipeline_id or pipeline_id not in set(self.pipeline_ids()):
            raise BridgeError("the pipeline is outside the temporary target project")

    def _require_known_job(self, arguments: list) -> None:
        positionals = _positional(arguments)
        job_id = positionals[2] if len(positionals) > 2 else None
        if not job_id or job_id not in set(self.job_ids()):
            raise BridgeError("the job is outside the temporary target project")

    def authorize(self, arguments: list, cwd: pathlib.Path) -> None:
        try:
            cwd.resolve().relative_to(self.checkout)
        except ValueError:
            raise BridgeError("TeamCity CLI commands must run inside the target checkout")

        if not arguments:
            raise BridgeError("a TeamCity CLI command is required")
        if any(flag in arguments for flag in ("--debug", "--verbose", "-V")):
            raise BridgeError("verbose/debug CLI output is disabled to protect credentials")
        if any(flag in arguments for flag in ("--help", "-h")):
            return
        if arguments in (["--version"], ["-v"]):
            return

        positionals = _positional(arguments)
        if len(positionals) < 2:
            raise BridgeError("unsupported TeamCity CLI command")
        area, operation = positionals[0], positionals[1]

        if area == "auth" and operation == "status":
            return
        if area == "migrate":
            return
        if area == "agent" and operation in {"list", "view", "jobs"}:
            return
        if area == "job" and operation in {"list", "view"}:
            return
        if area == "queue" and operation == "list":
            return

        if area == "project":
            if operation in {"list", "view"}:
                return
            if operation == "connection" and len(positionals) > 2 \
                    and positionals[2] in {"list", "view"}:
                return
            if operation == "vcs" and len(positionals) > 2:
                vcs_operation = positionals[2]
                if vcs_operation in {"list", "view", "test"}:
                    return
                if vcs_operation == "create":
                    self._require_target_project(arguments)
                    return

        if area == "pipeline":
            if operation in {"schema", "validate"}:
                return
            if operation in {"list"}:
                self._require_target_project(arguments)
                return
            if operation == "create":
                self._require_target_project(arguments)
                return
            if operation in {"view", "pull"}:
                self._require_known_pipeline(arguments)
                return
            if operation == "push":
                self._require_known_pipeline(arguments)
                return

        if area == "run":
            if operation in {"list", "view", "watch", "tree", "tests", "changes", "artifacts"}:
                return
            if operation in {"start", "restart", "cancel"} and self.allow_build_writes:
                self._require_known_job(arguments)
                return

        raise BridgeError(f"unsupported TeamCity CLI operation: {area} {operation}")


class _BridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _BridgeHandler(socketserver.StreamRequestHandler):
    def handle(self):
        bridge = self.server.bridge
        try:
            request = json.loads(self.rfile.readline(1024 * 1024))
            if request.get("nonce") != bridge.nonce:
                raise BridgeError("invalid bridge nonce")
            arguments = request.get("arguments")
            if not isinstance(arguments, list) or not all(isinstance(v, str) for v in arguments):
                raise BridgeError("invalid CLI arguments")
            cwd = pathlib.Path(request.get("cwd", ""))
            bridge.policy.authorize(arguments, cwd)
            outcome = bridge.execute(arguments, cwd)
            response = {
                "returncode": outcome.returncode,
                "stdout": outcome.stdout,
                "stderr": outcome.stderr,
            }
        except Exception as exc:  # Return a normal CLI-style failure to the wrapper.
            response = {"returncode": 2, "stdout": "", "stderr": f"Error: {exc}\n"}
        self.wfile.write(json.dumps(response).encode() + b"\n")


class TeamCityCliBridge:
    """Context manager for the scoped wrapper and its token-holding broker."""

    def __init__(
        self,
        cli: str,
        server_url: str,
        token: str,
        workspace: pathlib.Path,
        checkout: pathlib.Path,
        target_project: str,
        allow_build_writes: bool,
        pipeline_ids: Callable[[], Iterable[str]],
        job_ids: Callable[[], Iterable[str]],
        base_env: dict,
    ):
        self.cli = pathlib.Path(cli).resolve()
        self.server_url = server_url
        self.token = token
        self.workspace = workspace
        self.checkout = checkout
        self.base_env = dict(base_env)
        self.nonce = secrets.token_urlsafe(24)
        self.policy = CommandPolicy(
            target_project, checkout, allow_build_writes, pipeline_ids, job_ids
        )
        self.server = None
        self.thread = None
        self.wrapper_dir = workspace / "teamcity-cli-bridge"

    def execute(self, arguments: list, cwd: pathlib.Path) -> subprocess.CompletedProcess:
        command_env = dict(self.base_env)
        command_env["TEAMCITY_URL"] = self.server_url
        command_env["TEAMCITY_TOKEN"] = self.token
        command_env.pop("TEAMCITY_GUEST", None)
        command = [str(self.cli), *arguments]
        if os.name == "nt" and self.cli.suffix.lower() in {".cmd", ".bat"}:
            command = ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline(command)]
        return subprocess.run(
            command, cwd=cwd, env=command_env,
            capture_output=True, text=True, errors="replace", timeout=300,
        )

    def _write_client(self, host: str, port: int) -> None:
        self.wrapper_dir.mkdir()
        client = self.wrapper_dir / "client.py"
        client.write_text(
            "import json, os, socket, sys\n"
            f"request = {{'nonce': {self.nonce!r}, 'arguments': sys.argv[1:], 'cwd': os.getcwd()}}\n"
            f"with socket.create_connection(({host!r}, {port}), timeout=310) as connection:\n"
            "    connection.sendall(json.dumps(request).encode() + b'\\n')\n"
            "    response_file = connection.makefile('rb')\n"
            "    response = json.loads(response_file.readline())\n"
            "sys.stdout.write(response.get('stdout', ''))\n"
            "sys.stderr.write(response.get('stderr', ''))\n"
            "raise SystemExit(response.get('returncode', 2))\n"
        )
        launcher = self.wrapper_dir / "teamcity"
        python_for_shell = pathlib.Path(sys.executable).as_posix()
        client_for_shell = client.as_posix()
        launcher.write_text(
            f"#!/bin/sh\nexec {shlex_quote(python_for_shell)} "
            f"{shlex_quote(client_for_shell)} \"$@\"\n"
        )
        launcher.chmod(0o755)
        (self.wrapper_dir / "teamcity.cmd").write_text(
            f'@"{sys.executable}" "{client}" %*\r\n'
        )

    def __enter__(self):
        if not self.cli.is_file():
            raise BridgeError(f"TeamCity CLI executable not found: {self.cli}")
        self.server = _BridgeServer(("127.0.0.1", 0), _BridgeHandler)
        self.server.bridge = self
        host, port = self.server.server_address
        self._write_client(host, port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, _type, _value, _traceback):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=5)
        self.token = ""

    def agent_environment(self, environment: dict) -> dict:
        result = dict(environment)
        result.pop("TEAMCITY_TOKEN", None)
        result.pop("TEAMCITY_GUEST", None)
        result["TEAMCITY_URL"] = self.server_url
        result["TEAMCITY_EVAL_CLI"] = "teamcity"
        result["PATH"] = str(self.wrapper_dir) + os.pathsep + result.get("PATH", "")
        return result


def shlex_quote(value: str) -> str:
    """Quote one shell argument without importing a shell at execution time."""
    import shlex
    return shlex.quote(value)
