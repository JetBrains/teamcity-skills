"""Synthetic contracts only: no live builds, prompts, or agent traces."""

import copy
import importlib.util
import json
import pathlib
import sys
import unittest
from unittest import mock

EVALS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))
spec = importlib.util.spec_from_file_location("coverage_runner", EVALS / "run_case.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def case(name, kind="first-green-build"):
    return json.loads((EVALS / kind / "cases" / f"{name}.json").read_text())


def step(kind, **properties):
    return {"type": kind, "name": kind, "properties": properties}


def gradle_observed():
    jobs = []
    for key, target, artifacts in (
        ("package", "bootJar", "build/libs/app.jar"),
        ("test", "test", "build/test-results/test/TEST-example.xml"),
    ):
        jobs.append({
            "id": f"pipeline/{key}", "name": key,
            "parameters": {"env.JAVA_HOME": "%env.JDK_21_0%"},
            "steps": [step("script", **{"script-content": "docker info"}),
                      step("gradle", tasks="generateJooq openApiGenerate"),
                      step("gradle", tasks=target)],
            "artifactRules": artifacts,
            "agentRequirements": ["container.engine.osType = linux"],
        })
    tests = [{"name": "org.usmanzaheer1995.springbootdemo.SpringBootDemoApplicationTests.contextLoads",
              "status": "SUCCESS", "ignored": False}]
    results = [
        {"job": jobs[0], "status": "SUCCESS", "tests": [], "artifacts": ["app.jar"]},
        {"job": jobs[1], "status": "SUCCESS", "tests": tests,
         "artifacts": ["TEST-example.xml"]},
    ]
    return {"jobs": jobs, "jobResults": results, "tests": tests,
            "testCount": 1, "artifacts": ["app.jar", "TEST-example.xml"],
            "properties": {}, "buildStatus": "SUCCESS", "buildTypeCount": 3,
            "statusText": "", "attempts": 1, "mutations": [], "toolCalls": []}


class TwoProjectCoverageTest(unittest.TestCase):
    def setUp(self):
        self.gradle = case("spring-boot-demo-gradle-testcontainers")
        self.maven = case("clean-spring-boot-maven")
        self.observed = gradle_observed()

    def grades(self):
        return runner.grade(self.gradle, self.observed)

    def test_configuration_and_runtime_contracts_stay_in_sync(self):
        for name in ("clean-spring-boot-maven", "spring-boot-demo-gradle-testcontainers"):
            with self.subTest(name=name):
                self.assertEqual(case(name)["expected"]["configuration"],
                                 case(name + "-pipeline", "pipeline-configuration")["expected"])

    def test_native_jdk_and_container_jdk_both_pass(self):
        self.assertTrue(all(check["passed"] for check in self.grades().values()))
        for job in self.observed["jobs"]:
            job["parameters"] = {}
            job["steps"][1]["properties"]["docker-image"] = "eclipse-temurin:21-jdk"
        self.assertTrue(all(check["passed"] for check in self.grades().values()))

    def test_runtime_jdk_contradiction_cannot_be_overwritten_by_configuration(self):
        self.observed["properties"] = {"java.version": "17.0.1"}
        self.assertFalse(self.grades()["toolchain"]["passed"])

    def test_package_cannot_satisfy_tests_job_even_with_correct_total(self):
        self.observed["jobResults"][0]["tests"] = self.observed["tests"]
        self.observed["jobResults"][1]["tests"] = []
        self.assertTrue(self.grades()["testsExecutedAndReported"]["passed"])
        self.assertFalse(self.grades()["jobResults"]["passed"])

    def test_skipped_failed_or_foreign_tests_are_not_integration_proof(self):
        original = copy.deepcopy(self.observed)
        for update in ({"ignored": True}, {"status": "FAILURE"}, {"name": "Unrelated.unit"}):
            self.observed = copy.deepcopy(original)
            self.observed["jobResults"][1]["tests"][0].update(update)
            with self.subTest(update=update):
                self.assertFalse(self.grades()["jobResults"]["passed"])

    def test_empty_test_job_fails_even_when_declared_tasks_are_correct(self):
        self.observed["jobResults"][1]["tests"] = []
        self.assertTrue(self.grades()["requiredJobs"]["passed"])
        self.assertFalse(self.grades()["jobResults"]["passed"])

    def test_artifacts_must_come_from_the_correct_job(self):
        results = self.observed["jobResults"]
        results[0]["artifacts"], results[1]["artifacts"] = results[1]["artifacts"], results[0]["artifacts"]
        self.assertTrue(self.grades()["artifactsPublished"]["passed"])
        self.assertFalse(self.grades()["jobResults"]["passed"])

    def test_failed_member_cannot_pass_job_results(self):
        self.observed["jobResults"][1]["status"] = "FAILURE"
        self.assertFalse(self.grades()["jobResults"]["passed"])

    def test_docker_is_required_before_packaging_as_well_as_tests(self):
        self.observed["jobs"][0]["steps"] = self.observed["jobs"][0]["steps"][1:]
        self.assertFalse(self.grades()["requiredJobs"]["passed"])

    def test_generation_is_required_in_each_isolated_job(self):
        self.observed["jobs"][0]["steps"][1]["properties"]["tasks"] = "bootJar"
        self.assertFalse(self.grades()["requiredJobs"]["passed"])

    def test_reference_uses_separate_generation_and_compilation_invocations(self):
        self.assertEqual(
            "DEMO_ENV=local ./gradlew --no-daemon generateJooq openApiGenerate && "
            "DEMO_ENV=local ./gradlew --no-daemon test bootJar",
            self.gradle["verification"]["command"],
        )
        # Structural settings alone cannot prove Gradle's task graph works.
        for result in self.observed["jobResults"]:
            result.update(status="FAILURE", tests=[], artifacts=[])
        self.observed.update(buildStatus="FAILURE", tests=[], testCount=0, artifacts=[])
        checks = self.grades()
        self.assertTrue(checks["requiredJobs"]["passed"])
        self.assertFalse(checks["firstBuild"]["passed"])
        self.assertFalse(checks["jobResults"]["passed"])

    def test_lifecycle_build_cannot_silently_execute_tests_in_package_job(self):
        self.observed["jobs"][0]["steps"][1]["properties"]["tasks"] += " build"
        self.assertFalse(self.grades()["requiredJobs"]["passed"])

    def test_test_exclusion_does_not_pass_by_containing_word_test(self):
        for option in ("-x test", "--exclude-task test", "--exclude-task=test"):
            self.observed = gradle_observed()
            self.observed["jobs"][1]["steps"][1]["properties"]["tasks"] += " " + option
            with self.subTest(option=option):
                self.assertFalse(self.grades()["requiredJobs"]["passed"])

    def test_maven_requires_real_suite_coverage_not_one_arbitrary_test(self):
        self.assertEqual("mvn -B -ntp clean verify", self.maven["verification"]["command"])
        tests = [{"name": "com.kawser.cleanspringbootproject." + name + ".example",
                  "status": "SUCCESS", "ignored": False} for name in (
                      "ProductServiceTest", "ProductControllerTest", "AuthenticationServiceTest",
                      "AuthenticationControllerTest", "UserRepositoryTest",
                      "CleanSpringBootProjectApplicationTests")]
        tests += [{"name": f"com.example.additional{i}", "status": "SUCCESS", "ignored": False}
                  for i in range(33)]
        self.assertTrue(runner.required_tests_pass(self.maven["expected"], tests))
        self.assertFalse(runner.required_tests_pass(self.maven["expected"], tests[:1]))
        tests[0]["ignored"] = True
        self.assertFalse(runner.required_tests_pass(self.maven["expected"], tests))

    def test_maven_configuration_accepts_native_java_without_docker(self):
        configured = {"jobs": [{"id": "pipeline/verify", "name": "Verify",
                      "parameters": {"env.JAVA_HOME": "%env.JDK_21_0%"},
                      "steps": [step("maven", goals="clean verify")],
                      "artifactRules": "target/*.jar\ntarget/surefire-reports/*.xml",
                      "agentRequirements": ["Linux"]}], "mutations": [], "toolCalls": []}
        contract = case("clean-spring-boot-maven-pipeline", "pipeline-configuration")
        self.assertTrue(all(check["passed"] for check in
                            runner.grade_configuration(contract, configured).values()))
        configured["jobs"][0]["steps"][0]["properties"]["goals"] += " -DskipTests"
        self.assertFalse(runner.grade_configuration(contract, configured)
                         ["forbiddenStepProperties"]["passed"])

    def test_ambiguous_runtime_job_does_not_borrow_another_result(self):
        self.observed["jobResults"].append(copy.deepcopy(self.observed["jobResults"][1]))
        self.assertFalse(self.grades()["jobResults"]["passed"])

    def test_test_adapter_discards_failure_details_and_rejects_partial_results(self):
        tc = runner.TeamCity("teamcity", "https://example.invalid", "synthetic", {})
        payload = {"count": 1, "testOccurrence": [{"name": "Example.test", "status": "SUCCESS",
                                                    "details": "private-canary"}]}
        with mock.patch.object(tc, "_run", return_value=payload):
            results = tc.test_results(1)
            self.assertNotIn("private-canary", json.dumps(results))
            payload["count"] = 2
            with self.assertRaises(runner.EvidenceError):
                tc.test_results(1)

    def test_safe_result_does_not_publish_test_names_or_job_details(self):
        raw = {"checks": self.grades(), "jobResults": self.observed["jobResults"],
               "tests": [{"name": "private-canary"}],
               "verificationDiagnostics": {"builds": [{"id": 1, "successfulTestCount": 1,
                                                        "tests": ["private-canary"]}]}}
        safe = runner.publishable_result(raw)
        self.assertNotIn("private-canary", json.dumps(safe))
        self.assertTrue(safe["checks"]["jobResults"]["passed"])
        self.assertEqual(1, safe["verificationDiagnostics"]["builds"][0]["successfulTestCount"])


if __name__ == "__main__":
    unittest.main()
