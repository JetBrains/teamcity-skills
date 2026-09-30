"""Fail-closed first-green chain binding and safe, declaration-only JDK evidence."""

import re


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
        identity = {key: node.get(key) for key in ("id", "buildTypeId", "state", "status")}
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


def bind_jobs(jobs, builds):
    """Bind stored declarations to actual members via unique CLI job names.

    No parsing of undocumented virtual buildTypeId suffixes. A missing,
    duplicated, or foreign job is an explicit observation error, not a pass.
    """
    declared = {job["name"]: job for job in jobs}
    actual = {build.get("buildType", {}).get("name"): build for build in builds}
    if (not jobs or len(declared) != len(jobs) or len(actual) != len(builds)
            or set(actual) != set(declared)):
        raise EvidenceError("verification-chain-incomplete")
    return [declared[build["buildType"]["name"]] for build in builds]


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
    jobs = bind_jobs(tc.jobs(project_id, build["pipelineId"]), members)
    artifacts, test_count, diagnostics = [], 0, []
    for member in members:
        tests = tc.test_count(member["id"])
        published_artifacts = tc.artifacts(member["id"])
        test_count += tests
        artifacts.extend(published_artifacts)
        diagnostics.append({"id": member["id"], "state": member.get("state"),
                            "status": member.get("status"), "testCount": tests,
                            "artifactCount": len(published_artifacts)})
    _, _, jdk = jdk_evidence({}, required_jdk, jobs)
    return {
        "testCount": test_count, "artifacts": artifacts, "properties": {},
        "jobs": jobs, "attempts": build["attempts"], "buildStatus": build["status"],
    }, {
        "headId": build["id"], "selection": build["selection"], "builds": diagnostics,
        "testCount": test_count, "artifactCount": len(artifacts),
        "attempts": build["attempts"], "jdk": jdk,
    }


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
    safe["builds"] = []
    for item in value.get("builds", []) if isinstance(value.get("builds"), list) else []:
        if not isinstance(item, dict) or type(item.get("id")) is not int:
            continue
        record = {"id": item["id"]}
        for key in ("testCount", "artifactCount"):
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
