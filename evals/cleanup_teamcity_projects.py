#!/usr/bin/env python3
"""Archive and later delete expired TeamCity eval projects with guardrails.

Dry-run is the default and can use the authenticated TeamCity CLI/keyring. Any
mutation requires the REST token supplied by the cleanup pipeline, ``--apply``,
and an exact repeated parent-project confirmation.
"""

import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse

from run_case import EvalError, TeamCity


UTC = datetime.timezone.utc
EVAL_NAME = re.compile(
    r"^eval-(?:skill|baseline)-[a-z0-9][a-z0-9-]*-"
    r"(?P<stamp>\d{8}-\d{6})-[0-9a-f]{6}$"
)
SELFCHECK_NAME = re.compile(r"^selfcheck-[0-9a-f]{8}$")
MARKER_TEMPORARY = "teamcity.eval.temporary"
MARKER_CREATED = "teamcity.eval.createdAt"
MARKER_EXPIRES = "teamcity.eval.expiresAt"
MARKER_ARCHIVED = "teamcity.eval.archivedAt"


def parse_iso(value):
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def timestamp_from_name(name):
    match = EVAL_NAME.fullmatch(name)
    if not match:
        return None
    return datetime.datetime.strptime(match.group("stamp"), "%Y%m%d-%H%M%S").replace(
        tzinfo=UTC
    )


def strict_temporary_name(name):
    return bool(EVAL_NAME.fullmatch(name) or SELFCHECK_NAME.fullmatch(name))


class CliReader:
    """Read-only fallback that uses the CLI's authenticated keyring session."""

    def __init__(self, server):
        self.server = server

    def call(self, *args, no_build_types_is_empty=False):
        env = dict(os.environ)
        env["TEAMCITY_URL"] = self.server
        completed = subprocess.run(
            ["teamcity", *args], capture_output=True, text=True, env=env
        )
        if completed.returncode:
            if no_build_types_is_empty:
                try:
                    error = json.loads(completed.stdout or completed.stderr).get(
                        "error", {}
                    )
                except json.JSONDecodeError:
                    error = {}
                if (
                    error.get("code") == "not_found"
                    and str(error.get("message", "")).startswith(
                        "No build types found under the affected project "
                    )
                ):
                    return {"build": []}
            raise RuntimeError(f"teamcity {' '.join(args[:2])} failed")
        return json.loads(completed.stdout)

    def projects(self, parent):
        found = self.call(
            "project", "list", "--parent", parent, "--limit", "0",
            "--json=id,name,parentProjectId,webUrl",
        )
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "parentProjectId": item.get("parentProjectId"),
                "archived": False,
                "markers": {},
            }
            for item in found.get("project", [])
        ]

    def has_active_builds(self, project_id):
        found = self.call(
            "run", "list", "--project", project_id, "--limit", "0",
            "--json=id,state",
            no_build_types_is_empty=True,
        )
        return any(
            build.get("state") in ("queued", "running")
            for build in found.get("build", [])
        )


