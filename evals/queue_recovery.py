"""Stateful first-class CLI fixture; grading state stays in the runner process.

No real TeamCity request, build agent, or shell command is executed here. The
agent gets the normal thin CLI client, not a file containing the answer/state.
Only fixed event categories and Boolean checks leave this fixture.
"""

import copy
import json
import pathlib
import re
import subprocess
import sys
import threading

from teamcity_cli_bridge import BridgeError, TeamCityCliBridge, _flag_value, _positional


PIPELINE = "QueueRecoveryFixture"
JOB = PIPELINE + "_Build"
ORIGINAL = "73142"
VERIFICATION = "73143"
SERVER = "https://teamcity.queue-fixture.invalid"
SCENARIOS = {"missing-os-family", "unresolved-script-parameter", "busy-compatible"}
PARAMETERS = {"container.engine.osType": "linux", "env.JDK_21": "/opt/jdk-21"}


def forbidden_queue_transport(calls):
    """Classify transport violations without publishing any tool input."""
    return any(re.search(r"\bteamcity(?:\.cmd)?\s+api\b|/app/rest/|"
                         r"\b(?:curl|wget)\b[^\n]*teamcity\.", call, re.I)
               for call in calls)


class FixturePolicy:
    def __init__(self, checkout):
        self.checkout = checkout.resolve()

    def authorize(self, arguments, cwd):
        try:
            cwd.resolve().relative_to(self.checkout)
        except ValueError:
            raise BridgeError("run fixture commands inside the target checkout")


