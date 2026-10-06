---
name: teamcity-jdk-selection
version: 1.0.0
description: Use when configuring or repairing a TeamCity job that needs a specific JDK, including agent selection, JAVA_HOME, container fallback, and runtime verification.
---

# Select a JDK for a TeamCity Job

Match the repository's required JDK to the Java that the job actually uses.
Agent eligibility and Java selection are separate decisions.

## Find the required JDK

Read `pom.xml`, Gradle build and toolchain files, and repository documentation.
Resolve conflicting requirements before configuring the job. Record the JDK
needed to run each build job; a Java language or bytecode target can be a
different version.

## Use a JDK installed on an agent

Inspect compatible agents on the target TeamCity server. At startup, a
TeamCity agent searches for installed JDKs and may publish a parameter such as
`env.JDK_21_0` whose value is the JDK home directory. Agent administrators can
also define parameters. The name `env.JDK_21_0` and path `/opt/jdk-21` are
examples: inspect the actual agent's **Parameters** tab or a supported tool.
An installed JDK that the agent has not detected does not prove that this
parameter exists. See [TeamCity's Java-related agent parameters](https://www.jetbrains.com/help/teamcity/predefined-build-parameters.html#Java-Related+Environment+Variables).
The CLI command `teamcity agent jobs <agent-id> --incompatible --json` can
report unmet requirements, but it does not list parameter values.

For a host build:

1. Limit scheduling to agents with the observed JDK parameter. TeamCity checks
   agent requirements before a job starts. A `%env.JDK_21_0%` reference may
   create an implicit requirement; inspect job compatibility and add an
   explicit `exists` requirement only if needed.
2. Set the job's `env.JAVA_HOME` to the observed parameter, for example
   `%env.JDK_21_0%`. TeamCity resolves it to that agent's JDK home directory.
   If the parameter is `/opt/jdk-21`, the build receives
   `JAVA_HOME=/opt/jdk-21`.
   The requirement alone does not select Java for Maven or Gradle.
3. Check whether the Maven or Gradle step has its own JDK setting that
   overrides `JAVA_HOME`. Read back the saved job configuration and confirm
   both scheduling and Java selection before queueing.

On Unix, verify `"$JAVA_HOME/bin/java" -version` during the build. On Windows,
use `"%JAVA_HOME%\bin\java.exe" -version`. A bare `java` command uses `PATH`
and can select another installation. Check the Maven or Gradle runtime output
when a runner-specific JDK setting exists.

## Use a container or report a blocker

If no suitable agent exposes the required host JDK, a Linux-container-safe
job can run on a verified Docker-capable agent with a JDK image pinned to the
required major version. The Java executable is inside the container: require
Docker capability for scheduling, not a host `env.JDK_21_0` parameter, and
verify the Java version inside the container.

If neither a suitable host JDK nor a suitable container route exists, report
the missing capability and the agent or image change needed before retrying.
Native macOS or iOS work requires a compatible macOS agent and runtime; a
Linux container is not a substitute.

For configuration-only work, stop after read-back and agent compatibility
checks. For a requested build, report the observed Java version and final
build state; do not treat a queued job as verification.