class RestManager:
    def __init__(self, server, token):
        self.tc = TeamCity(server, token)

    @staticmethod
    def project_path(project_id):
        return f"/app/rest/projects/id:{urllib.parse.quote(project_id, safe='')}"

    @staticmethod
    def as_bool(value):
        if isinstance(value, bool):
            return value
        return str(value).lower() == "true"

    def projects(self, parent):
        collected = {}
        for archived in ("false", "true"):
            locator = urllib.parse.quote(
                f"parentProject:(id:{parent}),archived:{archived},count:10000", safe=""
            )
            found = self.tc.request(
                f"/app/rest/projects?locator={locator}"
                "&fields=project(id,name,parentProjectId,archived,webUrl)"
            )
            for item in (found or {}).get("project", []):
                collected[item["id"]] = {
                    "id": item["id"],
                    "name": item["name"],
                    "parentProjectId": item.get("parentProjectId"),
                    "archived": self.as_bool(item.get("archived", False)),
                    "markers": self.markers(item["id"]),
                }
        return list(collected.values())

    def markers(self, project_id):
        found = self.tc.request(
            self.project_path(project_id)
            + "/parameters?fields=property(name,value,own)"
        )
        markers = {}
        for item in (found or {}).get("property", []):
            name = item.get("name", "")
            # Never trust a lifecycle marker inherited from an ancestor.
            if name.startswith("teamcity.eval.") and item.get("own") is True:
                markers[name] = item.get("value", "")
        return markers

    def has_active_builds(self, project_id):
        project = urllib.parse.quote(project_id, safe="")
        queue_locator = urllib.parse.quote(
            f"affectedProject:(id:{project_id}),count:1", safe=""
        )
        queued = self.tc.request(
            f"/app/rest/buildQueue?locator={queue_locator}&fields=count"
        )
        running_locator = urllib.parse.quote(
            f"affectedProject:(id:{project_id}),running:true,defaultFilter:false,count:1",
            safe="",
        )
        running = self.tc.request(
            f"/app/rest/builds?locator={running_locator}&fields=count"
        )
        return bool((queued or {}).get("count", 0) or (running or {}).get("count", 0))

    def refresh(self, project_id):
        try:
            item = self.tc.request(
                self.project_path(project_id)
                + "?fields=id,name,parentProjectId,archived"
            )
        except EvalError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise
        return item

    def archive(self, project_id, archived_at):
        self.tc.set_project_parameter(project_id, MARKER_ARCHIVED, archived_at.isoformat())
        self.tc.set_project_archived(project_id, True)

    def delete_once_and_verify(self, project_id):
        error = None
        try:
            self.tc.delete_project(project_id)
        except Exception as exc:  # timeout may mean TeamCity accepted the delete
            error = type(exc).__name__
        still_exists = self.refresh(project_id)
        if still_exists is None:
            return True, "deleted" if error is None else f"deleted-after-{error}"
        return False, "delete-returned-but-project-still-exists" if error is None else error


def project_age_source(project, now, ttl):
    markers = project["markers"]
    marker = markers.get(MARKER_TEMPORARY)
    if marker is not None:
        if marker.lower() != "true":
            return None, None, "temporary-marker-not-true"
        created = parse_iso(markers.get(MARKER_CREATED))
        expires = parse_iso(markers.get(MARKER_EXPIRES))
        if created is None or expires is None:
            return None, None, "invalid-lifecycle-marker"
    else:
        created = timestamp_from_name(project["name"])
        expires = None
    if created is None:
        return None, None, "age-unknown"
    eligible_at = max(created + ttl, expires) if expires else created + ttl
    return created, eligible_at, None


