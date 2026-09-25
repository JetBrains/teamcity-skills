import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


EVALS = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mcp_config = load_module("teamcity_mcp_config_test", "write_teamcity_mcp_config.py")


class TeamCityMcpConfigTest(unittest.TestCase):
    def test_config_uses_teamcity_endpoint_and_bearer_header(self):
        self.assertEqual(
            {
                "mcpServers": {
                    "teamcity": {
                        "type": "http",
                        "url": "https://teamcity-nightly.labs.intellij.net/app/mcp",
                        "headers": {"Authorization": "Bearer test-token"},
                    }
                }
            },
            mcp_config.config("https://teamcity-nightly.labs.intellij.net/", "test-token"),
        )

    def test_config_rejects_non_https_or_embedded_query(self):
        for server in ("http://teamcity.example", "https://teamcity.example/?token=no"):
            with self.assertRaises(ValueError):
                mcp_config.endpoint(server)

    def test_config_rejects_an_empty_or_multiline_token(self):
        for token in ("", " \t", "one\ntwo"):
            with self.assertRaises(ValueError):
                mcp_config.config("https://teamcity.example", token)

    def test_local_probe_is_opt_in_and_token_free(self):
        contents = mcp_config.config(
            "https://teamcity.example", "test-token", with_local_probe=True,
        )

        probe = contents["mcpServers"]["probe"]
        self.assertEqual("stdio", probe["type"])
        self.assertEqual(sys.executable, probe["command"])
        self.assertEqual(1, len(probe["args"]))
        self.assertTrue(probe["args"][0].endswith("evals/fixtures/mcp_probe.py"))
        self.assertNotIn("headers", probe)

    def test_local_probe_serves_a_fixed_ping(self):
        fixture = EVALS / "fixtures" / "mcp_probe.py"
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-03-26",
            }},
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "ping", "arguments": {},
            }},
        ]
        completed = subprocess.run(
            [sys.executable, str(fixture)],
            input="\n".join(json.dumps(message) for message in messages) + "\n",
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        replies = [json.loads(line) for line in completed.stdout.splitlines()]

        self.assertEqual("2025-03-26", replies[0]["result"]["protocolVersion"])
        self.assertEqual("ping", replies[1]["result"]["tools"][0]["name"])
        self.assertEqual("ok", replies[2]["result"]["content"][0]["text"])

    def test_cli_writer_reads_token_only_from_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "mcp.json"
            environment = dict(os.environ, EVAL_MCP_TOKEN="test-token")
            subprocess.run(
                [
                    sys.executable,
                    str(EVALS / "write_teamcity_mcp_config.py"),
                    "--server", "https://teamcity.example",
                    "--output", str(output),
                ],
                env=environment,
                check=True,
            )
            contents = json.loads(output.read_text())

        self.assertEqual("https://teamcity.example/app/mcp", contents["mcpServers"]["teamcity"]["url"])
        self.assertEqual(
            "Bearer test-token",
            contents["mcpServers"]["teamcity"]["headers"]["Authorization"],
        )


if __name__ == "__main__":
    unittest.main()
