import importlib.util
import json
import pathlib
import unittest


EVALS = pathlib.Path(__file__).resolve().parents[1]
CASE = EVALS / "first-green-build/cases/spring-boot-kotlin-gradle-java25.json"
spec = importlib.util.spec_from_file_location("run_case_first_green_java25_test", EVALS / "run_case.py")
run_case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_case)


class FirstGreenJava25Test(unittest.TestCase):
    def setUp(self):
        self.case = json.loads(CASE.read_text())
        self.observed = {
            "buildTypeCount": 1,
            "buildStatus": "SUCCESS",
            "statusText": "Successful",
            "attempts": 1,
            "testCount": 1,
            "artifacts": ["template-app/build/libs/template-app.jar"],
            "properties": {},
            "jobs": [{
                "id": "fixture/build",
                "steps": [{
                    "type": "gradle",
                    "properties": {
                        "tasks": "clean build",
                        "docker-image": "eclipse-temurin:25-jdk",
                    },
                }],
            }],
            "mutations": [],
        }

    def test_pass_requires_green_build_and_java25_gradle_container(self):
        checks = run_case.grade(self.case, self.observed)
        self.assertTrue(all(check["passed"] for check in checks.values()))

        self.observed["jobs"][0]["steps"][0]["properties"].pop("docker-image")
        self.observed["properties"] = {"java.version": "25.0.1"}
        checks = run_case.grade(self.case, self.observed)
        self.assertTrue(checks["toolchain"]["passed"])
        self.assertFalse(checks["containerImage"]["passed"])

        self.observed["jobs"][0]["steps"][0]["properties"]["docker-image"] = "eclipse-temurin:21-jdk"
        checks = run_case.grade(self.case, self.observed)
        self.assertFalse(checks["containerImage"]["passed"])


if __name__ == "__main__":
    unittest.main()
