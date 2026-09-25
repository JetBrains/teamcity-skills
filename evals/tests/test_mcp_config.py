import importlib.util
import json
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
    def test_config_uses_only_teamcity_oauth_endpoint(self):
        self.assertEqual(
            {
                "mcpServers": {
                    "teamcity": {
                        "type": "http",
                        "url": "https://teamcity-nightly.labs.intellij.net/app/mcp",
                    }
                }
            },
            mcp_config.config("https://teamcity-nightly.labs.intellij.net/"),
        )

    def test_config_rejects_non_https_or_embedded_query(self):
        for server in ("http://teamcity.example", "https://teamcity.example/?token=no"):
            with self.assertRaises(ValueError):
                mcp_config.endpoint(server)

    def test_cli_writer_produces_parseable_non_secret_json(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "mcp.json"
            subprocess.run(
                [
                    sys.executable,
                    str(EVALS / "write_teamcity_mcp_config.py"),
                    "--server", "https://teamcity.example",
                    "--output", str(output),
                ],
                check=True,
            )
            contents = json.loads(output.read_text())

        self.assertEqual("https://teamcity.example/app/mcp", contents["mcpServers"]["teamcity"]["url"])
        self.assertNotIn("headers", contents["mcpServers"]["teamcity"])


if __name__ == "__main__":
    unittest.main()
