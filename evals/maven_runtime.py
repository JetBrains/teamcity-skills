"""Read Maven JVM launch evidence without retaining log text or host paths."""

import re


STATUSES = {"verified", "mismatch", "missing", "ambiguous", "unavailable"}
MAVEN_MAIN = re.compile(
    r"(?:^|\s)org\.(?:codehaus\.plexus\.classworlds\.launcher\.Launcher"
    r"|apache\.maven\.cli\.MavenCli|apache\.maven\.cling\.MavenCling)(?=\s|$)"
)
START = re.compile(r'''^Starting:\s*(?:"([^"]+)"|'([^']+)'|(\S+))\s+(.*)$''')
STEP = re.compile(r"\bStep (\d+)/(\d+)\b")
JAVA_INFO = re.compile(r"^Java version:\s*([^,\s]+),.*\bruntime:\s*(.+?)\s*$", re.I)


def java_major(version):
    match = re.fullmatch(r"(?:1\.)?([1-9]\d{0,2})(?:[._+\-][\w.+\-]+)?", version)
    return int(match[1]) if match else None


def java_home(executable):
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


def maven_runtime(log, jdk, step_count, step_indices=None, total_steps=None):
    """Require a known, matching JVM for every declared native Maven step.

    Accept the executable in a Maven launch command when its installation
    directory identifies a JDK version. For an unversioned installation, a
    Maven `Java version: ..., runtime: ...` record must identify that same home
    in that same step. Standalone `java -version` output is never evidence.
    """
    result = {"requiredMajor": int(jdk), "stepCount": step_count,
              "launchCount": 0, "verifiedLaunchCount": 0, "observedMajors": [],
              "status": "missing"}
    if not isinstance(log, str) or not log.strip():
        return result
    launches, information = [], []
    for step, line in log_messages(log):
        match = START.fullmatch(line)
        if match and MAVEN_MAIN.search(match[4]):
            home = java_home(next(value for value in match.groups()[:3] if value is not None))
            launches.append((step, home, path_major(home) if home else None))
        info = JAVA_INFO.fullmatch(line)
        if info:
            information.append((step, info[2].strip('"').replace("\\", "/").rstrip("/"),
                                java_major(info[1])))
    observed, missing, ambiguous = set(), False, False
    for step, home, major in launches:
        versions = {major} if major is not None else set()
        # An unscoped version record cannot identify one of several launches.
        peers = [launch for launch in launches if launch[0] == step]
        for info_step, info_home, info_major in information:
            if len(peers) == 1 and step == info_step and home:
                # Explicit conflicting Maven output wins even when Java
                # reports a resolved home different from the launch path.
                if info_major is not None and info_major != int(jdk):
                    versions.add(info_major)
                if not same_home(home, info_home):
                    continue
                if info_major is None:
                    ambiguous = True
                else:
                    versions.add(info_major)
        observed.update(versions)
        ambiguous |= len(versions) > 1
        missing |= not versions
        result["verifiedLaunchCount"] += versions == {int(jdk)}
    result.update(launchCount=len(launches), observedMajors=sorted(observed))
    scoped_steps = [step for step, _, _ in launches if step is not None]
    bound = (step_indices is None or
             (len(scoped_steps) == len(launches)
              and {step[0] for step in scoped_steps} == set(step_indices)
              and all(step[1] == total_steps for step in scoped_steps)))
    if observed - {int(jdk)}:
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
            or value["status"] not in STATUSES):
        return {}
    safe = {"status": value["status"]}
    for key in ("buildId", "requiredMajor", "stepCount", "launchCount", "verifiedLaunchCount"):
        if type(value.get(key)) is int and value[key] >= 0:
            safe[key] = value[key]
    majors = value.get("observedMajors")
    safe["observedMajors"] = sorted({major for major in majors
                                    if type(major) is int and 0 < major < 1000}) if isinstance(majors, list) else []
    return safe


def maven_runtime_matches(observations, jobs, jdk):
    maven_jobs = [job for job in jobs if any(step.get("type") == "maven"
                                           for step in job.get("steps", []))]
    if not maven_jobs or not isinstance(observations, list) or len(observations) != len(maven_jobs):
        return False
    for raw, job in zip(observations, maven_jobs):
        item = safe_maven_runtime(raw)
        step_count = sum(step.get("type") == "maven" for step in job.get("steps", []))
        if (not isinstance(raw, dict) or raw.get("jobId") != job["id"]
                or item.get("status") != "verified" or item.get("requiredMajor") != int(jdk)
                or item.get("observedMajors") != [int(jdk)]
                or not (item.get("stepCount") == item.get("launchCount")
                        == item.get("verifiedLaunchCount") == step_count)):
            return False
    return True
