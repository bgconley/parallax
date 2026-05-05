import Foundation

public enum ParallaxRuntimeConfigError: Error, Equatable {
    case invalidBaseURL(String)
    case missingBearerToken
    case missingDevUserId
    case invalidDevUserId(String)
    case unsupportedAuthMode(String)
}

public struct ParallaxRuntimeConfig: Equatable, Sendable {
    public let apiBaseURL: URL
    public let auth: ParallaxAPIAuth
    public let activityId: UUID?
    public let activityName: String?
    public let deviceId: String
    public let preflightCheckText: String?

    public init(
        apiBaseURL: URL,
        auth: ParallaxAPIAuth,
        activityId: UUID? = nil,
        activityName: String? = nil,
        deviceId: String,
        preflightCheckText: String? = nil
    ) {
        self.apiBaseURL = apiBaseURL
        self.auth = auth
        self.activityId = activityId
        self.activityName = activityName
        self.deviceId = deviceId
        self.preflightCheckText = preflightCheckText
    }

    public static func load(
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) throws -> ParallaxRuntimeConfig? {
        guard let baseURLString = environment["PARALLAX_API_BASE_URL"], !baseURLString.isEmpty else {
            return nil
        }
        guard let baseURL = URL(string: baseURLString) else {
            throw ParallaxRuntimeConfigError.invalidBaseURL(baseURLString)
        }
        let authMode = environment["PARALLAX_AUTH_MODE"] ?? "dev_header"
        let auth: ParallaxAPIAuth
        switch authMode {
        case "external_bearer":
            guard let token = environment["PARALLAX_BEARER_TOKEN"], !token.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                throw ParallaxRuntimeConfigError.missingBearerToken
            }
            auth = .bearer(token: token)
        case "dev_header":
            guard let rawUserId = environment["PARALLAX_DEV_USER_ID"], !rawUserId.isEmpty else {
                throw ParallaxRuntimeConfigError.missingDevUserId
            }
            guard let userId = UUID(uuidString: rawUserId) else {
                throw ParallaxRuntimeConfigError.invalidDevUserId(rawUserId)
            }
            auth = .devHeader(userId: userId)
        default:
            throw ParallaxRuntimeConfigError.unsupportedAuthMode(authMode)
        }
        return ParallaxRuntimeConfig(
            apiBaseURL: baseURL,
            auth: auth,
            activityId: environment["PARALLAX_ACTIVITY_ID"].flatMap(UUID.init(uuidString:)),
            activityName: Self.nonEmpty(environment["PARALLAX_ACTIVITY_NAME"]),
            deviceId: environment["PARALLAX_DEVICE_ID"] ?? "ios-uat-device",
            preflightCheckText: Self.nonEmpty(environment["PARALLAX_PREFLIGHT_CHECK_TEXT"])
        )
    }

    private static func nonEmpty(_ value: String?) -> String? {
        guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines),
              !trimmed.isEmpty
        else {
            return nil
        }
        return trimmed
    }
}
