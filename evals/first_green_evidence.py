"""Fail-closed first-green chain binding and safe, declaration-only JDK evidence."""

import re


VERIFICATION_ERROR_CATEGORIES = {
    "verification-no-pipeline", "verification-pipeline-ambiguous",
    "verification-chain-incomplete", "verification-observation-failed",
    "verification-invalid-script-steps",
    "verification-unexplained-head-failure",
    "build-not-queued", "build-wait-timeout", "build-queue-stalled",
}


def safe_verification_error(value):
    return value if isinstance(value, str) and value in VERIFICATION_ERROR_CATEGORIES else None


class EvidenceError(RuntimeError):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def pipeline_signature(document):
    # The server may normalize the display name; topology and settings must match.
    return {key: document.get(key) or {} for key in ("jobs", "parameters", "environment")}


def select_pipeline(definitions, source=None):
    """Never infer a verification pipeline from its name or greatest child ID."""
    candidates = list(definitions)
    if source is not None:
        candidates = [key for key, value in definitions.items()
                      if pipeline_signature(value) == pipeline_signature(source)]
    if len(candidates) != 1:
        raise EvidenceError("verification-pipeline-ambiguous")
    return candidates[0], "source-matched" if source is not None else "unique-pipeline"


def chain_nodes(tree, head_id, pipeline_id):
    if tree.get("id") != head_id or tree.get("buildTypeId") != pipeline_id:
        raise EvidenceError("verification-chain-incomplete")
    found = {}

    def visit(node, ancestors):
        build_id = node.get("id")
        if (type(build_id) is not int or build_id <= 0 or build_id in ancestors
                or not isinstance(node.get("buildTypeId"), str)
                or node.get("state") not in ("queued", "running", "finished")
                or not isinstance(node.get("dependencies"), list)):
            raise EvidenceError("verification-chain-incomplete")
        if any(not isinstance(child, dict) for child in node["dependencies"]):
            raise EvidenceError("verification-chain-incomplete")
        identity = {key: node.get(key) for key in ("id", "buildTypeId", "state", "status")}
        identity["dependencies"] = [child.get("id") for child in node["dependencies"]]
        if build_id in found:
            if identity != found[build_id]:
                raise EvidenceError("verification-chain-incomplete")
        else:
            found[build_id] = identity
        for child in node["dependencies"]:
            if not isinstance(child, dict):
                raise EvidenceError("verification-chain-incomplete")
            visit(child, ancestors | {build_id})

    visit(tree, set())
    return list(found.values())


def bind_jobs(jobs, builds, nodes):
    """Bind YAML jobs by name; bind TeamCity test batches by tree parent.

    A batch is an extra build of a declared parallel job, not another YAML
    declaration. Unknown builds, ambiguous names, and missing jobs fail closed.
    """
    declared = {job["name"]: {"job": job, "members": [], "batches": []}
                for job in jobs}
    by_id = {build["id"]: build for build in builds}
    if (not jobs or len(declared) != len(jobs) or len(by_id) != len(builds)
            or set(by_id) != {node["id"] for node in nodes[1:]}):
        raise EvidenceError("verification-chain-incomplete")

    for build in builds:
        name = build.get("buildType", {}).get("name")
        if name in declared:
            declared[name]["members"].append(build)

    if any(not group["members"] or len({member["buildTypeId"]
                                          for member in group["members"]}) != 1
           for group in declared.values()):
        raise EvidenceError("verification-chain-incomplete")

    for build in builds:
        if build.get("buildType", {}).get("name") in declared:
            continue
        match = re.fullmatch(r"Batch ([1-9]\d*)", build.get("buildType", {}).get("name") or "")
        parents = {by_id[node["id"]]["buildType"]["name"]
                   for node in nodes[1:]
                   if node["id"] in by_id and build["id"] in node["dependencies"]
                   and by_id[node["id"]]["buildType"]["name"] in declared}
        if (not match or len(parents) != 1
                or next(iter(parents)) not in declared):
            raise EvidenceError("verification-chain-incomplete")
        group = declared[next(iter(parents))]
        parallelism = group["job"].get("jobProperties", {}).get("parallelism")
        if (type(parallelism) is not int or parallelism < 2
                or int(match.group(1)) > parallelism):
            raise EvidenceError("verification-chain-incomplete")
        group["batches"].append(build)

    for group in declared.values():
        names = [build["buildType"]["name"] for build in group["batches"]]
        if len(names) != len(set(names)):
            raise EvidenceError("verification-chain-incomplete")
    return list(declared.values())


