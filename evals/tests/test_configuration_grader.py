import importlib.util
import json
import pathlib
import unittest


EVALS = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_case = load_module("run_case_configuration_test", "run_case.py")
TOOL_USE_CASE = EVALS / "pipeline-configuration/cases/teamcity-cli-not-curl.json"
CLEAN_SPRING_CASE = EVALS / "pipeline-configuration/cases/clean-spring-boot-maven-pipeline.json"
SPRING_DEMO_CASE = EVALS / "pipeline-configuration/cases/spring-boot-demo-gradle-testcontainers-pipeline.json"


CASE = {
    "expected": {
        "configurationValidated": True,
        "sourceMutations": "none",
        "minimumJobs": 3,
        "expectedJobCount": 3,
        "requiredJobs": [
            {
                "jobMatches": "(?i)android",
                "requiredStepTypes": ["gradle"],
                "requiredStepProperties": [
                    {"stepType": "gradle", "property": "tasks", "matches": "assembleDebug"}
                ],
                "requiredArtifactRules": [r"\.apk"],
                "requiredAgentRequirements": ["Linux"],
            },
            {
                "jobMatches": "(?i)ios",
                "requiredStepTypes": ["script"],
                "requiredStepProperties": [
                    {
                        "stepType": "script",
                        "property": "script-content",
                        "matches": r"(?s)xcodebuild.*(?:zip|ditto).*\.app",
                    }
                ],
                "requiredArtifactRules": [r"\.zip"],
                "requiredAgentRequirements": ["Mac"],
            },
            {
                "jobMatches": "(?i)desktop",
                "requiredStepTypes": ["gradle"],
            },
        ],
    }
}


def job(job_id, name, runs_on, steps, artifacts=""):
    return {
        "id": f"fixture/{job_id}",
        "name": name,
        "steps": steps,
        "artifactRules": artifacts,
        "agentRequirements": [runs_on],
    }


def step(step_type, **properties):
    return {"type": step_type, "name": step_type, "properties": properties}


def observed_jobs():
    return {
        "jobs": [
            job("android", "Android", "Linux", [step("gradle", tasks="assembleDebug")], "app.apk"),
            job(
                "ios",
                "iOS",
                "Mac",
                [step("script", **{"script-content": "xcodebuild\nzip ios.zip App.app"})],
                "ios.zip",
            ),
            job("desktop", "Desktop", "Linux", [step("gradle", tasks="packageDmg")]),
        ],
        "mutations": [],
        "toolCalls": [],
    }


