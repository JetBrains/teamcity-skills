# Pipeline features

Add these to every onboarding pipeline, whether or not the GitHub workflow had
them. They are the part of the demonstration that GitHub Actions cannot show.
Read [Build-step selection](build-step-selection.md) first for runner choice,
the Script Parameter Gate, and status messages.

## Dependency cache

`enable-dependency-cache: true` on each job. It replaces `actions/cache` and
`setup-gradle` caching.

## Parallel tests

`parallelism: <n>` on the job whose tests run through a Gradle, Maven, or
.NET runner. Use 3, or the number of compatible agents if that is smaller.
Below 2, leave `parallelism` out. TeamCity splits the tests into that many
batches once it has test history, so the first run collects history and later
runs show the split.

Keep packaging out of that job, because every batch runs the whole job. A
coverage gate above zero also fails in every batch, because each batch sees
only part of the tests. Keep such a gate out of the batched job, or choose a
module without one.

## Test reports

A Gradle, Maven, or .NET runner imports test results by itself. Only when a
test step has to stay a script, add an `xml-report` job feature with
`report-type: junit` and `rules:` for the report files.

## Artifacts

`files-publication` for the packaged output: what the workflow uploaded, or
the application JAR or package the build produces. Every path is a file or a
glob such as `**/target/*.jar` or `**/surefire-reports/*.xml`. A bare
directory fails the publish step and turns a green job red.

## Shape

```yaml
jobs:
  build:
    name: Build
    runs-on: Linux-Medium   # a value from this server's schema enum
    enable-dependency-cache: true
    parameters:
      env.JAVA_HOME: "%env.JDK_17_0%"   # a key observed on an agent
    files-publication:
      - path: "**/build/libs/*.jar"
        publish-artifact: true
    steps:
      - type: gradle
        name: Assemble
        tasks: assemble
  test:
    name: Test
    runs-on: Linux-Medium
    enable-dependency-cache: true
    parallelism: 3
    parameters:
      env.JAVA_HOME: "%env.JDK_17_0%"
    steps:
      - type: gradle
        name: Test
        tasks: test
```

Take the `runs-on` and `JAVA_HOME` values from
[Agents, JDK, and compatibility](agents-and-jdk.md).
