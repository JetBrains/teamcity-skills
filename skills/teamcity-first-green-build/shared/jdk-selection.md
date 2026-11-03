# JDK Selection For A TeamCity Job

Use this guide when a build job requires a specific JDK. Match the repository's
required JDK to the Java that the job actually uses. Agent eligibility and Java
selection are separate decisions.

## Find The Required JDK

Read `pom.xml`, Gradle build and toolchain files, and repository documentation.
Resolve conflicting requirements before configuring the job. Record the JDK
needed to run each build job; a Java language or bytecode target can be a
different version.

## Use A JDK Installed On An Agent

Inspect compatible agents on the target TeamCity server. At startup, a
TeamCity agent searches for installed JDKs and may publish a parameter such as
`env.JDK_21_0` whose value is the JDK home directory. Agent administrators can
also define parameters. The name `env.JDK_21_0` and path `/opt/jdk-21` are
examples: inspect the actual agent's **Parameters** tab or a supported tool.
An installed JDK that the agent has not detected does not prove that this
parameter exists. See [TeamCity's Java-related agent parameters](https://www.jetbrains.com/help/teamcity/predefined-build-parameters.html#Java-Related+Environment+Variables).
The CLI command `teamcity agent jobs <agent-id> --incompatible --json` can
report unmet requirements, but it does not list parameter values. Treat a key
inferred from the Java version as a candidate until agent parameters or job
compatibility confirm it.

When using an agent's installed JDK:

1. Limit scheduling to agents with the observed JDK parameter. TeamCity checks
   agent requirements before a job starts. A `%env.JDK_21_0%` reference may
   create an implicit requirement; inspect job compatibility and add an
   explicit `exists` requirement only if needed. A build step that searches
   host paths or calls `setParameter` runs too late to select an agent.
2. Set the job's `parameters.env.JAVA_HOME` to the observed parameter, for
   example `%env.JDK_21_0%`. TeamCity resolves it to that agent's JDK home
   directory. If the parameter is `/opt/jdk-21`, the build receives
   `JAVA_HOME=/opt/jdk-21`. The requirement alone does not select Java for
   Maven or Gradle.
3. Check whether the Maven or Gradle step has its own JDK setting that
   overrides `JAVA_HOME`. Read back the saved Pipeline YAML and confirm both
   scheduling and Java selection on every affected job before queueing.

## Download A JDK During The Build

If no suitable agent has the required JDK, first add a setup step that downloads
and unpacks it before the Maven or Gradle steps. A missing preinstalled JDK
alone is not an infrastructure blocker. Keep a container setup already
required by the repository or user.

1. Select an agent with the required OS, architecture, and other job
   capabilities. Check that policy, network access, writable storage, and
   download/extraction tools allow setup. The setup step must run without the
   JDK it is about to download.
2. Remove requirements and unresolved references to the missing host JDK,
   including `%env.JDK_21_0%`, from this provisioning route. Preserve unrelated
   requirements and check job compatibility again. A queued job cannot run
   its setup step to satisfy a pre-dispatch requirement.
3. Download an exact JDK release from an official vendor or approved mirror,
   matching the agent's OS and architecture. Verify its published checksum or
   signature before extraction. Unpack into a job-local writable directory,
   such as a subdirectory of TeamCity's build temp directory. Do not use
   `sudo`, change system Java, or modify the Java running the TeamCity agent.
4. Declare the job's `env.JAVA_HOME` with the intended unpacked JDK home and
   make subsequent Maven/Gradle steps use it. Account for archive layout,
   including `Contents/Home` on macOS. A shell `export` in the setup step does
   not persist into later steps. If the path is determined during setup,
   update the predeclared parameter with a TeamCity `setParameter` service
   message for subsequent steps. Check runner-specific JDK overrides.
5. Fail the setup step on download, integrity, extraction, or Java-version
   errors. Run build/test steps only after setup succeeds. Provision the JDK
   in each affected job; do not assume jobs share a filesystem or agent.

## Use A Container As A Fallback

Use Docker when build-local download/provisioning is unavailable or has a
diagnosed setup failure. Record the reason, such as a policy restriction,
blocked download, or an incompatible JDK archive. A Linux-container-safe job
can then run on a verified Docker-capable agent with an official JDK image
pinned to the required major version. Run the build step inside that image.
The Java executable is inside the container: require Docker capability for
scheduling, not a host `env.JDK_21_0` parameter.

Report an infrastructure blocker only when the installed-JDK, build-local
download, and applicable container routes are all ruled out by evidence.
Report the missing capability and the agent or image change needed before
retrying.
The infrastructure owner must provide the selector and compatibility evidence
for the repaired environment. Native macOS or iOS work requires a compatible
macOS agent and runtime; a Linux container is not a substitute.

## Verify The Selected JDK

On Unix, verify `"$JAVA_HOME/bin/java" -version` during the build. On Windows
cmd, use `"%JAVA_HOME%\bin\java.exe" -version`. For containers, run the check
inside the build container. A bare `java` command uses `PATH` and can select
another installation. Check the Maven or Gradle runtime output, including
runner-specific JDK overrides, before claiming the required Java was used.

For configuration-only work, stop after read-back and agent compatibility
checks. For a requested build, report the observed Java version and final
build state; do not treat a queued job as verification.
