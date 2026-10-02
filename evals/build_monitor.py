"""Read-only, source-bound checkpoints while a paid first-green agent runs.

Only fixed categories, counts and build IDs leave this module. No logs, traces,
parameters, tests, project mutations, build cancellations or retries are used.
"""

import json
import pathlib
import sys
import time

from first_green_evidence import (
    EvidenceError, chain_nodes, pipeline_signature, select_pipeline,
    safe_terminal_chain_diagnostics, terminal_chain_diagnostics,
)


STOP_CATEGORY = "verification-unexplained-head-failure"


def safe_monitor_diagnostics(value):
    if not isinstance(value, dict):
        return {}
    safe = {key: value[key] for key in ("checkCount", "readFailureCount", "intervalSeconds")
            if type(value.get(key)) is int and value[key] >= 0}
    if type(value.get("stoppedAgent")) is bool:
        safe["stoppedAgent"] = value["stoppedAgent"]
    if value.get("state") in ("waiting-for-source", "waiting-for-pipeline", "waiting-for-build",
                              "observed", "read-unavailable", "intervened"):
        safe["state"] = value["state"]
    chain = safe_terminal_chain_diagnostics(value.get("lastChain"))
    if chain:
        safe["lastChain"] = chain
    return safe


class LiveBuildMonitor:
    interval_seconds = 60
    read_budget_seconds = 15

    def __init__(self, tc, project_id, checkout, source_path, clock=time.monotonic):
        self.tc = tc  # Dedicated CLI reader with a short command timeout.
        self.project_id = project_id
        self.checkout = pathlib.Path(checkout).resolve()
        self.source_path = source_path
        self.clock = clock
        self.data = {"checkCount": 0, "readFailureCount": 0, "stoppedAgent": False,
                     "intervalSeconds": self.interval_seconds, "state": "waiting-for-source"}
        self.last_emitted = None

    def source(self):
        import yaml
        if not isinstance(self.source_path, str) or not self.source_path:
            return None
        path = (self.checkout / self.source_path).resolve()
        if self.checkout not in path.parents or not path.is_file():
            return None
        try:
            document = yaml.safe_load(path.read_text())
        except (OSError, yaml.YAMLError):
            return None  # The agent may be in the middle of writing the file.
        return document if isinstance(document, dict) and document.get("jobs") else None

    def diagnostics(self):
        return safe_monitor_diagnostics(self.data)

    def checkpoint(self, agent_deadline):
        self.data["checkCount"] += 1
        self.tc.deadline = min(agent_deadline, self.clock() + self.read_budget_seconds)
        try:
            return self._inspect()
        except (RuntimeError, OSError, ValueError, KeyError, TypeError, ImportError):
            # Never publish exception/CLI text. A broken reader must be visible,
            # but cannot justify terminating an otherwise healthy agent.
            self.data["readFailureCount"] += 1
            self.data["state"] = "read-unavailable"
            if self.last_emitted != "read-unavailable":
                print("[eval-build-monitor] read-unavailable; no stop inferred",
                      file=sys.stderr, flush=True)
                self.last_emitted = "read-unavailable"
            return None

    def _inspect(self):
        source = self.source()
        if source is None:
            self.data["state"] = "waiting-for-source"
            return None
        definitions = {key: self.tc.pipeline_definition(key)
                       for key in self.tc.pipeline_ids(self.project_id)}
        try:
            pipeline, _ = select_pipeline(definitions, source)
        except EvidenceError:
            self.data["state"] = "waiting-for-pipeline"
            return None
        candidates = [item for item in self.tc.builds(self.project_id, pipeline)
                      if item.get("buildTypeId") == pipeline]
        if not candidates:
            self.data["state"] = "waiting-for-build"
            return None
        head_id = max(item["id"] for item in candidates)
        nodes = chain_nodes(self.tc.build_tree(head_id), head_id, pipeline)
        snapshot = terminal_chain_diagnostics(nodes, head_id)
        if snapshot["requiresInvestigation"]:
            metadata = self.tc.build(head_id)
            head = next(node for node in nodes if node["id"] == head_id)
            if any(metadata.get(k) != head[k] for k in ("id", "buildTypeId", "state", "status")):
                raise EvidenceError("verification-chain-incomplete")
            snapshot = terminal_chain_diagnostics(nodes, head_id, metadata)
        self.data.update(state="observed", lastChain=snapshot)
        # State-change output contains no free-form TeamCity text or source.
        encoded = json.dumps(snapshot, sort_keys=True)
        if encoded != self.last_emitted:
            print("[eval-build-monitor] " + encoded, file=sys.stderr, flush=True)
            self.last_emitted = encoded
        if not snapshot["requiresInvestigation"] or snapshot["problemEvidence"] != "unavailable":
            return None
        # Do not stop on a stale definition or when a newer attempt already exists.
        latest = self.tc.builds(self.project_id, pipeline)
        if any(item.get("buildTypeId") == pipeline and item["id"] > head_id for item in latest):
            return None
        current_source = self.source()
        if (current_source is None
                or pipeline_signature(current_source) != pipeline_signature(source)
                or pipeline_signature(self.tc.pipeline_definition(pipeline)) != pipeline_signature(source)):
            return None
        return STOP_CATEGORY

    def mark_stopped(self):
        self.data.update(state="intervened", stoppedAgent=True)
