import Foundation
import ParallaxCore
import Testing

@Test func runtimeConfigDoesNotSynthesizeExampleActivityWhenSeedIsAbsent() throws {
    let config = try #require(try ParallaxRuntimeConfig.load(environment: [
        "PARALLAX_API_BASE_URL": "http://127.0.0.1:18000",
        "PARALLAX_AUTH_MODE": "dev_header",
        "PARALLAX_DEV_USER_ID": "11111111-1111-4111-8111-111111111111",
        "PARALLAX_DEVICE_ID": "ios-dynamic-test-device",
    ]))

    let reflected = Dictionary(uniqueKeysWithValues: Mirror(reflecting: config).children.compactMap { child in
        child.label.map { ($0, child.value) }
    })

    #expect(reflectedValue("activityId", as: UUID.self, in: reflected) == nil)
    #expect(reflectedValue("activityName", as: String.self, in: reflected) == nil)
    #expect(reflectedValue("preflightCheckText", as: String.self, in: reflected) == nil)
}

@Test func runtimeConfigKeepsExplicitUATSeedInputs() throws {
    let activityId = UUID(uuidString: "22222222-2222-4222-8222-222222222222")!
    let config = try #require(try ParallaxRuntimeConfig.load(environment: [
        "PARALLAX_API_BASE_URL": "http://127.0.0.1:18000",
        "PARALLAX_AUTH_MODE": "dev_header",
        "PARALLAX_DEV_USER_ID": "11111111-1111-4111-8111-111111111111",
        "PARALLAX_ACTIVITY_ID": activityId.uuidString,
        "PARALLAX_ACTIVITY_NAME": "UAT Dynamic Activity",
        "PARALLAX_DEVICE_ID": "ios-dynamic-test-device",
        "PARALLAX_PREFLIGHT_CHECK_TEXT": "Check the UAT dynamic supply",
    ]))

    let reflected = Dictionary(uniqueKeysWithValues: Mirror(reflecting: config).children.compactMap { child in
        child.label.map { ($0, child.value) }
    })

    #expect(reflectedValue("activityId", as: UUID.self, in: reflected) == activityId)
    #expect(reflectedValue("activityName", as: String.self, in: reflected) == "UAT Dynamic Activity")
    #expect(reflectedValue("preflightCheckText", as: String.self, in: reflected) == "Check the UAT dynamic supply")
}

@Test func runtimeSwiftSourcesDoNotEmbedExampleScenarioStrings() throws {
    let packageRoot = try iosPackageRoot()
    let runtimeRoots = [
        packageRoot.appending(path: "App"),
        packageRoot.appending(path: "Sources/ParallaxApp"),
        packageRoot.appending(path: "Sources/ParallaxCore"),
    ]
    let banned = [
        "Clean pots and pans",
        "Clean the kitchen",
        "sponge",
        "Load dishwasher",
        "Hand-wash pans",
        "Pack lunch",
        "Laundry",
        "NC2",
        "Alex",
    ]
    let allowedFilenames: Set<String> = [
        "PreviewFixtures.swift",
    ]

    let swiftFiles = runtimeRoots.flatMap { root in
        swiftFilesUnder(root).filter { !allowedFilenames.contains($0.lastPathComponent) }
    }
    var violations: [String] = []
    for file in swiftFiles {
        let source = try String(contentsOf: file, encoding: .utf8)
        for string in banned where source.localizedCaseInsensitiveContains(string) {
            violations.append("\(file.path): \(string)")
        }
    }

    #expect(violations == [])
}

@Test func runtimeSwiftSourcesDoNotUseEmptyButtonActions() throws {
    let packageRoot = try iosPackageRoot()
    let runtimeRoots = [
        packageRoot.appending(path: "App"),
        packageRoot.appending(path: "Sources/ParallaxApp"),
    ]
    let swiftFiles = runtimeRoots.flatMap(swiftFilesUnder)
    var violations: [String] = []
    for file in swiftFiles {
        let source = try String(contentsOf: file, encoding: .utf8)
        if source.contains("Button(\"") && source.contains(") {}") {
            violations.append(file.path)
        }
        if source.contains("Button {\n        } label:") || source.contains("Button {\n    } label:") {
            violations.append(file.path)
        }
    }

    #expect(violations == [])
}

private func iosPackageRoot() throws -> URL {
    var directory = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
    for _ in 0..<8 {
        if FileManager.default.fileExists(atPath: directory.appending(path: "Package.swift").path) {
            return directory
        }
        directory.deleteLastPathComponent()
    }
    throw Phase9RemediationTestError.packageRootNotFound
}

private func swiftFilesUnder(_ root: URL) -> [URL] {
    guard let enumerator = FileManager.default.enumerator(
        at: root,
        includingPropertiesForKeys: [.isRegularFileKey],
        options: [.skipsHiddenFiles]
    ) else {
        return []
    }
    return enumerator.compactMap { item in
        guard let url = item as? URL, url.pathExtension == "swift" else { return nil }
        return url
    }
}

private enum Phase9RemediationTestError: Error {
    case packageRootNotFound
}

private func reflectedValue<T>(
    _ key: String,
    as type: T.Type,
    in reflected: [String: Any]
) -> T? {
    guard let value = reflected[key] else { return nil }
    if let direct = value as? T {
        return direct
    }
    let optional = Mirror(reflecting: value)
    guard optional.displayStyle == .optional else {
        return nil
    }
    return optional.children.first?.value as? T
}
