# Pipeline features

Add these to every onboarding pipeline, whether or not the workflow had them.
They are the part of the demonstration GitHub Actions cannot show.

## Test reports

Tests run from a script step are invisible. A Gradle, Maven, or .NET runner
imports test results by itself. When a test step has to stay a script
(Vitest, pytest, `go test`, bats), write JUnit XML and add an `xml-report`
job feature with `report-type: junit` and `rules:` for the report files. A
filter that matches nothing leaves the job green with 0 tests: a silent
failure. [Verify a build](verify-build.md) checks the count after every run.

## Artifacts

`files-publication` for the packaged output: what the workflow uploaded, or
the JAR or package the build produces. Every path is a file or a glob such as
`**/target/*.jar`. A bare directory fails the publish step and turns a green
job red.

Rules: `dir/**` drops the directory prefix; `=>` is rejected;
`publish-artifact: true` puts the files under `publish/`; `share-with-jobs`
defaults to true. Pack a directory into one archive to pass it.

On TC Cloud every artifact, and the job's `.shared_files.zip` with all shared
files together, is limited to 300 MB by default. A fat JAR or a Docker image
does not fit; never plan to pass one between jobs. Only a system
administrator can raise the limit. A compile-heavy project can share its
Gradle build cache archive with downstream jobs when it fits.

## Report tab

A custom tab is a `ReportTab` project feature on the project from
[Discover and connect](discover-and-connect.md), with
`startPage=publish/<file>.html`. There is no YAML key. The `Status` step
writes a one-page HTML summary of what the job built and tested; publish it
with `publish-artifact: true`. Add the feature once through `teamcity api`,
with the property names copied from an existing `ReportTab` feature on the
server. When there is none to copy, write a
[manual prerequisite](manual-prerequisites.md). Give the user the tab's link.

## Shape

```yaml
jobs:
  build:
    name: Build
    runs-on: Linux-Medium              # a value this server dispatches
    parameters:
      env.JAVA_HOME: "%env.JDK_17_0%"  # a key observed on an agent
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
    parameters:
      env.JAVA_HOME: "%env.JDK_17_0%"
    steps:
      - type: gradle
        name: Test
        tasks: test
      - type: script
        name: Status
        script-content: |-
          echo "##teamcity[buildStatus text='{build.status.text}, unit tests']"
```
