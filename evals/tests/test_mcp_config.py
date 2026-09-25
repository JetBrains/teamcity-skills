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
