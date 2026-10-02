"""Supplement Pipeline schema validation without exposing script contents.

The server schema can accept arbitrary runner properties. This narrow check
only establishes that each script step has a usable source; it does not prove
shell syntax, checkout file existence, parameter resolution, or agent capacity.
"""

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
