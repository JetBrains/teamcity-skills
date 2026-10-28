"""Pinned Clean Spring requirements, tested without builds or XML downloads."""

import copy
import importlib.util
import json
import pathlib
import sys
import unittest
from unittest import mock


EVALS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))
from maven_version import maven_version, maven_versions_match, observe_maven_versions

spec = importlib.util.spec_from_file_location("clean_spring_runner", EVALS / "run_case.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

CASE = json.loads((EVALS / "first-green-build/cases/clean-spring-boot-maven.json").read_text())
CONFIG = json.loads((EVALS / "pipeline-configuration/cases/clean-spring-boot-maven-pipeline.json").read_text())
CLASSES = {
    "CleanSpringBootProjectApplicationTests": 1,
    "api.controllers.ProductControllerTest": 12,
    "api.services.ProductServiceTest": 6,
    "auth.controllers.AuthenticationControllerTest": 4,
    "auth.repositories.UserRepositoryTest": 8,
    "auth.services.AuthenticationServiceTest": 8,
}
PREFIX = "com.kawser.cleanspringbootproject."
MAIN = "org.codehaus.plexus.classworlds.launcher.Launcher"


def step(kind="maven", **properties):
    return {"type": kind, "properties": properties}


def job(steps=None):
    return {"id": "pipeline/Verify", "name": "Verify", "agentRequirements": [],
            "parameters": {"env.JAVA_HOME": "%env.JDK_21_0%"},
            "steps": steps or [step(goals="clean verify", **{"runner-arguments": "-V"})],
            "artifactRules": "target/*.jar\ntarget/surefire-reports/*.xml"}


def log(version="3.9.11", index=1, total=1, command=None):
    command = command or f"/jdk-21/bin/java {MAIN} -V -B clean verify"
    return (f"[12:34:56] : [Step {index}/{total}] Starting: {command}\n"
            f"[12:34:56] : [Step {index}/{total}] Apache Maven {version} (release-hash)\n")


def observed():
    configured = job()
    tests = [{"name": PREFIX + name + f".method{i}", "status": "SUCCESS", "ignored": False}
             for name, count in CLASSES.items() for i in range(count)]
    version = {**maven_version(log(), configured, "3.6"), "jobId": configured["id"]}
    return {"jobs": [configured], "tests": tests, "testCount": len(tests),
            "mavenVersions": [version], "properties": {}, "mutations": [],
            "buildTypeCount": 2, "buildStatus": "SUCCESS", "attempts": 1,
            "artifacts": ["app.jar"] + [f"TEST-{PREFIX}{name}.xml" for name in CLASSES]}


class CleanSpringContractTest(unittest.TestCase):
    def test_complete_verification_passes_repository_checks(self):
        checks = runner.grade(CASE, observed())
        for name in ("requiredTests", "allTestsPassed", "mavenVersion",
                     "artifactsPublished", "forbiddenStepProperties"):
            with self.subTest(check=name):
                self.assertTrue(checks[name]["passed"], checks[name])

    def test_test_skipping_in_either_maven_property_fails(self):
        for property_name in ("goals", "runner-arguments"):
            for option in ("-DskipTests", "-DskipTests=true", "-Dmaven.test.skip",
                           "-Dmaven.test.skip=true", '-DskipTests="true"',
                           "'-Dmaven.test.skip=true'", "-D skipTests=true",
                           '-D"skipTests=true"', '-D"maven.test.skip=true"'):
                with self.subTest(property=property_name, option=option):
                    actual = observed()
                    props = actual["jobs"][0]["steps"][0]["properties"]
                    props[property_name] = props.get(property_name, "") + " " + option
                    self.assertFalse(runner.grade(CASE, actual)["forbiddenStepProperties"]["passed"])
                    self.assertFalse(runner.grade_configuration(CONFIG, actual)
                                     ["forbiddenStepProperties"]["passed"])

    def test_disabling_assertions_in_either_property_fails(self):
        for property_name in ("goals", "runner-arguments"):
            for option in ("-DenableAssertions=false", '-DenableAssertions="false"',
                           '-D"enableAssertions=false"',
                           '-DargLine="-da"', "-DargLine=-disableassertions",
                           "-DargLine='-Xmx512m -da'", '-DargLine="-da:com.kawser..."',
                           '-DargLine="-Xmx512m -disableassertions:com.kawser..."',
                           '"-DargLine=-Xmx512m -da"',
                           "'-DargLine=-Xmx512m -disableassertions'",
                           '"-DargLine=-Xmx512m\t-da"',
                           '-D argLine="-Xmx512m -da"',
                           r'-DargLine="-Dlabel=\"some text\" -da"'):
                with self.subTest(property=property_name, option=option):
                    actual = observed()
                    props = actual["jobs"][0]["steps"][0]["properties"]
                    props[property_name] = props.get(property_name, "") + " " + option
                    self.assertFalse(runner.grade(CASE, actual)["forbiddenStepProperties"]["passed"])
                    self.assertFalse(runner.grade_configuration(CONFIG, actual)
                                     ["forbiddenStepProperties"]["passed"])

    def test_enabled_tests_and_assertions_remain_allowed(self):
        for property_name in ("goals", "runner-arguments"):
            for option in ("-DskipTests=false", "-Dmaven.test.skip=false",
                           "-DenableAssertions=true", '-DargLine="-ea"',
                           '-DargLine="-Xmx512m -enableassertions"',
                           '-DargLine="-Ddata=example"',
                           '-DargLine="-ea" -Dother="-da"',
                           '"-DargLine=-Xmx512m -ea"',
                           r'-DargLine="-Dlabel=\"some -da text\" -ea"',
                           '-Dlabel="some -DskipTests=true -DenableAssertions=false"',
                           r'-Dmaven.repo.local="C:\Program Files\maven-repo"'):
                with self.subTest(property=property_name, option=option):
                    actual = observed()
                    props = actual["jobs"][0]["steps"][0]["properties"]
                    props[property_name] = props.get(property_name, "") + " " + option
                    self.assertTrue(runner.grade(CASE, actual)["forbiddenStepProperties"]["passed"])
                    self.assertTrue(runner.grade_configuration(CONFIG, actual)
                                    ["forbiddenStepProperties"]["passed"])

    def test_adapter_resolves_maven_arguments_before_discarding_parameters(self):
        tc = runner.TeamCity("teamcity", "https://example.invalid", "synthetic", {})
        for field in ("goals", "runner-arguments"):
            for parameters, environment, overrides, selected, expected in (
                ({"args": '-V "-DargLine=-Xmx512m -da"'}, {}, {}, "%args%", False),
                ({"args": "-DskipTests"}, {}, {}, "%args%", False),
                ({"args": "%nested%", "nested": "-DenableAssertions=false"}, {}, {}, "%args%", False),
                ({"args": "%nested%", "nested": "-DskipTests=false"}, {}, {}, "%args%", True),
                ({"args": "-DskipTests"}, {}, {"args": "-DskipTests=false"}, "%args%", True),
                ({"args": "-DskipTests=false"}, {}, {"args": "-DskipTests"}, "%args%", False),
                ({}, {"MAVEN_ARGS": "-DenableAssertions=false"}, {}, "%env.MAVEN_ARGS%", False),
                ({}, {"MAVEN_ARGS": "-DskipTests"}, {"env.MAVEN_ARGS": "-DskipTests=false"}, "%env.MAVEN_ARGS%", True),
                ({}, {}, {}, "%missing%", False),
                ({"args": "%nested%", "nested": "%args%"}, {}, {}, "%args%", False),
                ({"args": 42}, {}, {}, "%args%", False),
            ):
                with self.subTest(field=field, selected=selected, parameters=parameters, overrides=overrides):
                    properties = {"goals": "clean verify", "runner-arguments": "-V"}
                    properties[field] += " " + selected
                    document = {"parameters": {"private": "private-canary", **parameters},
                        "environment": environment, "jobs": {"Verify": {
                            "parameters": {"env.JAVA_HOME": "%env.JDK_21_0%", **overrides},
                            "steps": [{"type": "maven", **properties}],
                            "files-publication": ["target/*.jar", "target/surefire-reports/*.xml"],
                        }}}
                    with mock.patch.object(tc, "pipeline_definition", return_value=document):
                        actual = observed()
                        actual["jobs"] = tc.jobs("project", "pipeline")
                    self.assertNotIn("private-canary", json.dumps(actual["jobs"]))
                    self.assertEqual(expected, runner.grade(CASE, actual)["forbiddenStepProperties"]["passed"])
                    self.assertEqual(expected, runner.grade_configuration(CONFIG, actual)
                                     ["forbiddenStepProperties"]["passed"])

    def test_inconclusive_maven_arguments_cannot_pass(self):
        for value in ('-V "-DargLine=-da', "%unknown%", "-D", None):
            with self.subTest(value=value):
                actual = observed()
                actual["jobs"][0]["steps"][0]["properties"]["runner-arguments"] = value
                self.assertFalse(runner.grade(CASE, actual)["forbiddenStepProperties"]["passed"])
                self.assertFalse(runner.grade_configuration(CONFIG, actual)["forbiddenStepProperties"]["passed"])

    def test_known_older_bundled_maven_is_rejected_before_running(self):
        for minor in (0, 1, 2, 3, 5, 6, 8, 9):
            with self.subTest(minor=minor):
                actual = observed()
                actual["jobs"][0]["steps"][0]["properties"]["maven-version"] = {
                    f"bundled-3-{minor}": {}}
                checks = runner.grade_configuration(CONFIG, actual)
                self.assertEqual(minor >= 6, checks["forbiddenStepProperties"]["passed"])
                self.assertNotIn("mavenVersion", checks)

    def test_extra_failed_or_ignored_test_fails_despite_39_successes(self):
        for update in ({"status": "FAILURE"}, {"ignored": True}, {"status": "UNKNOWN"}):
            with self.subTest(update=update):
                actual = observed()
                actual["tests"].append({"name": "Extra.test", "status": "SUCCESS",
                                        "ignored": False, **update})
                actual["testCount"] += 1
                checks = runner.grade(CASE, actual)
                self.assertTrue(checks["requiredTests"]["passed"])
                self.assertFalse(checks["allTestsPassed"]["passed"])

    def test_no_tests_fails_all_tests_passed(self):
        actual = observed()
        actual.update(tests=[], testCount=0)
        self.assertFalse(runner.grade(CASE, actual)["allTestsPassed"]["passed"])

    def test_each_real_test_class_requires_its_xml_filename(self):
        expected = {f"TEST-{PREFIX}{name}.xml" for name in CLASSES}
        paths = CASE["verification"]["artifactPaths"]
        self.assertEqual(expected, {path.rsplit("/", 1)[-1] for path in paths if path.endswith(".xml")})
        self.assertFalse(any("ProductRepositoryTest" in path for path in paths))
        for missing in expected:
            with self.subTest(missing=missing):
                actual = observed()
                actual["artifacts"].remove(missing)
                actual["artifacts"].append("TEST-unrelated.xml")
                self.assertFalse(runner.grade(CASE, actual)["artifactsPublished"]["passed"])

    def test_nested_or_flattened_xml_publication_is_accepted(self):
        for folder in ("", "target/surefire-reports/", "reports/junit/"):
            actual = observed()
            actual["artifacts"] = [folder + name for name in actual["artifacts"]]
            self.assertTrue(runner.grade(CASE, actual)["artifactsPublished"]["passed"])

    def test_runtime_check_is_scoped_to_opted_in_case(self):
        actual = observed()
        actual["mavenVersions"] = []
        self.assertFalse(runner.grade(CASE, actual)["mavenVersion"]["passed"])
        legacy = copy.deepcopy(CASE)
        legacy["expected"].pop("minimumMavenVersion")
        self.assertNotIn("mavenVersion", runner.grade(legacy, actual))

    def test_runtime_contract_cannot_be_used_in_configuration_only_case(self):
        import jsonschema
        schema = json.loads((EVALS / "schema.json").read_text())
        validator = jsonschema.Draft7Validator(schema)
        self.assertFalse(list(validator.iter_errors(CASE)))
        for value in ("unknown", "3.x", 3.6):
            invalid = copy.deepcopy(CASE)
            invalid["expected"]["minimumMavenVersion"] = value
            self.assertTrue(list(validator.iter_errors(invalid)))
        invalid = copy.deepcopy(CONFIG)
        invalid["expected"]["minimumMavenVersion"] = "3.6"
        self.assertTrue(list(validator.iter_errors(invalid)))


class MavenVersionTest(unittest.TestCase):
    def test_minimum_version_comparison_is_numeric(self):
        for version, status in (("3.5.4", "mismatch"), ("3.6", "verified"),
                                ("3.6.0", "verified"), ("3.9.11", "verified"),
                                ("3.10.0", "verified"), ("4.0.0", "verified")):
            with self.subTest(version=version):
                self.assertEqual(status, maven_version(log(version), job(), "3.6")["status"])

    def test_version_from_path_environment_or_free_banner_is_not_evidence(self):
        for text in (None, "M2_HOME=/tools/maven-3.9.11", "Apache Maven 3.9.11",
                     log().splitlines()[0], log("unknown"), log(index=2, total=2),
                     log(command="mvn --version")):
            with self.subTest(log=text):
                self.assertEqual("missing", maven_version(text, job(), "3.6")["status"])

    def test_pom_model_probe_cannot_supply_the_build_version(self):
        probe = log(command=f"/jdk-21/bin/java {MAIN} -f info.123.pom.xml "
                            "org.jetbrains.maven:info-maven3-plugin:1.0:info")
        self.assertEqual("missing", maven_version(probe, job(), "3.6")["status"])
        self.assertEqual("missing", maven_version(probe + log().splitlines()[0], job(), "3.6")["status"])
        self.assertEqual("mismatch", maven_version(probe + log("3.5.4"), job(), "3.6")["status"])
        self.assertEqual("verified", maven_version(probe + log(), job(), "3.6")["status"])

    def test_script_banner_cannot_cover_native_maven_step(self):
        configured = job([step("script"), step()])
        text = log(index=1, total=2) + log(index=2, total=2).splitlines()[0]
        self.assertEqual("missing", maven_version(text, configured, "3.6")["status"])
        self.assertEqual("verified", maven_version(log(index=2, total=2), configured, "3.6")["status"])

    def test_every_native_step_needs_its_own_version(self):
        configured = job([step(), step()])
        first = log(index=1, total=2)
        self.assertEqual("missing", maven_version(first, configured, "3.6")["status"])
        self.assertEqual("missing", maven_version(first + first, configured, "3.6")["status"])
        self.assertEqual("verified", maven_version(first + log(index=2, total=2), configured, "3.6")["status"])
        self.assertEqual("mismatch", maven_version(first + log("3.5.4", 2, 2), configured, "3.6")["status"])

    def test_conflicting_banners_and_duplicate_launches_fail(self):
        self.assertEqual("missing", maven_version(log() + "Apache Maven 3.8.6\n", job(), "3.6")["status"])
        self.assertEqual("missing", maven_version(log() + log(), job(), "3.6")["status"])

    def test_docker_wrapper_uses_actual_maven_command(self):
        text = ("[Step 1/1] Container script (to be run inside container):\n"
                f"[Step 1/1] exec /jdk/bin/java {MAIN} \\\n"
                "[Step 1/1] -V -B clean verify\n"
                "[Step 1/1] Starting: /bin/sh -c docker exec container /script.sh\n"
                "[Step 1/1] Apache Maven 3.9.11\n")
        for runtime in ("docker", "podman"):
            with self.subTest(runtime=runtime):
                wrapped = text.replace("docker exec", runtime + " exec")
                self.assertEqual("verified", maven_version(wrapped, job(), "3.6")["status"])
                self.assertEqual("missing", maven_version(
                    wrapped.replace("Starting:", "Not executed:"), job(), "3.6")["status"])
                self.assertEqual("mismatch", maven_version(
                    wrapped.replace("Apache Maven 3.9.11", "Apache Maven 3.5.4"), job(), "3.6")["status"])

    def test_observation_reads_only_bound_maven_child_logs(self):
        tc = mock.Mock()
        tc.build_log.return_value = log()
        configured = job()
        results = [{"job": job([step("script")]), "buildId": 101},
                   {"job": configured, "buildId": 102}]
        measured = observe_maven_versions(tc, results, "3.6")
        tc.build_log.assert_called_once_with(102)
        self.assertTrue(maven_versions_match(measured, [configured], "3.6"))
        self.assertNotIn("/jdk", json.dumps(measured))
        self.assertNotIn("Launcher", json.dumps(measured))
        for corrupt in ([], measured * 2, [{**measured[0], "jobId": "other"}],
                        [{**measured[0], "versions": ["3.5.4"]}]):
            self.assertFalse(maven_versions_match(corrupt, [configured], "3.6"))
        tc.build_log.side_effect = RuntimeError("private-canary")
        measured = observe_maven_versions(tc, results, "3.6")
        self.assertEqual("unavailable", measured[0]["status"])
        self.assertNotIn("private-canary", json.dumps(measured))
        self.assertFalse(maven_versions_match(measured, [configured], "3.6"))

    def test_adapter_reads_raw_log_through_first_class_cli(self):
        tc = runner.TeamCity("teamcity", "https://example.invalid", "synthetic", {})
        with mock.patch.object(tc, "_run", return_value=log()) as command:
            self.assertEqual(log(), tc.build_log(102))
        command.assert_called_once_with(["run", "log", "102", "--raw"])


if __name__ == "__main__":
    unittest.main()
