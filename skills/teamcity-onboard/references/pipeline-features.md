# Pipeline features

Add each feature below that the project can feed, whether or not the
workflow had it. The `Status` step and the report tab fit every pipeline.
Test reports need test output in a format TeamCity reads. The artifact is
required whenever the project has a build command; see
[Project inspection](project-inspection.md). Say in the report which
features were left out, and why.

## Test reports

Tests run from a script step are invisible. A Gradle, Maven, or .NET runner
imports test results by itself. When a test step has to stay a script
(Vitest, pytest, `go test`, bats), write JUnit XML and add an `xml-report`
job feature with `report-type: junit` and `rules:` for the report files.
`xml-report` also reads testng, surefire, nunit, mstest, trx, vstest,
google-test, and ctest. When the tool writes none of these, keep the tests
in the job, and declare in the report that TeamCity shows no count for it.
A filter that matches nothing leaves the job green with 0 tests: a silent
failure. [Verify a build](verify-build.md) checks the count after every run.

## Artifacts

`files-publication` on the `Build` job for the shippable output: the JAR,
the package, the binary, or a web app's `dist/` or `build/` directory. What
the workflow uploaded is a hint, not the limit: a workflow that uploads
nothing still has output to publish. Every path is a file or a glob such as
`**/target/*.jar` or `dist/**`. A bare directory fails the
publish step and turns a green job red. A web app's output directory has
many files: pack it into one archive in the build step and publish the
archive, so the user downloads one file.

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
