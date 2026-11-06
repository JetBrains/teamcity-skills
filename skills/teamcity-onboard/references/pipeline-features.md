# Pipeline features

Add each feature below that the project can feed, whether the workflow had it or not.
The `Status` step and the report tab fit every pipeline.

## Test reports

Tests run from a script step are invisible. A Gradle, Maven, or .NET runner
imports test results by itself. When a test step has to stay a script
(Vitest, pytest, `go test`, bats), write JUnit XML and add an `xml-report`
job feature with `report-type: junit` and `rules:` for the report files.
Add the JUnit reporter next to the default one and keep the rest of the
test command unchanged.
`xml-report` also reads testng, surefire, nunit, mstest, trx, vstest,
google-test, and ctest. When the tool writes none of these, keep the tests
in the job, and declare in the report that TeamCity shows no count for it.
[Verify a build](verify-build.md) checks the count after every run.

## Artifacts

`files-publication` for the packaged output: what the workflow uploaded, or
the JAR or package the build produces.

Publishing (`publish-artifact: true`) puts the files under `publish/`.
- A path that matches a directory fails the publish and turns the job red
  with `Is a directory`: a bare directory such as `out`, or `dir/**` when
  `dir` has subdirectories. Use file globs only, such as `**/target/*.jar` or
  `dist/**/*.js`.
- The published path drops the part before the first wildcard:
  `globdir/**/*.txt` gives `publish/sub/g.txt`, and a single file
  `single/one.txt` gives `publish/one.txt`.
- Do not use `=>`: TeamCity adds its own `=> publish`, so the target folder
  never appears.

Sharing (`share-with-jobs`, true by default) works with a bare directory
too, and shared files keep their full paths: `out` arrives as `out/…` in
the next job, so a directory needs no archive. To share a directory without
publishing it, leave out `publish-artifact`. A later job gets shared files
only when its dependency has a `files:` list:
`dependencies: [{build: {files: [out]}}]`. It then gets all the shared files
of that job, whatever the list names. A plain `- build` only orders the
jobs.

On TC Cloud every artifact file, and the job's `.shared_files.zip` with all
shared files together, is limited to 1 GB by default. A bigger file fails
with "exceeds maximum allowed size".
Share a file only when a later job reads it. Set `share-with-jobs: false` on
files that are only published. Keep the shared files of a job well under the
limit.
A job publishes at most 1,000 files. Pack a big output, such as a `dist/` folder, into one archive.
A compile-heavy project can share its Gradle build cache archive with downstream jobs when it fits.

## Report tab

A custom tab is a `ReportTab` project feature on the project from
[Discover and connect](discover-and-connect.md), with
`startPage=publish/<file>.html`. There is no YAML key. The `Status` step
writes a one-page HTML summary of what the job built and tested; publish it
with `publish-artifact: true`. Add the feature once through `teamcity api`,
with the property names copied from an existing `ReportTab` feature on the
server. When there is none to copy, write a
[manual prerequisite](manual-prerequisites.md). Give the user the tab's link.

The tab shows what the project naturally has: a test or Allure report, an
E2E results table, coverage HTML, a Playwright or Cypress report with
screenshots, benchmark results, a packages overview. For an HTML report that
is a directory, point the tab into the zip:
`startPage=publish/<x>.zip!index.html`.

## Write and validate

- No YAML anchors (`&`, `*`). `pipeline validate` accepts them, but the push
  fails with a misleading error, such as
  `Field type is required for a step in job '<job>'`.
- Run `teamcity pipeline validate` on changed YAML, then push. Validate
  rejects hosted `runs-on` names the server accepts and misses what the
  server rejects. A push error is the real validation, but a passed push
  proves little: check `runs-on` as
  [Agents and runtimes](agents-and-runtimes.md) describes.

## Shape

```yaml
jobs:
  build:
    name: Build
    runs-on: Linux-Medium              # a value this server dispatches
    parameters:
      env.JAVA_HOME: "%env.JDK_17_0%"  # a key observed on an agent
    files-publication:
      - path: "build/libs/app.jar"
        publish-artifact: true
        share-with-jobs: false         # no later job reads it
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