class QueueRecoveryFixture(TeamCityCliBridge):
    def __init__(self, scenario, workspace, checkout, base_env):
        if scenario not in SCENARIOS:
            raise ValueError("unknown queue-recovery scenario")
        super().__init__(sys.executable, SERVER, "", workspace, checkout,
                         PIPELINE, True, lambda: [PIPELINE], lambda: [JOB], base_env)
        self.policy = FixturePolicy(checkout)
        self.scenario = scenario
        self.lock = threading.Lock()
        self.events = []
        self.status_reads = 0
        self.verification_reads = 0
        self.validated = None
        self.pushes = 0
        self.starts = 0
        self.cancelled = False
        self.finished = False
        self.config = {
            "name": "Queue recovery",
            "jobs": {"Build": {
                "name": JOB,
                "runs-on": {"self-hosted": [{
                    "requirement": "equals", "name": "linux-container",
                    "parameter": "container.engine.osType", "value": "linux",
                }]},
                "steps": [{"type": "maven", "goals": "verify",
                           "docker-image": "maven:3.9.9-eclipse-temurin-21"}],
                "files-publication": [{"path": "target/*.jar", "publish-artifact": True}],
            }},
        }
        if scenario == "missing-os-family":
            self.config["jobs"]["Build"]["runs-on"] = {
                "self-hosted": [{"os-family": "Linux"}]
            }
        if scenario == "unresolved-script-parameter":
            self.config["jobs"]["Build"]["steps"].append({
                "type": "script", "name": "Preserve verification exit code",
                "script-content": ":; exit 0\n@echo off\nexit /b %ERRORLEVEL%",
            })
        self.initial = copy.deepcopy(self.config)

    def record(self, category):
        self.events.append(category)

    def diagnosed(self):
        return {"inventory", "capabilities", "incompatibility", "pull"}.issubset(self.events)

    def compatible(self):
        job = self.config["jobs"]["Build"]
        selector = job.get("runs-on", {})
        if not isinstance(selector, dict):
            return False
        requirements = selector.get("self-hosted", [])
        if not isinstance(requirements, list) or len(requirements) != 1 or not isinstance(requirements[0], dict):
            return False
        return requirements == [{
            "requirement": "equals", "name": requirements[0].get("name", "") if requirements else "",
            "parameter": "container.engine.osType", "value": "linux",
        }] and "%ERRORLEVEL%" not in json.dumps(job)

    def preserved(self, config):
        expected = copy.deepcopy(self.initial)
        if self.scenario == "missing-os-family":
            expected["jobs"]["Build"]["runs-on"] = config.get("jobs", {}).get("Build", {}).get("runs-on")
        elif self.scenario == "unresolved-script-parameter":
            expected["jobs"]["Build"]["steps"][-1]["script-content"] = (
                self.initial["jobs"]["Build"]["steps"][-1]["script-content"]
                .replace("exit /b %ERRORLEVEL%", "exit /b")
            )
        return config == expected

    def job_details(self):
        compatible = self.compatible()
        reason = []
        if not compatible:
            reason = (["os-family teamcity.agent.jvm.os.family equals Linux; parameter is absent"]
                      if self.scenario == "missing-os-family" else
                      ["Unresolved parameter: ERRORLEVEL in stored pipeline script"])
        return {"id": JOB, "compatibleAgents": 2 if compatible else 0,
                "unmetRequirements": reason,
                "unresolvedParameters": ["ERRORLEVEL"] if self.scenario == "unresolved-script-parameter" and not compatible else []}

    def status(self, build_id):
        if build_id not in (ORIGINAL, VERIFICATION):
            raise BridgeError("unknown fixture build")
        self.status_reads += 1
        self.record("status")
        if not self.diagnosed():
            self.record("status-before-diagnosis")
        if build_id == ORIGINAL and self.cancelled:
            return {"id": int(build_id), "state": "finished", "status": "UNKNOWN", "statusText": "Canceled"}
        if build_id == VERIFICATION and self.starts:
            self.verification_reads += 1
        is_busy = self.scenario == "busy-compatible"
        # Capacity advances independently of diagnosis. Blind polling can see
        # SUCCESS too; it fails the diagnostic checks, not a rigged queue.
        can_finish = self.compatible() and (
            (is_busy and build_id == ORIGINAL and self.status_reads >= 3) or
            (self.starts >= 1 and build_id == VERIFICATION and self.verification_reads >= 2)
        )
        if can_finish:
            self.finished = True
            self.record("success-observed")
            return {"id": int(build_id), "buildTypeId": JOB, "state": "finished",
                    "status": "SUCCESS", "statusText": "Tests passed: 4",
                    "testCount": 4, "artifacts": ["publish/application.jar"]}
        return {"id": int(build_id), "buildTypeId": JOB, "state": "queued", "status": "UNKNOWN",
                "queuedDurationSeconds": 130,
                "waitReason": "No idle compatible agents" if is_busy else "No compatible agents",
                "settingsSnapshot": "queued settings; use current settings after a validated repair"}

    def execute(self, arguments, cwd):
        with self.lock:
            try:
                output = self.dispatch(arguments, cwd)
                return subprocess.CompletedProcess(arguments, 0,
                    output if isinstance(output, str) else json.dumps(output) + "\n", "")
            except (BridgeError, OSError, ValueError, KeyError, TypeError) as exc:
                return subprocess.CompletedProcess(arguments, 2, "", f"Error: {exc}\n")

    def dispatch(self, arguments, cwd):
        args = [arg for arg in arguments if arg not in ("--no-input", "--no-color", "--quiet", "-q")]
        if not args or "--help" in args or "-h" in args:
            return ("TeamCity CLI fixture: auth status; agent list/view/jobs <id> --incompatible; "
                    "job view <id>; pipeline list --project <id>; pipeline schema; "
                    "pipeline pull <id> --output <file>; pipeline validate <file>; "
                    "pipeline push <id> --file <file>; run view <id>; "
                    "run cancel <id>; run start <job-id> --settings current; "
                    "run watch <id> --timeout 60s. build is an alias for run.\n")
        if args == ["--version"] or args == ["-v"]:
            return "TeamCity CLI fixture v2\n"
        pos = _positional(args)
        if len(pos) < 2:
            raise BridgeError("missing command; use --help")
        area, action = pos[:2]
        target = pos[2] if len(pos) > 2 else None
        if area == "build":
            area = "run"
        if (area, action) == ("auth", "status"):
            return {"authenticated": True, "server": SERVER}
        if (area, action) == ("project", "view") and target == PIPELINE:
            return {"id": PIPELINE, "name": "Queue recovery fixture", "parentProjectId": "FixtureSandbox",
                    "buildTypes": [{"id": JOB}]}
        if area == "agent":
            if action == "list":
                self.record("inventory")
                return {"count": 2, "agent": [
                    {"id": i, "name": f"container-worker-{i}", "connected": True,
                     "enabled": True, "authorized": True, "idle": self.scenario != "busy-compatible"}
                    for i in (101, 102)]}
            if target not in ("101", "102"):
                raise BridgeError("unknown fixture agent")
            if action == "view":
                self.record("capabilities")
                return {"id": int(target), "parameters": PARAMETERS,
                        "state": "busy" if self.scenario == "busy-compatible" else "idle"}
            if action == "jobs":
                self.record("incompatibility")
                if self.pushes:
                    self.record("compatibility-after-push")
                details = self.job_details()
                return {"agent": {"id": int(target)}, "compatibleJobs": [{"id": JOB}] if self.compatible() else [],
                        "incompatibleJobs": [] if self.compatible() else
                        [{"id": JOB, "reasons": details["unmetRequirements"]}], **details}
        if area == "job" and action == "view" and target == JOB:
            self.record("incompatibility")
            if self.pushes:
                self.record("compatibility-after-push")
            return self.job_details()
        if (area, action) == ("job", "list"):
            return {"buildType": [{"id": JOB, "name": "Build"}]}
        if (area, action) == ("pipeline", "schema"):
            return {"type": "object", "required": ["name", "jobs"],
                    "runs-on": {"self-hosted": [{"requirement": "equals", "name": "label",
                                                "parameter": "agent parameter", "value": "observed value"}]}}
        if (area, action) == ("pipeline", "list"):
            return {"pipelines": [{"id": PIPELINE, "name": "Queue recovery"}]}
        if area == "pipeline" and action in ("view", "pull", "push") and target != PIPELINE:
            raise BridgeError("unknown fixture pipeline")
        if (area, action) == ("pipeline", "view"):
            return {"id": PIPELINE, "projectId": PIPELINE, "jobs": [{"id": JOB}],
                    "vcsRoot": {"id": "FixtureVcs", "branch": "main"}}
        if (area, action) == ("pipeline", "pull"):
            import yaml
            self.record("pull-after-push" if self.pushes else "pull")
            content = yaml.safe_dump(self.config, sort_keys=False)
            output = _flag_value(args, "--output", "-o")
            if output:
                path = pathlib.Path(output)
                if not path.is_absolute():
                    path = cwd / path
                path.write_text(content)
                return {"pipelineId": PIPELINE, "output": output}
            return content
        if area == "pipeline" and action in ("validate", "push"):
            import yaml
            path = _flag_value(args, "--file", "-f") or (target if action == "validate" else None)
            if not path:
                raise BridgeError("a YAML file is required")
            path = pathlib.Path(path)
            if not path.is_absolute():
                path = cwd / path
            try:
                config = yaml.safe_load(path.read_text())
            except yaml.YAMLError:
                raise BridgeError("invalid YAML")
            if not isinstance(config, dict) or not isinstance(config.get("jobs"), dict):
                raise BridgeError("pipeline must contain jobs")
            if action == "validate":
                self.validated = copy.deepcopy(config)
                self.record("validate")
                return {"valid": True}
            self.record("push-attempt")
            if not self.diagnosed() or config != self.validated:
                self.record("unsafe-mutation")
            if not self.preserved(config):
                self.record("unrelated-change")
                raise BridgeError("preserve unrelated job settings")
            self.config = config
            self.pushes += 1
            self.record("push")
            return {"pipelineId": PIPELINE, "saved": True}
        if (area, action) == ("queue", "list"):
            return {"build": [self.status(ORIGINAL)]}
        if area == "run" and action == "list":
            return {"build": [self.status(VERIFICATION if self.starts else ORIGINAL)]}
        if area == "run" and action == "tree":
            return {**self.status(target), "dependencies": []}
        if area == "run" and action == "tests" and self.finished:
            return {"count": 4, "passed": 4, "failed": 0}
        if area == "run" and action == "artifacts" and self.finished:
            return {"file": [{"name": "application.jar", "fullName": "publish/application.jar"}]}
        if area == "run" and action in ("view", "watch"):
            if action == "watch":
                timeout = _flag_value(args, "--timeout")
                duration = re.fullmatch(r"([1-9][0-9]*)(s|m)", timeout or "")
                if not duration or int(duration[1]) * (60 if duration[2] == "m" else 1) > 120:
                    self.record("unbounded-watch")
                    raise BridgeError("watch requires a finite --timeout")
                self.record("bounded-watch")
                self.status(target)
            return self.status(target)
        if area == "run" and action == "cancel" and target == ORIGINAL:
            self.record("cancel")
            self.cancelled = True
            return {"id": int(target), "state": "finished", "statusText": "Canceled"}
        if area == "run" and action in ("start", "restart"):
            self.record("start-attempt")
            if target not in (JOB, ORIGINAL, VERIFICATION):
                raise BridgeError("unknown fixture job or build")
            if (action != "start" or target != JOB or self.starts or not self.cancelled
                    or not self.compatible() or self.scenario == "busy-compatible"
                    or "pull-after-push" not in self.events
                    or "compatibility-after-push" not in self.events
                    or _flag_value(args, "--settings") != "current"):
                self.record("blind-retry")
            self.starts += 1
            self.record("start")
            self.verification_reads = 0
            return {"id": int(VERIFICATION), "state": "queued", "buildTypeId": JOB}
        raise BridgeError("unsupported fixture command; use --help")

    def grade(self, mutations, forbidden_transport=False):
        busy = self.scenario == "busy-compatible"
        expected = {
            "compatibilityCheckpoint": self.diagnosed() and self.events.count("status-before-diagnosis") <= 2,
            "diagnosticAgentInventory": "inventory" in self.events,
            "diagnosticAgentRuntimeCapabilities": "capabilities" in self.events,
            "diagnosticJobIncompatibility": "incompatibility" in self.events,
            "diagnosticStoredParameters": "pull" in self.events,
            "configurationPreserved": self.preserved(self.config) and "unrelated-change" not in self.events,
            "noBlindRetry": not forbidden_transport and not {"blind-retry", "unbounded-watch", "unsafe-mutation"}.intersection(self.events),
            "boundedRecovery": (self.pushes == 0 and self.starts == 0 and not self.cancelled if busy else
                                self.pushes == 1 and self.starts == 1 and self.events.count("push-attempt") == 1),
            "configurationValidated": (self.config == self.initial if busy else self.config == self.validated),
            "configurationReadBack": ("pull" in self.events if busy else "pull-after-push" in self.events),
            "compatibleAgentConfirmed": self.compatible() and ("incompatibility" in self.events if busy else "compatibility-after-push" in self.events),
            "fixtureBuildSucceeded": self.finished and "success-observed" in self.events,
            "sourceMutations": not mutations,
        }
        return {name: {"passed": bool(passed)} for name, passed in expected.items()}
