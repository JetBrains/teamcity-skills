import importlib.util
import os
import pathlib
import sys
import tempfile
import unittest


EVALS = pathlib.Path(__file__).resolve().parents[1]


def load_runner():
    spec = importlib.util.spec_from_file_location("run_case_cli_lifecycle", EVALS / "run_case.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_case = load_runner()


class TeamCityCliLifecycleTest(unittest.TestCase):
    def test_lifecycle_uses_cli_for_project_markers_and_stored_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            program = root / "teamcity.py"
            program.write_text(
                "import json, sys\n"
                "args = sys.argv[1:]\n"
                "if args[:2] == ['project', 'create']:\n"
                "    print(json.dumps({'id': 'Eval_Project'}))\n"
                "elif args[:2] == ['pipeline', 'list']:\n"
                "    print(json.dumps({'count': 1, 'pipeline': [{'id': 'Eval_Pipeline'}]}))\n"
                "elif args[:2] == ['pipeline', 'pull']:\n"
                "    print('name: test\\njobs:\\n  verify:\\n    steps:\\n      - type: gradle\\n        tasks: test')\n"
            )
            cli = root / "teamcity"
            cli.write_text(f"#!{sys.executable}\n" + program.read_text())
            cli.chmod(0o755)

            tc = run_case.TeamCity(
                str(cli), "https://teamcity.example", "lifecycle-canary", os.environ
            )
            self.assertEqual("Eval_Project", tc.create_project("Eval", "Parent"))
            tc.mark_temporary_project("Eval_Project", 1)
            jobs = tc.jobs("Eval_Project")

            self.assertEqual(["Eval_Pipeline/verify"], [job["id"] for job in jobs])
            self.assertEqual("gradle", jobs[0]["steps"][0]["type"])

    def test_runner_has_no_direct_teamcity_http_client(self):
        source = (EVALS / "run_case.py").read_text()
        self.assertNotIn("urllib.request", source)
        self.assertNotIn("/app/rest/", source)


if __name__ == "__main__":
    unittest.main()
