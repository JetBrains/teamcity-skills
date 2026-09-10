require "xcodeproj"

default_platform(:ios)

def app_dir
  File.expand_path("..", __dir__)
end

def project_path
  Dir[File.join(app_dir, "*.xcodeproj")].first ||
    UI.user_error!("No .xcodeproj found in #{app_dir}")
end

def detected_scheme
  schemes = Xcodeproj::Project.schemes(project_path)
  schemes.find { |scheme| scheme == File.basename(project_path, ".xcodeproj") } || schemes.first
end

def scheme_has_tests?(scheme)
  file = File.join(project_path, "xcshareddata", "xcschemes", "#{scheme}.xcscheme")
  return false unless File.exist?(file)

  test_action = Xcodeproj::XCScheme.new(file).test_action
  !test_action.nil? && !test_action.testables.empty?
end

def simulator_destination
  ENV.fetch("TC_IOS_SIMULATOR_DESTINATION").strip
end

def build_destination
  ENV.fetch("TC_IOS_BUILD_DESTINATION", "generic/platform=iOS").strip
end

platform :ios do
  desc "Run tests when the selected scheme defines testable targets, otherwise build"
  lane :verify do
    scheme = detected_scheme
    UI.user_error!("No shared Xcode scheme found for #{project_path}") if scheme.nil? || scheme.empty?
    UI.message("Project '#{project_path}', scheme '#{scheme}'")

    if scheme_has_tests?(scheme)
      test(scheme: scheme)
    else
      UI.message("The selected scheme has no testable targets; building it instead")
      build(scheme: scheme)
    end
  end

  desc "Build the app without signing"
  lane :build do |options|
    build_app(
      scheme: options[:scheme] || detected_scheme,
      configuration: "Release",
      skip_archive: true,
      skip_codesigning: true,
      destination: build_destination,
      clean: true,
      derived_data_path: "build"
    )
  end

  desc "Run the test suite on a discovered simulator destination"
  lane :test do |options|
    run_tests(
      scheme: options[:scheme] || detected_scheme,
      clean: true,
      destination: simulator_destination
    )
  end
end