class ConfigurationGraderTest(unittest.TestCase):
    def test_toolchain_accepts_exact_jdk_container_image(self):
        jobs = [
            job(
                "build",
                "Build",
                "self-hosted",
                [step("gradle", tasks="build", **{"docker-image": "eclipse-temurin:25-jdk"})],
            )
        ]

        matched, evidence = run_case.toolchain_evidence({}, "25", jobs)

        self.assertTrue(matched)
        self.assertIn("declared-docker-image", evidence)

    def test_toolchain_rejects_wrong_jdk_container_image(self):
        jobs = [
            job(
                "build",
                "Build",
                "self-hosted",
                [step("gradle", tasks="build", **{"docker-image": "eclipse-temurin:21-jdk"})],
            )
        ]

        matched, _ = run_case.toolchain_evidence({}, "25", jobs)

        self.assertFalse(matched)

    def test_clean_spring_requires_java_21_not_a_particular_selection_method(self):
        case = json.loads(CLEAN_SPRING_CASE.read_text())
        observed = {
            "jobs": [
                job(
                    "verify",
                    "Maven verify",
                    "Linux",
                    [step("maven", goals="clean verify", **{"docker-image": "eclipse-temurin:17-jdk"})],
                    "target/app.jar",
                )
            ],
            "mutations": [],
            "toolCalls": [],
        }

        checks = run_case.grade_configuration(case, observed)
        self.assertFalse(checks["toolchain"]["passed"])

        observed["jobs"][0]["steps"][0]["properties"]["docker-image"] = "eclipse-temurin:21-jdk"
        checks = run_case.grade_configuration(case, observed)
        self.assertTrue(checks["toolchain"]["passed"])

        del observed["jobs"][0]["steps"][0]["properties"]["docker-image"]
        observed["jobs"][0]["parameters"] = {"env.JAVA_HOME": "%env.JDK_21_0%"}
        self.assertTrue(run_case.grade_configuration(case, observed)["toolchain"]["passed"])

    def test_spring_demo_keeps_docker_backed_tests_out_of_package_job(self):
        case = json.loads(SPRING_DEMO_CASE.read_text())
        jdk_image = "eclipse-temurin:21-jdk"
        observed = {
            "jobs": [
                job(
                    "build-package",
                    "Build package",
                    "self-hosted Docker available",
                    [
                        step("script", **{"script-content": "docker info"}),
                        step(
                            "gradle",
                            tasks="generateJooq openApiGenerate bootJar",
                            **{"docker-image": jdk_image},
                        )
                    ],
                    "build/libs/spring-boot-demo-local.jar",
                ),
                job(
                    "testcontainers-tests",
                    "Testcontainers tests",
                    "self-hosted Docker available",
                    [
                        step("script", **{"script-content": "docker info"}),
                        step(
                            "gradle",
                            tasks="generateJooq openApiGenerate test",
                            **{"docker-image": jdk_image},
                        ),
                    ],
                    "build/test-results/test/TEST-example.xml",
                ),
            ],
            "mutations": [],
            "toolCalls": [],
        }

        checks = run_case.grade_configuration(case, observed)
        self.assertTrue(checks["requiredJobs"]["passed"])

        observed["jobs"][0]["name"] = "Build and package JAR (generated sources, no tests)"
        checks = run_case.grade_configuration(case, observed)
        self.assertTrue(checks["requiredJobs"]["passed"])

        observed["jobs"][0]["steps"][1]["properties"]["tasks"] += " test"
        checks = run_case.grade_configuration(case, observed)
        self.assertFalse(checks["requiredJobs"]["passed"])

    def test_job_description_is_a_fallback_for_generic_keys(self):
        observed = observed_jobs()
        observed["jobs"][0]["id"] = "fixture/job1"
        checks = run_case.grade_configuration(CASE, observed)
        self.assertTrue(checks["requiredJobs"]["passed"])

    def test_ambiguous_structural_keys_still_fail(self):
        observed = observed_jobs()
        observed["jobs"][2]["id"] = "fixture/android-desktop"
        checks = run_case.grade_configuration(CASE, observed)
        self.assertFalse(checks["requiredJobs"]["passed"])

    def test_per_job_contracts_accept_correct_topology(self):
        checks = run_case.grade_configuration(CASE, observed_jobs())

        self.assertTrue(checks["jobCount"]["passed"])
        self.assertTrue(checks["requiredJobs"]["passed"])

    def test_ios_framework_contract_uses_gradle_on_macos(self):
        case = {
            "expected": {
                "configurationValidated": True,
                "sourceMutations": "none",
                "minimumJobs": 1,
                "expectedJobCount": 1,
                "requiredJobs": [
                    {
                        "jobMatches": "(?i)ios",
                        "requiredStepTypes": ["gradle", "script"],
                        "requiredStepProperties": [
                            {
                                "stepType": "gradle",
                                "property": "tasks",
                                "matches": "linkDebugFrameworkIosSimulatorArm64",
                            },
                            {
                                "stepType": "script",
                                "property": "script-content",
                                "matches": r"(?s)(?:zip|ditto).*\.framework",
                            },
                        ],
                        "requiredArtifactRules": [r"\.zip"],
                        "requiredAgentRequirements": ["Mac"],
                    }
                ]
            }
        }
        observed = {
            "jobs": [
                job(
                    "ios-framework",
                    "iOS simulator framework",
                    "Mac",
                    [
                        step("gradle", tasks="linkDebugFrameworkIosSimulatorArm64"),
                        step("script", **{"script-content": "zip ios.framework.zip shared.framework"}),
                    ],
                    "ios.framework.zip",
                )
            ],
            "mutations": [],
            "toolCalls": [],
        }

        checks = run_case.grade_configuration(case, observed)

        self.assertTrue(checks["requiredJobs"]["passed"])

    def test_exact_job_count_rejects_extra_job(self):
        observed = observed_jobs()
        observed["jobs"].append(
            job("extra", "Extra", "Linux", [step("gradle", tasks="help")])
        )

        checks = run_case.grade_configuration(CASE, observed)

        self.assertFalse(checks["jobCount"]["passed"])

    def test_artifact_on_wrong_job_does_not_pass(self):
        observed = observed_jobs()
        observed["jobs"][0]["artifactRules"] = ""
        observed["jobs"][2]["artifactRules"] = "app.apk"

        checks = run_case.grade_configuration(CASE, observed)

        self.assertFalse(checks["requiredJobs"]["passed"])

    def test_step_property_on_wrong_job_does_not_pass(self):
        observed = observed_jobs()
        observed["jobs"][0]["steps"][0]["properties"]["tasks"] = "check"
        observed["jobs"][2]["steps"][0]["properties"]["tasks"] = "assembleDebug"

        checks = run_case.grade_configuration(CASE, observed)

        self.assertFalse(checks["requiredJobs"]["passed"])

    def test_two_contracts_cannot_reuse_one_job(self):
        case = {"expected": dict(CASE["expected"])}
        case["expected"]["requiredJobs"] = [
            {"jobMatches": "(?i)android"},
            {"jobMatches": "(?i)android|mobile"},
        ]

        checks = run_case.grade_configuration(case, observed_jobs())

        self.assertFalse(checks["requiredJobs"]["passed"])

    def test_tool_use_rejects_rest_through_teamcity_cli(self):
        case = json.loads(TOOL_USE_CASE.read_text())
        observed = observed_jobs()
        observed["toolCalls"] = [
            'Bash {"command": "teamcity api /app/rest/projects"}',
        ]

        checks = run_case.grade_configuration(case, observed)

        self.assertFalse(checks["toolUse"]["passed"])

    def test_tool_use_accepts_first_class_teamcity_commands(self):
        case = json.loads(TOOL_USE_CASE.read_text())
        observed = observed_jobs()
        observed["toolCalls"] = [
            'Bash {"command": "teamcity pipeline list --project Example"}',
        ]

        checks = run_case.grade_configuration(case, observed)

        self.assertTrue(checks["toolUse"]["passed"])

    def test_mcp_only_requires_mcp_and_forbids_cli(self):
        checks = run_case.grade_configuration(CASE, observed_jobs())
        run_case.add_transport_checks(
            checks,
            "mcp-only",
            {"mcpTeamCityCalls": 0, "teamcityCliCalls": 1},
        )

        self.assertFalse(checks["requiredMcpToolUse"]["passed"])
        self.assertFalse(checks["forbiddenCliToolUse"]["passed"])

    def test_mcp_only_transport_checks_pass_for_mcp_without_cli(self):
        checks = run_case.grade_configuration(CASE, observed_jobs())
        run_case.add_transport_checks(
            checks,
            "mcp-only",
            {"mcpTeamCityCalls": 1, "teamcityCliCalls": 0},
        )

        self.assertTrue(checks["requiredMcpToolUse"]["passed"])
        self.assertTrue(checks["forbiddenCliToolUse"]["passed"])


if __name__ == "__main__":
    unittest.main()
