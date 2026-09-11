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
        self.assertIn("docker-image:eclipse-temurin:25-jdk", evidence)

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


if __name__ == "__main__":
    unittest.main()
