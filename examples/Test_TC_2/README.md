# TeamCity Kotlin Demo

Minimal Kotlin/JVM project prepared for TeamCity.

## Local build

Use the Gradle wrapper with JDK 21 as the Java launcher:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
./gradlew clean check jacocoTestReport build
```

The project also declares a Kotlin JVM toolchain for JDK 21, but Gradle still
uses the launcher JDK to compile the Kotlin build scripts. Launching Gradle with
newer JDKs, for example JDK 25, can fail before toolchain selection.

This now runs:

- `test` for unit tests
- `integrationTest` for end-to-end style verification
- `ktlintCheck` for formatting validation
- `detekt` for static analysis
- `jacocoTestCoverageVerification` for a minimum coverage gate

## Useful local commands

```bash
./gradlew test
./gradlew integrationTest
./gradlew ktlintCheck detekt
./gradlew check jacocoTestReport
docker build -t teamcity-kotlin-demo .
```

## What is included

- Gradle-based Kotlin/JVM build
- JUnit 5 unit tests
- Separate `integrationTest` source set and Gradle task
- `ktlint` formatting checks
- `detekt` static analysis
- JaCoCo coverage reports and verification
- Multi-stage Docker build for packaging the app
- TeamCity Pipelines YAML in `.teamcity.yml`

## Reports

After running `./gradlew check jacocoTestReport`, you can inspect:

- `build/reports/jacoco/test/html/index.html`
- `build/reports/tests/test/index.html`
- `build/reports/tests/integrationTest/index.html`

## TeamCity setup

1. Create a VCS root that points to this repository.
2. Enable Pipelines from `.teamcity.yml`.
3. Make sure the agent has JDK 21.
4. Run the `Build and Test` pipeline.

The project now exposes the quality and verification tasks you would typically wire into CI, but the actual pipeline orchestration is left up to you.

The pipeline contains a `Verify` job and a dependent `Build and Smoke Test
Container` job. Validate `.teamcity.yml` against the target TeamCity server
before relying on it for older or differently configured Pipelines
installations.
