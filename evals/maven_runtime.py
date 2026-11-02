"""Read Maven JVM launch evidence without retaining log text or host paths."""

import re


STATUSES = {"verified", "mismatch", "missing", "ambiguous", "unavailable"}
JDK_MATCH_MODES = ("exact", "minimum")
MAVEN_MAIN = re.compile(
    r"(?:^|\s)org\.(?:codehaus\.plexus\.classworlds\.launcher\.Launcher"
    r"|apache\.maven\.cli\.MavenCli|apache\.maven\.cling\.MavenCling)(?=\s|$)"
)
START = re.compile(r'''^Starting:\s*(?:"([^"]+)"|'([^']+)'|(\S+))\s+(.*)$''')
STEP = re.compile(r"\bStep (\d+)/(\d+)\b")
JAVA_INFO = re.compile(r"^Java version:\s*([^,\s]+),.*\bruntime:\s*(.+?)\s*$", re.I)
MODEL_QUERY = re.compile(r"\borg\.jetbrains\.maven:info-maven3-plugin:[^:\s]+:info\b")


def java_major(version):
    match = re.fullmatch(r"(?:1\.)?([1-9]\d{0,2})(?:[._+\-][\w.+\-]+)?", version)
    return int(match[1]) if match else None


def jdk_major_matches(major, jdk, jdk_match="exact"):
    if type(major) is not int:
        return False
    if jdk_match == "exact":
        return major == int(jdk)
    if jdk_match == "minimum":
        return major >= int(jdk)
    return False


def java_home(executable):
    if executable.lower() in ("java", "java.exe"):
        return ""  # Java selected through PATH needs Maven's runtime record.
    path = executable.replace("\\", "/").rstrip("/")
    return re.sub(r"/bin/java(?:\.exe)?$", "", path, flags=re.I) if re.search(
        r"/bin/java(?:\.exe)?$", path, re.I) else None


def same_home(left, right):
    if re.match(r"^[A-Za-z]:/", left):
        return left.casefold() == right.casefold()
    return left == right


def path_major(home):
    # Only the installation directory counts, never an ancestor, a classpath,
    # a Maven watcher JDK, or an unrelated command-line property.
    installation = re.sub(r"/Contents/Home$", "", home, flags=re.I).rsplit("/", 1)[-1]
    versions = {int(value) for value in re.findall(
        r"(?:^|[-_])(?:java|jdk|openjdk|temurin|corretto|zulu)[-_]?"
        r"(?:1\.)?([1-9]\d{0,2})(?=[._+\-]|$)", installation, re.I)}
    return next(iter(versions)) if len(versions) == 1 else None


def log_messages(log):
    """Strip TeamCity download-log prefixes, preserving step boundaries."""
    current_step = None
    for line in log.splitlines():
        line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        line = re.sub(r"^\[[\d:.]+\]\s*(?:[A-Za-z]?:\s*)?", "", line)
        match = STEP.search(line)
        if match:
            current_step = (int(match[1]), int(match[2]))
        line = re.sub(r"^\[Step \d+/\d+\]\s*", "", line)
        yield current_step, line


def maven_log_messages(log):
    """Pair a Docker wrapper's printed exec command with its actual launch."""
    previous_step, in_script, command, pending = None, False, None, None
    for step, line in log_messages(log):
        if step != previous_step:
            in_script, command, pending = False, None, None
            previous_step = step
        if line == "Container script (to be run inside container):":
            in_script, command, pending = True, None, None
        elif in_script:
            if command is not None:
                command += " " + line
            elif line.startswith("exec "):
                command = line[5:]
            if command is not None:
                if command.endswith("\\"):
                    command = command[:-1]
                else:
                    pending, command, in_script = command, None, False
        if START.fullmatch(line):
            if pending is not None and re.search(r"\bdocker\s+exec\s", line):
                yield step, "Starting: " + pending
                in_script, command, pending = False, None, None
                continue
            in_script, command, pending = False, None, None
        yield step, line


