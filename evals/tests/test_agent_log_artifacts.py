import importlib.util
import json
import pathlib
import tempfile
import time
import unittest
from unittest import mock


EVALS = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_case_log_artifacts_test", EVALS / "run_case.py")
run_case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_case)

CLAUDE_SESSION = "11111111-2222-3333-4444-555555555555"
CODEX_SESSION = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


class AgentLogArtifactsTest(unittest.TestCase):
    def test_claude_copies_only_current_session_and_its_debug_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            config = root / ".claude"
            project = config / "projects" / "-checkout"
            project.mkdir(parents=True)
            (config / "debug").mkdir()
            trace = root / "trace.log"
            trace.write_text("--- output ---\n" + json.dumps({
                "type": "system", "subtype": "init", "session_id": CLAUDE_SESSION,
            }) + "\n")
            started_at = time.time()
            (project / f"{CLAUDE_SESSION}.jsonl").write_text("current session")
            (config / "debug" / f"{CLAUDE_SESSION}.txt").write_text("current debug")
            (project / "99999999-2222-3333-4444-555555555555.jsonl").write_text("other session")
            (config / "auth.json").write_text("credential")
            subagents = project / CLAUDE_SESSION / "subagents"
            subagents.mkdir(parents=True)
            (subagents / "agent-one.jsonl").write_text("current subagent")

            artifact = root / "artifact"
            manifest = run_case.collect_agent_logs(
                trace, root / "checkout", {"CLAUDE_CONFIG_DIR": str(config)},
                "claude -p --output-format stream-json", artifact, started_at,
            )

            self.assertEqual({"provider": "claude", "status": "copied", "copiedFiles": 3},
                             manifest)
            self.assertEqual("current session", (artifact / "claude" / "session.jsonl").read_text())
            self.assertEqual("current debug", (artifact / "claude" / "debug.txt").read_text())
            self.assertEqual("current subagent",
                             (artifact / "claude" / "subagents" / "agent-one.jsonl").read_text())
            self.assertEqual(4, len([p for p in artifact.rglob("*") if p.is_file()]))

    def test_codex_copies_only_matching_rollout_not_global_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            config = root / ".codex"
            sessions = config / "sessions" / "2026" / "10" / "08"
            sessions.mkdir(parents=True)
            (config / "log").mkdir()
            trace = root / "trace.log"
            trace.write_text("--- output ---\n" + json.dumps({
                "type": "thread.started", "thread_id": CODEX_SESSION,
            }) + "\n")
            started_at = time.time()
            (sessions / f"rollout-2026-10-08T01-00-00-{CODEX_SESSION}.jsonl").write_text("current")
            (sessions / "rollout-2026-10-08T00-00-00-11111111-2222-3333-4444-555555555555.jsonl").write_text("other")
            (config / "log" / "codex-tui.log").write_text("shared log")
            (config / "auth.json").write_text("credential")

            artifact = root / "artifact"
            manifest = run_case.collect_agent_logs(
                trace, root / "checkout", {"CODEX_HOME": str(config)},
                "codex exec --json", artifact, started_at,
            )

            self.assertEqual({"provider": "codex", "status": "copied", "copiedFiles": 1},
                             manifest)
            self.assertEqual("current", (artifact / "codex" / "rollout.jsonl").read_text())
            self.assertEqual(2, len([p for p in artifact.rglob("*") if p.is_file()]))

    def test_missing_session_id_never_falls_back_to_home_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            config = root / ".claude"
            project = config / "projects" / "-checkout"
            project.mkdir(parents=True)
            (project / f"{CLAUDE_SESSION}.jsonl").write_text("old session")
            trace = root / "trace.log"
            trace.write_text("--- output ---\nstartup failed\n")

            artifact = root / "artifact"
            manifest = run_case.collect_agent_logs(
                trace, root / "checkout", {"CLAUDE_CONFIG_DIR": str(config)},
                "claude -p", artifact, time.time(),
            )

            self.assertEqual("no-session-id", manifest["status"])
            self.assertEqual(0, manifest["copiedFiles"])
            self.assertEqual([artifact / "manifest.json"], list(artifact.rglob("*.json")))

    def test_claude_init_id_takes_priority_over_result_id(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace.log"
            trace.write_text("--- output ---\n" + "\n".join(json.dumps(event) for event in (
                {"type": "system", "subtype": "init", "session_id": CLAUDE_SESSION},
                {"type": "result", "session_id": CODEX_SESSION},
            )) + "\n")

            self.assertEqual(CLAUDE_SESSION,
                             run_case.agent_log_session_id(trace, "claude"))

    def test_stale_session_file_is_not_published_even_if_id_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            config = root / ".claude"
            project = config / "projects" / "-checkout"
            project.mkdir(parents=True)
            session = project / f"{CLAUDE_SESSION}.jsonl"
            session.write_text("stale")
            old = time.time() - 60
            run_case.os.utime(session, (old, old))
            trace = root / "trace.log"
            trace.write_text("--- output ---\n" + json.dumps({
                "type": "system", "subtype": "init", "session_id": CLAUDE_SESSION,
            }) + "\n")

            artifact = root / "artifact"
            manifest = run_case.collect_agent_logs(
                trace, root / "checkout", {"CLAUDE_CONFIG_DIR": str(config)},
                "claude -p", artifact, time.time(),
            )

            self.assertEqual(0, manifest["copiedFiles"])
            self.assertFalse((artifact / "claude" / "session.jsonl").exists())

    def test_symlinked_session_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            config = root / ".claude"
            project = config / "projects" / "-checkout"
            project.mkdir(parents=True)
            secret = root / "secret.txt"
            secret.write_text("credential")
            (project / f"{CLAUDE_SESSION}.jsonl").symlink_to(secret)
            trace = root / "trace.log"
            trace.write_text("--- output ---\n" + json.dumps({
                "type": "system", "subtype": "init", "session_id": CLAUDE_SESSION,
            }) + "\n")

            artifact = root / "artifact"
            manifest = run_case.collect_agent_logs(
                trace, root / "checkout", {"CLAUDE_CONFIG_DIR": str(config)},
                "claude -p", artifact, time.time(),
            )

            self.assertEqual(0, manifest["copiedFiles"])
            self.assertFalse((artifact / "claude" / "session.jsonl").exists())

    def test_timeout_collects_at_run_end_without_exposing_artifact_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            case = root / "case.json"
            case.write_text(json.dumps({
                "id": "log-timeout", "kind": "first-green-build", "status": "draft",
                "prompt": "create a build", "repository": {"defaultBranch": "main"},
            }))
            bridge = mock.MagicMock()
            bridge.__enter__.return_value.agent_environment.return_value = {}
            env = {
                "TEAMCITY_URL": "https://teamcity.example",
                "TEAMCITY_TOKEN": "private-token",
                "EVAL_AGENT_LOG_ARTIFACT_DIR": str(root / "artifact"),
            }
            with mock.patch.dict(run_case.os.environ, env, clear=True), \
                    mock.patch.object(run_case.shutil, "which", return_value="teamcity"), \
                    mock.patch.object(run_case, "TeamCity") as teamcity, \
                    mock.patch.object(run_case, "TeamCityCliBridge", return_value=bridge), \
                    mock.patch.object(run_case, "checkout_repository"), \
                    mock.patch.object(run_case, "invoke_agent", return_value={
                        "exitCode": 124, "timedOut": True, "timeoutSeconds": 7,
                    }) as invoked, \
                    mock.patch.object(run_case, "agent_usage", return_value={}), \
                    mock.patch.object(run_case, "trace_error_category", return_value=None), \
                    mock.patch.object(run_case, "permission_failure_surface", return_value=None), \
                    mock.patch.object(run_case, "agent_tool_summary", return_value={}), \
                    mock.patch.object(run_case, "wait_for_build",
                                      side_effect=run_case.NoBuildQueued("none")), \
                    mock.patch.object(run_case, "collect_agent_logs") as collect:
                teamcity.return_value.create_project.return_value = "temporary-project"
                result = run_case.run(case, False, False, "baseline", "cli-only")

            self.assertTrue(result["agentTimedOut"])
            self.assertEqual(1, collect.call_count)
            self.assertNotIn("EVAL_AGENT_LOG_ARTIFACT_DIR", invoked.call_args.args[2])
            self.assertNotIn("EVAL_AGENT_LOG_ARTIFACT_DIR", collect.call_args.args[2])

    def test_both_teamcity_eval_jobs_publish_the_log_artifact(self):
        repository = EVALS.parent
        artifact_rule = "path: .teamcity/evaluation-agent-logs/**"
        for pipeline in ("eval-runner.yml", "config-eval-runner.yml"):
            with self.subTest(pipeline=pipeline):
                self.assertIn(artifact_rule,
                              (repository / ".teamcity" / pipeline).read_text())
        self.assertIn("export EVAL_AGENT_LOG_ARTIFACT_DIR=",
                      (EVALS / "run-eval-case.sh").read_text())


if __name__ == "__main__":
    unittest.main()