def jdk_selectors(mapping, parameter=False):
    allowed = ("env.JAVA_HOME", "env.JDK_HOME") if parameter else ("JAVA_HOME", "JDK_HOME")
    return {key: value for key, value in (mapping or {}).items()
            if key in allowed and isinstance(value, str)}


def jdk_evidence(properties, jdk, jobs=None):
    version = re.compile(rf"(?<!\d){re.escape(jdk)}(?!\d)")
    # A selected home or available JDK is not a measured runtime version.
    runtime = [str(value) for key, value in properties.items()
               if key in ("java.version", "java.specification.version")]
    runtime_verified = bool(runtime) and all(version.search(value) for value in runtime)
    matched_jobs, evidence = 0, []
    for job in jobs or []:
        selectors = list(jdk_selectors(job.get("environment")).values())
        selectors += list(jdk_selectors(job.get("parameters"), parameter=True).values())
        images = [step.get("properties", {}).get("docker-image", "")
                  for step in job.get("steps", [])]
        images = [image for image in images if isinstance(image, str)
                  and re.search(r"(?i)java|jdk|openjdk|temurin", image)]
        choices = selectors + images
        if choices and all(version.search(value) for value in choices):
            matched_jobs += 1
            evidence.append("declared-java-home" if selectors else "declared-docker-image")
    declared_match = bool(jobs) and matched_jobs == len(jobs)
    # Contradictory runtime evidence must override a declaration.
    matched = runtime_verified if runtime else declared_match
    return matched, evidence, {
        "requiredMajor": int(jdk), "declaredMatch": declared_match,
        "runtimeVerified": runtime_verified, "declaredJobCount": matched_jobs,
        "jobCount": len(jobs or []),
    }


def observe_chain(tc, project_id, build, required_jdk):
    members = []
    for node in build["nodes"]:
        if node["id"] == build["id"]:
            continue
        member = tc.build(node["id"])
        if any(member.get(key) != node[key] for key in ("id", "buildTypeId", "state", "status")):
            raise EvidenceError("verification-chain-incomplete")
        members.append(member)
    groups = bind_jobs(tc.jobs(project_id, build["pipelineId"]), members, build["nodes"])
    jobs = [group["job"] for group in groups]
    artifacts, all_tests, diagnostics, job_results = [], [], [], []
    observations = {}
    for member in members:
        tests = tc.test_results(member["id"])
        published_artifacts = tc.artifacts(member["id"])
        observations[member["id"]] = (tests, published_artifacts)
        diagnostics.append({"id": member["id"], "state": member.get("state"),
                            "status": member.get("status"), "testCount": len(tests),
                            "successfulTestCount": sum(test["status"] == "SUCCESS"
                                                       and not test["ignored"] for test in tests),
                            "artifactCount": len(published_artifacts)})
    for group in groups:
        # Parallel parent jobs report the same tests as their child batches.
        test_builds = group["batches"] or group["members"]
        job_tests = [test for member in test_builds
                     for test in observations[member["id"]][0]]
        job_artifacts = [artifact for member in group["members"] + group["batches"]
                         for artifact in observations[member["id"]][1]]
        job_results.append({"job": group["job"],
                            "status": "SUCCESS" if all(member["status"] == "SUCCESS"
                                                       for member in group["members"] + group["batches"])
                                      else "FAILURE",
                            "tests": job_tests, "artifacts": job_artifacts})
        all_tests.extend(job_tests)
        artifacts.extend(job_artifacts)
    _, _, jdk = jdk_evidence({}, required_jdk, jobs)
    head = next(node for node in build["nodes"] if node["id"] == build["id"])
    metadata = None
    if head.get("status") in ("FAILURE", "ERROR"):
        try:
            metadata = tc.build(head["id"])
        except (RuntimeError, OSError, ValueError):
            # A diagnostics read failure is not evidence of zero problems.
            pass
        if metadata is not None and any(
            metadata.get(key) != head[key] for key in ("id", "buildTypeId", "state", "status")
        ):
            raise EvidenceError("verification-chain-incomplete")
    return {
        "testCount": len(all_tests), "tests": all_tests, "jobResults": job_results,
        "artifacts": artifacts, "properties": {},
        "jobs": jobs, "attempts": build["attempts"], "buildStatus": build["status"],
    }, {
        "headId": build["id"], "selection": build["selection"], "builds": diagnostics,
        "testCount": len(all_tests), "artifactCount": len(artifacts),
        "attempts": build["attempts"], "jdk": jdk,
        "terminalChain": terminal_chain_diagnostics(build["nodes"], build["id"], metadata),
    }


