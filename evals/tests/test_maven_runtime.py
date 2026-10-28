import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest
from unittest import mock


EVALS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))
from first_green_evidence import observe_chain
from maven_runtime import maven_runtime, maven_runtime_matches

spec = importlib.util.spec_from_file_location("maven_runtime_runner", EVALS / "run_case.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
spec = importlib.util.spec_from_file_location("maven_runtime_collector", EVALS / "collect_teamcity_eval_runs.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def launch(home="/usr/lib/jvm/java-21-amazon-corretto", step=1, total=1):
    executable = home + ("\\bin\\java.exe" if "\\" in home else "/bin/java")
    return (f'[10:00:00]i: [Step {step}/{total}] Starting: "{executable}" '
            '-Dteamcity.auth.password=private-canary -Dteamcity.maven.watcher.home=/watcher-jdk17 '
            '-classpath /tools/plexus-classworlds-2.9.0.jar '
            'org.codehaus.plexus.classworlds.launcher.Launcher -B clean verify\n')


def job(number=1, steps=1):
    return {"id": f"pipeline/verify{number}", "name": f"Verify {number}",
            "parameters": {"env.JAVA_HOME": "%env.JDK_21_0%"},
            "steps": [{"type": "maven", "properties": {"goals": "clean verify"}}
                      for _ in range(steps)],
            "artifactRules": "target/app.jar\ntarget/surefire-reports/*.xml", "agentRequirements": []}


class MavenLogTest(unittest.TestCase):
    def test_native_maven_launch_identifies_java_on_linux_windows_and_macos(self):
        for home, required in (("/usr/lib/jvm/java-21-amazon-corretto", "21"),
                               (r"C:\Program Files\Java\jdk-21.0.2", "21"),
                               ("/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home", "21"),
                               ("/opt/jdk1.8.0_402", "8")):
            with self.subTest(home=home):
                result = maven_runtime(launch(home), required, 1)
                self.assertEqual("verified", result["status"])
                self.assertEqual([int(required)], result["observedMajors"])
                self.assertNotIn("private-canary", json.dumps(result))

    def test_agent_jvm_home_container_and_standalone_java_are_not_maven_evidence(self):
        log = ('Agent is running under JRE: 21.0.2\n'
               'JAVA_HOME=/jdk-21\nteamcity.agent.jvm.java.home=/jdk-21\n'
               'Starting: /jdk-21/bin/java -version\nopenjdk version "21.0.2"\n'
               'Java version: 21.0.2, vendor: Example, runtime: /jdk-21\n')
        self.assertEqual("missing", maven_runtime(log, "21", 1)["status"])

    def test_wrong_maven_jvm_is_not_hidden_by_other_java_output(self):
        log = 'openjdk version "21.0.2"\n' + launch("/opt/jdk-17.0.10")
        result = maven_runtime(log, "21", 1)
        self.assertEqual("mismatch", result["status"])
        self.assertEqual([17], result["observedMajors"])

    def test_major_must_come_from_the_executable_installation(self):
        for home in ("/jdk-21/current", "/work/21/java", "/opt/jdk-121"):
            with self.subTest(home=home):
                self.assertNotEqual("verified", maven_runtime(launch(home), "21", 1)["status"])

    def test_unversioned_home_requires_maven_version_output_for_that_home(self):
        log = launch("/opt/java/openjdk")
        self.assertEqual("missing", maven_runtime(log, "21", 1)["status"])
        log += ('[10:00:01] : [Step 1/1] Java version: 21.0.2, vendor: Example, '
                'runtime: /opt/java/openjdk\n')
        self.assertEqual("verified", maven_runtime(log, "21", 1)["status"])
        self.assertEqual("mismatch", maven_runtime(log.replace("version: 21", "version: 17"), "21", 1)["status"])

    def test_version_output_from_another_home_or_step_cannot_confirm_maven(self):
        log = launch("/opt/java/openjdk", step=2, total=2)
        for info in ('[Step 1/2] Java version: 21.0.2, vendor: Example, runtime: /opt/java/openjdk',
                     '[Step 2/2] Java version: 21.0.2, vendor: Example, runtime: /opt/jdk-21'):
            with self.subTest(info=info):
                self.assertEqual("missing", maven_runtime(log + info, "21", 1)["status"])

    def test_conflicting_maven_version_output_overrides_a_versioned_path(self):
        for home in ("/opt/jdk-21", "/resolved/jdk-17"):
            with self.subTest(home=home):
                log = launch("/opt/jdk-21") + f'[Step 1/1] Java version: 17.0.10, vendor: Example, runtime: {home}'
                self.assertEqual("mismatch", maven_runtime(log, "21", 1)["status"])

    def test_unversioned_unix_homes_are_case_sensitive(self):
        log = launch("/opt/Java") + '[Step 1/1] Java version: 21.0.2, vendor: Example, runtime: /opt/java'
        self.assertEqual("missing", maven_runtime(log, "21", 1)["status"])

    def test_every_maven_step_must_have_its_own_launch(self):
        first = launch(step=1, total=2)
        self.assertEqual("missing", maven_runtime(first, "21", 2)["status"])
        self.assertEqual("ambiguous", maven_runtime(first + first, "21", 2)["status"])
        self.assertEqual("verified", maven_runtime(first + launch(step=2, total=2), "21", 2)["status"])
        self.assertEqual("mismatch", maven_runtime(first + launch("/jdk-17", 2, 2), "21", 2)["status"])

    def test_maven_launch_must_belong_to_the_declared_step_position(self):
        self.assertEqual("verified", maven_runtime(launch(step=2, total=3), "21", 1, [2], 3)["status"])
        self.assertEqual("missing", maven_runtime(launch(step=1, total=3), "21", 1, [2], 3)["status"])
        self.assertEqual("missing", maven_runtime(launch(step=2, total=2), "21", 1, [2], 3)["status"])

    def test_empty_malformed_or_unresolved_logs_do_not_pass(self):
        for log in (None, "", "No log available", launch("%env.JDK_21_0%"),
                    'echo "' + launch() + '"',
                    launch("/opt/java/openjdk") + '[Step 1/1] Java version: unknown, vendor: Example, runtime: /opt/java/openjdk'):
            with self.subTest(log=log):
                self.assertNotEqual("verified", maven_runtime(log, "21", 1)["status"])


class MavenGraderTest(unittest.TestCase):
    def fixture(self, job_count=1):
        jobs = [job(number) for number in range(1, job_count + 1)]
        children = [{"id": 100 + number, "buildTypeId": f"verify{number}",
                     "state": "finished", "status": "SUCCESS", "buildType": {"name": item["name"]}}
                    for number, item in enumerate(jobs, 1)]
        build = {"id": 10, "pipelineId": "pipeline", "selection": "source-matched",
                 "attempts": 1, "status": "SUCCESS", "nodes": [
                     {"id": 10, "state": "finished", "status": "SUCCESS"}, *children]}
        tc = mock.Mock()
        tc.jobs.return_value = jobs
        tc.build.side_effect = lambda build_id: next(item for item in children if item["id"] == build_id)
        tc.build_log.return_value = launch()
        tc.test_results.return_value = [{"name": "Example.test", "status": "SUCCESS", "ignored": False}]
        tc.artifacts.return_value = ["app.jar"]
        return tc, build, jobs

    def grade(self, observed):
        case = json.loads((EVALS / "first-green-build/cases/spring-petclinic-maven-yaml.json").read_text())
        case["expected"]["toolchain"]["jdk"] = "21"
        return runner.grade(case, {**observed, "buildTypeCount": 2, "mutations": []})["toolchain"]

    def test_collects_only_bound_maven_child_logs_and_grades_without_java_home(self):
        tc, build, jobs = self.fixture()
        jobs[0]["parameters"] = {}
        jobs[0]["steps"][0]["properties"]["jdk-home"] = "%env.JDK_21_0%"
        observed, diagnostics = observe_chain(tc, "project", build, "21")
        tc.build_log.assert_called_once_with(101)
        self.assertTrue(self.grade(observed)["passed"])
        self.assertTrue(diagnostics["jdk"]["runtimeVerified"])

    def test_java_home_and_agent_properties_cannot_override_runtime(self):
        tc, build, jobs = self.fixture()
        jobs[0]["steps"][0]["properties"].update({"jdk-home": "%env.JDK_17_0%",
                                                  "docker-image": "eclipse-temurin:21-jdk"})
        for log in ("", launch("/jdk-17")):
            with self.subTest(log=log):
                tc.build_log.return_value = log
                observed, diagnostics = observe_chain(tc, "project", build, "21")
                observed["properties"] = {"java.version": "21.0.2"}
                self.assertFalse(self.grade(observed)["passed"])
                self.assertFalse(diagnostics["jdk"]["runtimeVerified"])

    def test_configuration_grading_honors_runner_override_without_logs(self):
        tc, _, jobs = self.fixture()
        case = {"expected": {"minimumJobs": 1, "sourceMutations": "none", "toolchain": {"jdk": "21"}}}
        observed = {"jobs": jobs, "mutations": [], "toolCalls": []}
        for home, expected in (("%env.JDK_17_0%", False), ("%env.JDK_21_0%", True)):
            with self.subTest(home=home):
                jobs[0]["steps"][0]["properties"]["jdk-home"] = home
                self.assertEqual(expected, runner.grade_configuration(case, observed)["toolchain"]["passed"])
        jobs[0]["parameters"] = {}
        self.assertTrue(runner.grade_configuration(case, observed)["toolchain"]["passed"])
        jobs[0]["parameters"] = {"env.JAVA_HOME": "%env.JDK_17_0%"}
        self.assertTrue(runner.grade_configuration(case, observed)["toolchain"]["passed"])
        tc.build_log.assert_not_called()

    def test_each_maven_job_needs_its_own_runtime_evidence(self):
        tc, build, jobs = self.fixture(2)
        tc.build_log.side_effect = lambda build_id: launch() if build_id == 101 else ""
        observed, diagnostics = observe_chain(tc, "project", build, "21")
        self.assertEqual([mock.call(101), mock.call(102)], tc.build_log.call_args_list)
        self.assertFalse(self.grade(observed)["passed"])
        self.assertEqual(["verified", "missing"], [item["status"] for item in diagnostics["jdk"]["mavenRuntime"]])
        observed["mavenRuntime"][1] = copy.deepcopy(observed["mavenRuntime"][0])
        self.assertFalse(maven_runtime_matches(observed["mavenRuntime"], jobs, "21"))

    def test_failed_log_read_has_safe_diagnostics_and_cannot_pass(self):
        tc, build, _ = self.fixture()
        tc.build_log.side_effect = runner.EvalError("private-canary")
        observed, diagnostics = observe_chain(tc, "project", build, "21")
        self.assertFalse(self.grade(observed)["passed"])
        self.assertEqual("unavailable", diagnostics["jdk"]["mavenRuntime"][0]["status"])
        self.assertNotIn("private-canary", json.dumps(diagnostics))

    def test_maven_case_cannot_fall_back_to_declarations_when_no_maven_step_exists(self):
        tc, build, jobs = self.fixture()
        jobs[0]["steps"] = [{"type": "script", "properties": {"script-content": "mvn verify"}}]
        observed, _ = observe_chain(tc, "project", build, "21")
        self.assertFalse(self.grade(observed)["passed"])
        tc.build_log.assert_not_called()

    def test_public_result_and_collector_keep_only_safe_runtime_diagnostics(self):
        tc, build, _ = self.fixture()
        observed, diagnostics = observe_chain(tc, "project", build, "21")
        diagnostics["jdk"]["mavenRuntime"][0].update(log=launch(), path="private-canary")
        published = runner.publishable_result({"checks": {}, "verificationDiagnostics": diagnostics,
                                               "mavenRuntime": observed["mavenRuntime"], "log": launch()})
        self.assertNotIn("private-canary", json.dumps(published))
        self.assertNotIn("jobId", json.dumps(published))

        def cli(_server, *args):
            if "--json" in args:
                return subprocess.CompletedProcess([], 0, json.dumps({"file": [{"name": "eval-result.json"}]}))
            destination = pathlib.Path(args[args.index("--output") + 1])
            (destination / "eval-result.json").write_text(json.dumps(published))
            return subprocess.CompletedProcess([], 0, "")

        with mock.patch.object(collector, "cli", side_effect=cli):
            collected = collector.download_result([], "https://example.invalid", 50, set())
        self.assertNotIn("private-canary", json.dumps(collected))
        self.assertEqual("verified", collected["verificationDiagnostics"]["jdk"]["mavenRuntime"][0]["status"])

    def test_cli_reads_complete_raw_log_for_the_exact_build(self):
        tc = runner.TeamCity("teamcity", "https://example.invalid", "private", {})
        with mock.patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, launch())) as call:
            self.assertEqual(launch(), tc.build_log(101))
        self.assertEqual(["teamcity", "run", "log", "101", "--raw"], call.call_args.args[0])
        self.assertEqual("https://example.invalid", call.call_args.kwargs["env"]["TEAMCITY_URL"])
        self.assertNotIn("private", call.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
