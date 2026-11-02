"""Check Maven's version banner in the selected native runner's build log."""

import re


STEP = re.compile(r"\bStep (\d+)/(\d+)\b")
MAVEN_MAIN = re.compile(
    r"\borg\.(?:codehaus\.plexus\.classworlds\.launcher\.Launcher"
    r"|apache\.maven\.cli\.MavenCli|apache\.maven\.cling\.MavenCling)(?=\s|$)"
)
BANNER = re.compile(r"^Apache Maven (\d+\.\d+(?:\.\d+)?)(?:\s|$)")


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", value):
        return None
    parts = tuple(int(part) for part in value.split("."))
    return parts + (0,) * (3 - len(parts))


def maven_version(log, job, minimum):
    """Require a version from each actual Maven launch, excluding POM probes.

    A versioned installation path, M2_HOME, or a standalone script's banner
    does not prove which Maven ran the verification goals. No log text, paths,
    or command arguments leave this function.
    """
    indices = {index for index, step in enumerate(job.get("steps", []), 1)
               if step.get("type") == "maven"}
    result = {"status": "missing", "stepCount": len(indices), "launchCount": 0,
              "versions": []}
    required = version_tuple(minimum)
    if not isinstance(log, str) or not indices or required is None:
        return result
    launches, current_step, active, container_command = [], None, None, None
    in_container_script = False
    for line in log.splitlines():
        line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        line = re.sub(r"^\[[\d:.]+\]\s*(?:[A-Za-z]?:\s*)?", "", line)
        match = STEP.search(line)
        if match:
            step = (int(match[1]), int(match[2]))
            if step != current_step:
                active, container_command, in_container_script = None, None, False
            current_step = step
        line = re.sub(r"^\[Step \d+/\d+\]\s*", "", line)
        if line == "Container script (to be run inside container):":
            in_container_script, container_command = True, None
        elif in_container_script and line.startswith("exec "):
            container_command = line[5:]
        elif in_container_script and container_command and container_command.endswith("\\"):
            container_command = container_command[:-1] + " " + line
        if line.startswith("Starting:"):
            active = None
            command = line
            if re.search(r"\b(?:docker|podman)\s+exec\s", line) and container_command:
                command = container_command
            container_command, in_container_script = None, False
            probe = (re.search(r"\borg\.jetbrains\.maven:info-maven3-plugin:[^:\s]+:info\b", command)
                     and re.search(r"\binfo\.\d+\.pom\.xml\b", command))
            if (current_step and current_step[0] in indices
                    and current_step[1] == len(job["steps"])
                    and MAVEN_MAIN.search(command) and not probe):
                active = {"step": current_step[0], "versions": set()}
                launches.append(active)
        banner = BANNER.match(line)
        if banner and active is not None:
            active["versions"].add(banner[1])
    versions = sorted({value for launch in launches for value in launch["versions"]},
                      key=version_tuple)
    result.update(launchCount=len(launches), versions=versions)
    if any(version_tuple(value) < required for value in versions):
        result["status"] = "mismatch"
    elif (len(launches) != len(indices) or {item["step"] for item in launches} != indices
          or any(len(item["versions"]) != 1 for item in launches)):
        result["status"] = "missing"
    else:
        result["status"] = "verified"
    return result


def observe_maven_versions(tc, results, minimum):
    observations = []
    for item in results:
        job = item["job"]
        if not any(step.get("type") == "maven" for step in job.get("steps", [])):
            continue
        try:
            result = maven_version(tc.build_log(item["buildId"]), job, minimum)
        except (RuntimeError, OSError, ValueError):
            result = {**maven_version(None, job, minimum), "status": "unavailable"}
        observations.append({**result, "jobId": job["id"]})
    return observations


def maven_versions_match(observations, jobs, minimum):
    required = version_tuple(minimum)
    maven_jobs = [job for job in jobs if any(step.get("type") == "maven"
                                           for step in job.get("steps", []))]
    if (required is None or not maven_jobs or not isinstance(observations, list)
            or len(observations) != len(maven_jobs)):
        return False
    by_job = {item.get("jobId"): item for item in observations if isinstance(item, dict)}
    if len(by_job) != len(maven_jobs):
        return False
    for job in maven_jobs:
        item = by_job.get(job["id"], {})
        step_count = sum(step.get("type") == "maven" for step in job["steps"])
        versions = item.get("versions")
        if (item.get("status") != "verified"
                or item.get("stepCount") != step_count or item.get("launchCount") != step_count
                or not isinstance(versions, list) or not versions
                or any(version_tuple(value) is None or version_tuple(value) < required
                       for value in versions)):
            return False
    return True