def terminal_chain_diagnostics(nodes, head_id, metadata=None):
    """Preserve head/child disagreement without treating status text as a cause."""
    head = next(node for node in nodes if node["id"] == head_id)
    children = [node for node in nodes if node["id"] != head_id]
    terminal = bool(children) and all(node["state"] == "finished" for node in nodes)
    anomaly = (terminal and head.get("status") in ("FAILURE", "ERROR")
               and all(node.get("status") == "SUCCESS" for node in children))
    problems = (metadata or {}).get("problemOccurrences")
    count = problems.get("count") if isinstance(problems, dict) else None
    if type(count) is not int or count < 0:
        count = None
    recorded = bool(count) or (isinstance(problems, dict)
                              and bool(problems.get("problemOccurrence")))
    # These indicate available structured evidence, not a diagnosed root cause.
    recorded = recorded or (metadata or {}).get("failedToStart") is True
    recorded = recorded or bool((metadata or {}).get("canceledInfo"))
    safe = {
        "headId": head_id, "headState": head["state"], "headStatus": head.get("status"),
        "childCount": len(children),
        "successfulChildCount": sum(node.get("status") == "SUCCESS"
                                    and node["state"] == "finished" for node in children),
        "failurePattern": "head-failed-children-succeeded" if anomaly else "none",
        "problemEvidence": "recorded" if recorded else "unavailable",
        "requiresInvestigation": anomaly,
        "children": children,
    }
    if count is not None:
        safe["problemCount"] = count
    return safe_terminal_chain_diagnostics(safe)


def safe_terminal_chain_diagnostics(value):
    if not isinstance(value, dict):
        return {}
    safe = {key: value[key] for key in (
        "headId", "childCount", "successfulChildCount", "problemCount"
    ) if type(value.get(key)) is int and value[key] >= 0}
    for key, allowed in (
        ("headState", ("queued", "running", "finished")),
        ("headStatus", ("SUCCESS", "FAILURE", "ERROR", "UNKNOWN", "CANCELED")),
        ("failurePattern", ("none", "head-failed-children-succeeded")),
        ("problemEvidence", ("recorded", "unavailable")),
    ):
        if isinstance(value.get(key), str) and value[key] in allowed:
            safe[key] = value[key]
    if type(value.get("requiresInvestigation")) is bool:
        safe["requiresInvestigation"] = value["requiresInvestigation"]
    if isinstance(value.get("children"), list):
        safe["children"] = []
        for child in value["children"]:
            if not isinstance(child, dict) or type(child.get("id")) is not int or child["id"] <= 0:
                continue
            item = {"id": child["id"]}
            if child.get("state") in ("queued", "running", "finished"):
                item["state"] = child["state"]
            if child.get("status") in ("SUCCESS", "FAILURE", "ERROR", "UNKNOWN", "CANCELED"):
                item["status"] = child["status"]
            safe["children"].append(item)
    return safe


def safe_verification_diagnostics(value):
    """No names, scripts, properties, paths, status text, or server payloads."""
    if not isinstance(value, dict):
        return {}
    safe = {}
    for key in ("headId", "testCount", "artifactCount", "attempts"):
        if type(value.get(key)) is int and value[key] >= 0:
            safe[key] = value[key]
    if value.get("selection") in ("source-matched", "unique-pipeline"):
        safe["selection"] = value["selection"]
    terminal = safe_terminal_chain_diagnostics(value.get("terminalChain"))
    if terminal:
        safe["terminalChain"] = terminal
    safe["builds"] = []
    for item in value.get("builds", []) if isinstance(value.get("builds"), list) else []:
        if not isinstance(item, dict) or type(item.get("id")) is not int:
            continue
        record = {"id": item["id"]}
        for key in ("testCount", "successfulTestCount", "artifactCount"):
            if type(item.get(key)) is int and item[key] >= 0:
                record[key] = item[key]
        if item.get("state") in ("queued", "running", "finished"):
            record["state"] = item["state"]
        if item.get("status") in ("SUCCESS", "FAILURE", "ERROR", "UNKNOWN", "CANCELED"):
            record["status"] = item["status"]
        safe["builds"].append(record)
    jdk = value.get("jdk")
    if isinstance(jdk, dict):
        safe["jdk"] = {key: jdk[key] for key in ("requiredMajor", "declaredJobCount", "jobCount")
                       if type(jdk.get(key)) is int and jdk[key] >= 0}
        safe["jdk"].update({key: jdk[key] for key in ("declaredMatch", "runtimeVerified")
                            if type(jdk.get(key)) is bool})
    return safe
