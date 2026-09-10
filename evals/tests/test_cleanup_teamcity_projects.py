import datetime
import importlib.util
import pathlib
import subprocess
import sys
import unittest
from unittest import mock


EVALS = pathlib.Path(__file__).resolve().parents[1]
if str(EVALS) not in sys.path:
    sys.path.insert(0, str(EVALS))


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cleanup = load_module("cleanup_teamcity_projects_test", "cleanup_teamcity_projects.py")
UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 9, 9, 12, tzinfo=UTC)
PARENT = "EvalSandbox"


def project(name, *, archived=False, markers=None, parent=PARENT):
    return {
        "id": f"id-{name}",
        "name": name,
        "parentProjectId": parent,
        "archived": archived,
        "markers": markers or {},
    }


class FakeBackend:
    def __init__(self, *, active=None, refreshed=None):
        self.active = set(active or [])
        self.refreshed = refreshed or {}
        self.archived = []
        self.deleted = []

    def has_active_builds(self, project_id):
        return project_id in self.active

    def refresh(self, project_id):
        return self.refreshed.get(project_id)

    def archive(self, project_id, archived_at):
        self.archived.append((project_id, archived_at))

    def delete_once_and_verify(self, project_id):
        self.deleted.append(project_id)
        return True, "deleted"


def classify(items, backend=None, *, mode="dry-run", apply=False):
    return cleanup.classify_projects(
        items,
        backend or FakeBackend(),
        PARENT,
        mode,
        datetime.timedelta(hours=6),
        datetime.timedelta(hours=24),
        NOW,
        apply,
    )


class CleanupTeamCityProjectsTest(unittest.TestCase):
    def test_strict_name_matching(self):
        self.assertTrue(
            cleanup.strict_temporary_name(
                "eval-skill-teamcity-cli-not-curl-20260908-204924-20739c"
            )
        )
        self.assertTrue(cleanup.strict_temporary_name("selfcheck-deadbeef"))
        for unsafe in (
            "eval-skill-anything",
            "eval-skill-case-20260908-204924-zzzzzz",
            "selfcheck-deadbeef-extra",
            "production-eval-skill-case-20260908-204924-20739c",
        ):
            self.assertFalse(cleanup.strict_temporary_name(unsafe), unsafe)

    def test_cli_treats_project_without_build_types_as_inactive(self):
        response = {
            "error": {
                "code": "not_found",
                "message": "No build types found under the affected project expired",
            }
        }
        completed = subprocess.CompletedProcess(
            [], 1, stdout="", stderr=cleanup.json.dumps(response)
        )
        reader = cleanup.CliReader("https://teamcity.example")

        with mock.patch.object(cleanup.subprocess, "run", return_value=completed):
            self.assertFalse(reader.has_active_builds("expired"))

    def test_lifecycle_marker_takes_precedence_over_old_name(self):
        item = project(
            "eval-skill-case-20200101-000000-abcdef",
            markers={
                cleanup.MARKER_TEMPORARY: "true",
                cleanup.MARKER_CREATED: "2026-09-09T10:00:00Z",
                cleanup.MARKER_EXPIRES: "2026-09-10T10:00:00Z",
            },
        )

        [record] = classify([item])

        self.assertEqual("skipped", record["status"])
        self.assertEqual("younger-than-ttl", record["reason"])

    def test_explicit_non_temporary_marker_is_never_overridden_by_name(self):
        item = project(
            "eval-skill-case-20200101-000000-abcdef",
            markers={cleanup.MARKER_TEMPORARY: "false"},
        )

        [record] = classify([item])

        self.assertEqual("temporary-marker-not-true", record["reason"])

    def test_invalid_lifecycle_marker_is_skipped(self):
        item = project(
            "eval-skill-case-20200101-000000-abcdef",
            markers={
                cleanup.MARKER_TEMPORARY: "true",
                cleanup.MARKER_CREATED: "not-a-date",
                cleanup.MARKER_EXPIRES: "2020-01-01T00:00:00Z",
            },
        )

        [record] = classify([item])

        self.assertEqual("invalid-lifecycle-marker", record["reason"])

    def test_active_young_and_unknown_age_projects_are_skipped(self):
        active = project("eval-skill-case-20260908-000000-abcdef")
        young = project("eval-skill-case-20260909-100000-abcdef")
        unknown = project("selfcheck-deadbeef")
        backend = FakeBackend(active={active["id"]})

        records = classify([active, young, unknown], backend)
        reasons = {record["name"]: record["reason"] for record in records}

        self.assertEqual("queued-or-running-build", reasons[active["name"]])
        self.assertEqual("younger-than-ttl", reasons[young["name"]])
        self.assertEqual("age-unknown", reasons[unknown["name"]])

    def test_expired_unarchived_project_is_archive_candidate(self):
        item = project("eval-baseline-case-20260908-000000-abcdef")

        [record] = classify([item])

        self.assertEqual("candidate", record["status"])
        self.assertEqual("eligible-for-archive", record["reason"])

    def test_archive_apply_rechecks_identity(self):
        item = project("eval-skill-case-20260908-000000-abcdef")
        changed = dict(item, name="production")
        backend = FakeBackend(refreshed={item["id"]: changed})

        [record] = classify([item], backend, mode="archive", apply=True)

        self.assertEqual("failed", record["status"])
        self.assertEqual("identity-guard-changed", record["reason"])
        self.assertEqual([], backend.archived)

    def test_archive_apply_marks_matching_project(self):
        item = project("eval-skill-case-20260908-000000-abcdef")
        backend = FakeBackend(refreshed={item["id"]: item})

        [record] = classify([item], backend, mode="archive", apply=True)

        self.assertEqual("archived", record["status"])
        self.assertEqual([item["id"]], [entry[0] for entry in backend.archived])

    def test_archived_project_must_wait_for_delete_grace(self):
        item = project(
            "eval-skill-case-20260908-000000-abcdef",
            archived=True,
            markers={cleanup.MARKER_ARCHIVED: "2026-09-09T00:00:00Z"},
        )

        [record] = classify([item], mode="delete", apply=False)

        self.assertEqual("within-delete-grace", record["reason"])

    def test_delete_apply_rechecks_archived_identity(self):
        item = project(
            "eval-skill-case-20260907-000000-abcdef",
            archived=True,
            markers={cleanup.MARKER_ARCHIVED: "2026-09-07T00:00:00Z"},
        )
        backend = FakeBackend(refreshed={item["id"]: item})

        [record] = classify([item], backend, mode="delete", apply=True)

        self.assertEqual("deleted", record["status"])
        self.assertEqual([item["id"]], backend.deleted)

    def test_delete_is_called_once_then_verified_even_after_timeout(self):
        class FakeTeamCity:
            def __init__(self):
                self.deletes = 0

            def delete_project(self, project_id):
                self.deletes += 1
                raise TimeoutError("response timed out")

        manager = cleanup.RestManager.__new__(cleanup.RestManager)
        manager.tc = FakeTeamCity()
        manager.refresh = lambda project_id: None

        deleted, reason = manager.delete_once_and_verify("expired-project")

        self.assertTrue(deleted)
        self.assertEqual("deleted-after-TimeoutError", reason)
        self.assertEqual(1, manager.tc.deletes)


if __name__ == "__main__":
    unittest.main()