def maven_runtime(log, jdk, step_count, step_indices=None, total_steps=None, jdk_match="exact"):
    """Require a known, matching JVM for every declared native Maven step.

    Accept the executable in a Maven launch command when its installation
    directory identifies a JDK version. For an unversioned installation, a
    Maven `Java version: ..., runtime: ...` record must identify that same home
    in that same step. A Docker wrapper may launch Java through PATH; Maven's
    runtime record must then identify its home and version. Standalone
    `java -version` output is never evidence. Exact matching is the default;
    minimum matching accepts newer majors while still rejecting conflicts
    within a single launch.
    """
    result = {"requiredMajor": int(jdk), "jdkMatch": jdk_match, "stepCount": step_count,
              "launchCount": 0, "verifiedLaunchCount": 0, "observedMajors": [],
              "status": "missing"}
    if not isinstance(log, str) or not log.strip():
        return result
    launches, information, active_launch = [], [], None
    for step, line in maven_log_messages(log):
        match = START.fullmatch(line)
        if match:
            active_launch = None
            # The native runner probes the POM before executing build goals.
            model_query = (MODEL_QUERY.search(match[4])
                           and re.search(r"\binfo\.\d+\.pom\.xml\b", match[4]))
            if MAVEN_MAIN.search(match[4]) and not model_query:
                home = java_home(next(value for value in match.groups()[:3] if value is not None))
                active_launch = len(launches)
                launches.append((step, home, path_major(home) if home else None))
        info = JAVA_INFO.fullmatch(line)
        if info and active_launch is not None and step == launches[active_launch][0]:
            information.append((active_launch, info[2].strip('"').replace("\\", "/").rstrip("/"),
                                java_major(info[1])))
    observed, missing, ambiguous = set(), False, False
    for index, (step, home, major) in enumerate(launches):
        versions = {major} if major is not None else set()
        for info_launch, info_home, info_major in information:
            if index == info_launch and home is not None:
                # Explicit conflicting Maven output wins even when Java
                # reports a resolved home different from the launch path.
                if info_major is not None and (major is not None
                                              or not jdk_major_matches(info_major, jdk, jdk_match)):
                    versions.add(info_major)
                if home and not same_home(home, info_home):
                    continue
                if not home and not re.match(r"^(?:/|[A-Za-z]:/)", info_home):
                    continue
                if info_major is None:
                    ambiguous = True
                else:
                    versions.add(info_major)
        observed.update(versions)
        ambiguous |= len(versions) > 1
        missing |= not versions
        result["verifiedLaunchCount"] += (len(versions) == 1 and
                                         all(jdk_major_matches(value, jdk, jdk_match) for value in versions))
    result.update(launchCount=len(launches), observedMajors=sorted(observed))
    scoped_steps = [step for step, _, _ in launches if step is not None]
    bound = (step_indices is None or
             (len(scoped_steps) == len(launches)
              and {step[0] for step in scoped_steps} == set(step_indices)
              and all(step[1] == total_steps for step in scoped_steps)))
    if any(not jdk_major_matches(value, jdk, jdk_match) for value in observed):
        result["status"] = "mismatch"
    elif (ambiguous or len(launches) > step_count
          or len(scoped_steps) != len(set(scoped_steps))):
        result["status"] = "ambiguous"
    elif not launches or missing or len(launches) != step_count or not bound:
        result["status"] = "missing"
    else:
        result["status"] = "verified"
    return result


def safe_maven_runtime(value):
    if (not isinstance(value, dict) or not isinstance(value.get("status"), str)
            or value["status"] not in STATUSES
            or value.get("jdkMatch", "exact") not in JDK_MATCH_MODES):
        return {}
    safe = {"status": value["status"], "jdkMatch": value.get("jdkMatch", "exact")}
    for key in ("buildId", "requiredMajor", "stepCount", "launchCount", "verifiedLaunchCount"):
        if type(value.get(key)) is int and value[key] >= 0:
            safe[key] = value[key]
    majors = value.get("observedMajors")
    safe["observedMajors"] = sorted({major for major in majors
                                    if type(major) is int and 0 < major < 1000}) if isinstance(majors, list) else []
    return safe


def maven_runtime_matches(observations, jobs, jdk, jdk_match="exact"):
    maven_jobs = [job for job in jobs if any(step.get("type") == "maven"
                                           for step in job.get("steps", []))]
    if not maven_jobs or not isinstance(observations, list) or len(observations) != len(maven_jobs):
        return False
    for raw, job in zip(observations, maven_jobs):
        item = safe_maven_runtime(raw)
        step_count = sum(step.get("type") == "maven" for step in job.get("steps", []))
        if (not isinstance(raw, dict) or raw.get("jobId") != job["id"]
                or item.get("status") != "verified" or item.get("requiredMajor") != int(jdk)
                or item.get("jdkMatch") != jdk_match or not item.get("observedMajors")
                or not all(jdk_major_matches(major, jdk, jdk_match) for major in item["observedMajors"])
                or not (item.get("stepCount") == item.get("launchCount")
                        == item.get("verifiedLaunchCount") == step_count)):
            return False
    return True
