"""Interpret CLI schema validation and check script sources without exposing YAML.

The server schema can accept arbitrary runner properties. This narrow check
only establishes that each script step has a usable source; it does not prove
shell syntax, checkout file existence, parameter resolution, or agent capacity.
"""

import re


SCHEMA_ERROR_CATEGORIES = {"schema-validation-error", "invalid-enum-value"}


def safe_schema_diagnostics(value):
    """Keep validation outcomes and source positions, never YAML or CLI text."""
    if not isinstance(value, dict) or value.get("status") not in ("valid", "invalid", "unavailable"):
        return {}
    safe = {"status": value["status"]}
    if type(value.get("errorCount")) is int and value["errorCount"] >= 0:
        safe["errorCount"] = value["errorCount"]
    safe["issues"] = [
        {"line": item["line"], "category": item["category"]}
        for item in value.get("issues", []) if isinstance(item, dict)
        and type(item.get("line")) is int and item["line"] > 0
        and isinstance(item.get("category"), str)
        and item["category"] in SCHEMA_ERROR_CATEGORIES
    ] if isinstance(value.get("issues"), list) else []
    return safe


class PipelineSchemaError(ValueError):
    def __init__(self, diagnostics):
        self.diagnostics = safe_schema_diagnostics(diagnostics)
        self.category = ("verification-invalid-pipeline-yaml"
                         if self.diagnostics.get("status") == "invalid"
                         else "verification-schema-validation-unavailable")
        super().__init__(self.category)


def pipeline_schema_result(completed, filename):
    """Interpret the CLI's text-only validator; unknown failures are not grades.

    CLI 1.3.0 prints a file-specific error count and line/path pairs for schema
    violations, but returns the same exit code for auth, schema and CLI errors.
    Only a recognized validation report establishes invalid agent output.
    """
    if completed.returncode == 0:
        return {"status": "valid", "errorCount": 0, "issues": []}
    output = re.sub(r"\x1b\[[0-9;]*m", "", completed.stderr or "")
    report = re.search(re.escape(str(filename)) + r" has ([1-9]\d*) error\(s\)\s*\n", output)
    if completed.returncode != 1 or report is None:
        raise PipelineSchemaError({"status": "unavailable"})
    issues = []
    for match in re.finditer(r"(?m)^\s*Line ([1-9]\d*):[^\n]*\n([^\n]*)", output[report.end():]):
        category = ("invalid-enum-value" if re.match(r"\s*value must be (?:one of |['\"])", match[2])
                    else "schema-validation-error")
        issues.append({"line": int(match[1]), "category": category})
    raise PipelineSchemaError({"status": "invalid", "errorCount": int(report[1]), "issues": issues})


SCRIPT_ISSUE_CATEGORIES = {
    "unsupported-script-key", "invalid-script-source-type",
    "missing-script-source", "conflicting-script-sources",
}


def script_step_diagnostics(jobs, *, raw=False):
    """Inspect stored YAML jobs or the adapter's normalized job records."""
    checked, issues = 0, []
    for job_index, job in enumerate(jobs, 1):
        for step_index, step in enumerate(job.get("steps") or [], 1):
            if not isinstance(step, dict) or step.get("type") != "script":
                continue  # General shape validation belongs to the server schema.
            checked += 1
            properties = step if raw else step.get("properties", {})
            if not isinstance(properties, dict):
                category = "invalid-script-source-type"
            elif "script" in properties:
                category = "unsupported-script-key"
            elif any(key in properties and not isinstance(properties[key], str)
                     for key in ("script-content", "script-file")):
                category = "invalid-script-source-type"
            else:
                sources = sum(bool(properties.get(key, "").strip())
                              for key in ("script-content", "script-file"))
                category = ("missing-script-source" if sources == 0 else
                            "conflicting-script-sources" if sources > 1 else None)
            if category:
                issues.append({"jobIndex": job_index, "stepIndex": step_index,
                               "category": category})
    return {"checkedScriptStepCount": checked, "invalidScriptStepCount": len(issues),
            "issues": issues}


def safe_script_diagnostics(value):
    """Publish only counts, one-based positions, and fixed error categories."""
    if not isinstance(value, dict):
        return {}
    safe = {key: value[key] for key in ("checkedScriptStepCount", "invalidScriptStepCount")
            if type(value.get(key)) is int and value[key] >= 0}
    if not safe:
        return {}
    safe["issues"] = [
        {key: item[key] for key in ("jobIndex", "stepIndex", "category")}
        for item in value.get("issues", []) if isinstance(item, dict)
        and all(type(item.get(key)) is int and item[key] > 0
                for key in ("jobIndex", "stepIndex"))
        and isinstance(item.get("category"), str)
        and item["category"] in SCRIPT_ISSUE_CATEGORIES
    ] if isinstance(value.get("issues"), list) else []
    return safe


class ScriptConfigurationError(ValueError):
    category = "verification-invalid-script-steps"

    def __init__(self, diagnostics):
        self.diagnostics = safe_script_diagnostics(diagnostics)
        positions = ", ".join(
            f"job {issue['jobIndex']} step {issue['stepIndex']}: {issue['category']}"
            for issue in self.diagnostics["issues"]
        )
        super().__init__(
            "Invalid Pipeline script parameters (" + positions + "). "
            "Use non-empty script-content for inline commands or script-file for a file, "
            "not script; specify only one source. Schema validation alone is insufficient."
        )


def validate_pipeline_scripts(document):
    jobs = document.get("jobs") if isinstance(document, dict) else None
    # The server's shape validator handles malformed/missing jobs and steps.
    diagnostics = script_step_diagnostics(
        [job for job in jobs.values() if isinstance(job, dict)]
        if isinstance(jobs, dict) else [], raw=True,
    )
    if diagnostics["issues"]:
        raise ScriptConfigurationError(diagnostics)
    return diagnostics
