import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


EVALS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))

from teamcity_cli_bridge import BridgeError, CommandPolicy, TeamCityCliBridge


class TeamCityCliBridgeTest(unittest.TestCase):
    def policy(self, checkout):
        return CommandPolicy(
            "Eval_Project", checkout, False,
            pipeline_ids=lambda: ["Eval_Project_Pipeline"],
            job_ids=lambda: ["Eval_Project_Pipeline_Job"],
        )

    def test_policy_limits_writes_to_temporary_project(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = pathlib.Path(directory)
            policy = self.policy(checkout)

            policy.authorize(
                ["project", "vcs", "create", "--project", "Eval_Project"], checkout
            )
            policy.authorize(
                ["pipeline", "create", "verify", "--project", "Eval_Project"], checkout
            )
            policy.authorize(
                ["pipeline", "push", "Eval_Project_Pipeline", "pipeline.yml"], checkout
            )

            with self.assertRaises(BridgeError):
                policy.authorize(
                    ["project", "vcs", "create", "--project", "Other"], checkout
                )
            with self.assertRaises(BridgeError):
                policy.authorize(
                    ["pipeline", "push", "Other_Pipeline", "pipeline.yml"], checkout
                )

    def test_policy_rejects_rest_debug_and_build_writes_for_configuration_eval(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = pathlib.Path(directory)
            policy = self.policy(checkout)

            for arguments in (
                ["api", "/app/rest/server"],
                ["pipeline", "list", "--project", "Eval_Project", "--debug"],
                ["run", "start", "Eval_Project_Pipeline_Job"],
                ["auth", "login"],
            ):
                with self.subTest(arguments=arguments), self.assertRaises(BridgeError):
                    policy.authorize(arguments, checkout)

    def test_bridge_authenticates_cli_without_exposing_token_to_agent_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = root / "checkout"
            checkout.mkdir()
            fake_cli = root / "real-teamcity"
            fake_cli.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "assert os.environ.get('TEAMCITY_TOKEN') == 'bridge-canary'\n"
                "print(json.dumps({'arguments': sys.argv[1:], 'url': os.environ['TEAMCITY_URL']}))\n"
            )
            fake_cli.chmod(0o755)

            with TeamCityCliBridge(
                cli=str(fake_cli),
                server_url="https://teamcity.example",
                token="bridge-canary",
                workspace=root,
                checkout=checkout,
                target_project="Eval_Project",
                allow_build_writes=False,
                pipeline_ids=lambda: [],
                job_ids=lambda: [],
                base_env=os.environ,
            ) as bridge:
                agent_env = bridge.agent_environment(
                    {**os.environ, "TEAMCITY_TOKEN": "bridge-canary"}
                )
                outcome = subprocess.run(
                    ["teamcity", "auth", "status"], cwd=checkout, env=agent_env,
                    capture_output=True, text=True, check=True,
                )

            self.assertNotIn("TEAMCITY_TOKEN", agent_env)
            payload = json.loads(outcome.stdout)
            self.assertEqual(["auth", "status"], payload["arguments"])
            self.assertEqual("https://teamcity.example", payload["url"])


if __name__ == "__main__":
    unittest.main()
