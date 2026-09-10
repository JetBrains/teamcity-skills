# Kotlin Multiplatform And Mobile Builds

Use this route when the repository declares Kotlin Multiplatform or Compose
Multiplatform targets, contains an Android application, or contains an Xcode
project or workspace. Its purpose is to give the first verification build real
mobile coverage without treating signing or distribution as a default.

## Detect The Actual Targets

Inspect Gradle settings and module build files for Android and Kotlin targets,
then list Gradle tasks before choosing them. Locate an iOS app directory as
follows:

1. Prefer the shallowest directory named `iosApp`.
2. Otherwise select the shallowest directory that directly contains an
   `.xcodeproj`; use an `.xcworkspace` only if no project is found.
3. Do not scan into `.git`, `.gradle`, `.idea`, `build`, `out`,
   `node_modules`, `Pods`, or `DerivedData`.

For Xcode projects, prefer a shared scheme named after the project; otherwise
use the sole shared scheme. If several plausible schemes remain, obtain the
list on the macOS agent (`xcodebuild -list`) and select a scheme only with
evidence. Do not hardcode an `iosApp` path, scheme, simulator model, SDK, or
Xcode version merely because it worked in another repository.

When the Xcode scheme embeds a Kotlin Multiplatform framework, determine the
simulator target architecture from the Gradle targets and the selected macOS
agent before generating `xcodebuild`. A project with only
`iosSimulatorArm64` must run on an Arm64 macOS agent and pass
`ARCHS=arm64 ONLY_ACTIVE_ARCH=YES` to `xcodebuild`; otherwise Xcode may request
`x86_64` as well and the Gradle embed task will fail. For an x86_64-only or
multi-architecture project, choose the matching target and agent from the
repository and server evidence; do not carry `ARCHS=arm64` over as a default.

## Default First-Green Topology

Keep independent targets as separate jobs when agents permit parallelism.

- **Android job:** use the Gradle runner where the Pipeline schema supports it.
  Run the discovered debug assemble task and JVM/unit-test task. Publish the
  exact debug APK or AAB output only after confirming its path locally or from
  the build output.
- **iOS job:** query the target server's schema and macOS/Xcode agents or cloud
  images before setting `jobs.<ios-job-id>.runs-on`. Use the exact durable
  macOS/Xcode agent or image offered by that server, or stable self-hosted
  constraints accepted by its schema; do not use a generic macOS requirement or
  a transient VM name. Read back the YAML to verify it. Reuse a checked-in
  Fastlane setup when it already
  defines the project, scheme, and test flow; otherwise use a script step that
  runs the discovered `xcodebuild` commands. Build the app and run tests only
  for a scheme that has testable targets.
- **Shared/JVM job:** keep Kotlin common/JVM tests when the project defines
  them; mobile jobs do not replace common-code coverage.

Do not run Android instrumented tests unless a compatible emulator or device is
available. Do not call their absence a green mobile test result: report that
only unit tests and packaging were verified.

For iOS, a test command needs a simulator destination that exists on the
selected macOS agent. Discover it there; if the scheme has no test action, a
successful app build is useful coverage and the report must say that no iOS
tests existed or ran.

## Fastlane Template Ownership

The canonical runtime location for a generated Fastlane setup is the target
repository's detected iOS app directory:

- `<ios-app>/Gemfile`
- `<ios-app>/fastlane/Fastfile`

The skill includes reusable templates at `assets/kmp-ios/Gemfile` and
`assets/kmp-ios/build.Fastfile`. They are source templates, not a substitute
for checked-in build configuration. Copy them into the repository only when
the user has authorized a durable repository change; then show the generated
files and ensure they are committed with a VCS-backed pipeline. Do not
overwrite an existing Gemfile or Fastfile without explicit authorization.

For a server-stored, VCS-less Remote Run, prefer a short generated
`xcodebuild` script in the pipeline rather than creating untracked Fastlane
files solely for the build. If the user asks for the IDE-equivalent Fastlane
flow, create the two files above first and include them in the uploaded patch.

Before invoking the template's `verify` lane, set
`TC_IOS_SIMULATOR_DESTINATION` to a destination discovered on the selected
macOS agent. `TC_IOS_BUILD_DESTINATION` is optional; set it to an iOS Simulator
destination when the requested artifact must be installable in a simulator.

## Artifacts

Publish artifacts that a developer can use:

- Android: the generated debug APK/AAB.
- iOS simulator request: package the built `*.app` directory for
  `iphonesimulator` as a zip. A simulator app is not an IPA and is installable
  only into a compatible simulator architecture.
- iOS device build: publish the unsigned app bundle only as a build artifact;
  it cannot be installed on a physical device without signing.
- Compose Desktop: when the repository declares OS-specific native formats,
  keep the DMG, MSI, and DEB tasks on separate macOS, Windows, and Linux jobs
  and publish the matching output from each job. Do not run all three package
  tasks on one host or claim an artifact produced by another platform.
- Wasm/web: publish the browser distribution directory (or a deterministic
  archive of it) from the web job. Do not publish Gradle caches as the web
  deliverable.

Do not publish Gradle caches, DerivedData, or TeamCity's shared-files archive as
the primary mobile artifact.

## Signing And Distribution Are Separate

Never make Apple signing, an IPA, App Store Connect credentials, or TestFlight
upload part of the default first-green pipeline. They require explicit user
intent and protected credentials. When the user asks for TestFlight, use a
separate macOS signing job that consumes only TeamCity secure parameters, then
make the upload job depend on its IPA artifact. Validate certificate, team ID,
bundle ID, project/workspace, scheme, and export method before queuing it.

## Mobile Preconditions And Completion

Before queueing, verify that the selected TeamCity server exposes compatible
Linux/Android and macOS/Xcode environments when those jobs are generated. For
each platform-specific job, set the exact durable server-offered agent/image or
stable self-hosted selector supported by the live schema in
`jobs.<job-id>.runs-on`, then read the saved YAML back to verify it was applied.
Do not pin a transient cloud-VM name or reuse an agent choice from another
server. An iOS job must not be sent to a generic Linux agent.

The first-green outcome for a multi-target project reports each target
separately: Android build/tests/artifact, iOS build/tests/artifact, and
common/JVM tests. A missing macOS/Xcode agent is a blocker for iOS, not a reason
to claim that the whole KMP pipeline was validated.