def classify_projects(projects, backend, parent, mode, ttl, delete_grace, now, apply):
    records = []
    for project in sorted(projects, key=lambda item: item["name"]):
        record = {
            "id": project["id"],
            "name": project["name"],
            "archived": project["archived"],
            "status": "skipped",
            "reason": "",
        }
        records.append(record)

        if project.get("parentProjectId") != parent:
            record["reason"] = "not-a-direct-child"
            continue
        if not strict_temporary_name(project["name"]):
            record["reason"] = "name-not-allowed"
            continue

        created, eligible_at, age_error = project_age_source(project, now, ttl)
        if age_error:
            record["reason"] = age_error
            continue
        record["ageHours"] = round((now - created).total_seconds() / 3600, 2)
        if now < eligible_at:
            record["reason"] = "younger-than-ttl"
            continue

        try:
            if backend.has_active_builds(project["id"]):
                record["reason"] = "queued-or-running-build"
                continue
        except Exception:
            record["reason"] = "active-state-unknown"
            continue

        if not project["archived"]:
            if mode == "delete":
                record["reason"] = "not-archived"
                continue
            if not apply:
                record.update(status="candidate", reason="eligible-for-archive")
                continue
            current = backend.refresh(project["id"])
            if (not current or current.get("parentProjectId") != parent
                    or current.get("name") != project["name"]
                    or not strict_temporary_name(current.get("name", ""))):
                record.update(status="failed", reason="identity-guard-changed")
                continue
            try:
                backend.archive(project["id"], now)
                record.update(status="archived", reason="archived-and-marked")
            except Exception as exc:
                record.update(status="failed", reason=type(exc).__name__)
            continue

        archived_at = parse_iso(project["markers"].get(MARKER_ARCHIVED))
        if archived_at is None:
            record["reason"] = "archive-age-unknown"
            continue
        record["archivedHours"] = round((now - archived_at).total_seconds() / 3600, 2)
        if now < archived_at + delete_grace:
            record["reason"] = "within-delete-grace"
            continue
        if mode != "delete":
            record.update(status="candidate", reason="eligible-for-delete")
            continue
        if not apply:
            record.update(status="candidate", reason="eligible-for-delete")
            continue

        current = backend.refresh(project["id"])
        if (not current or current.get("parentProjectId") != parent
                or current.get("name") != project["name"]
                or not current.get("archived")
                or not strict_temporary_name(current.get("name", ""))):
            record.update(status="failed", reason="identity-guard-changed")
            continue
        try:
            deleted, reason = backend.delete_once_and_verify(project["id"])
            record.update(status="deleted" if deleted else "failed", reason=reason)
        except Exception as exc:
            record.update(status="failed", reason=type(exc).__name__)
    return records


def public_cleanup_record(record):
    """Strip the internal TeamCity object ID from the published report."""
    return {name: value for name, value in record.items() if name != "id"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default=os.environ.get("TEAMCITY_URL"))
    parser.add_argument(
        "--parent-project", default=os.environ.get("EVAL_PARENT_PROJECT"), required=False
    )
    parser.add_argument("--mode", choices=("dry-run", "archive", "delete"), default="dry-run")
    parser.add_argument("--ttl-hours", type=float, default=6)
    parser.add_argument("--delete-grace-hours", type=float, default=24)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-parent")
    parser.add_argument("--report", type=pathlib.Path, default=pathlib.Path("cleanup-report.json"))
    args = parser.parse_args()

    if not args.server or not args.parent_project:
        parser.error("--server and --parent-project (or their environment variables) are required")
    if args.mode == "dry-run" and args.apply:
        parser.error("--apply is invalid in dry-run mode")
    if args.mode != "dry-run" and (
        not args.apply or args.confirm_parent != args.parent_project
    ):
        parser.error(
            "archive/delete requires --apply and --confirm-parent equal to --parent-project"
        )

    token = os.environ.get("TEAMCITY_TOKEN")
    if args.mode != "dry-run" and not token:
        parser.error("TEAMCITY_TOKEN is required for archive/delete")
    backend = RestManager(args.server, token) if token else CliReader(args.server)
    if args.mode != "dry-run" and not isinstance(backend, RestManager):
        parser.error("archive/delete requires the REST manager")

    now = datetime.datetime.now(UTC)
    projects = backend.projects(args.parent_project)
    records = classify_projects(
        projects,
        backend,
        args.parent_project,
        args.mode,
        datetime.timedelta(hours=args.ttl_hours),
        datetime.timedelta(hours=args.delete_grace_hours),
        now,
        args.apply,
    )
    counts = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    report = {
        "server": args.server,
        "parentProject": args.parent_project,
        "mode": args.mode,
        "apply": args.apply,
        "generatedAt": now.isoformat(),
        "ttlHours": args.ttl_hours,
        "deleteGraceHours": args.delete_grace_hours,
        "summary": counts,
        "projects": [public_cleanup_record(record) for record in records],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"summary": counts, "report": str(args.report)}, indent=2))
    for record in records:
        if record["status"] != "skipped":
            print(f"{record['status']:9} {record['name']} ({record['reason']})")
    return 1 if counts.get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
