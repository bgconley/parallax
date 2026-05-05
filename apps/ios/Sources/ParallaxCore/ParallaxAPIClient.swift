import Foundation

public enum ParallaxAPIError: Error, Equatable {
    case invalidURL
    case invalidAuthConfiguration
    case requestFailed(statusCode: Int, body: String?)
    case invalidResponse
}

public enum ParallaxAPIAuth: Equatable, Sendable {
    case devHeader(userId: UUID)
    case bearer(token: String)

    public func apply(to request: inout URLRequest) throws {
        switch self {
        case let .devHeader(userId):
            request.setValue(userId.uuidString, forHTTPHeaderField: "X-Parallax-User-Id")
        case let .bearer(token):
            let trimmed = token.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else {
                throw ParallaxAPIError.invalidAuthConfiguration
            }
            request.setValue("Bearer \(trimmed)", forHTTPHeaderField: "Authorization")
        }
    }
}

public protocol ParallaxHTTPTransport: Sendable {
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse)
}

public struct URLSessionHTTPTransport: ParallaxHTTPTransport {
    private let urlSession: URLSession

    public init(urlSession: URLSession = .shared) {
        self.urlSession = urlSession
    }

    public func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let (data, response) = try await urlSession.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw ParallaxAPIError.invalidResponse
        }
        return (data, httpResponse)
    }
}

public struct ParallaxAPIClient: Sendable {
    public let baseURL: URL
    public let auth: ParallaxAPIAuth
    private let transport: any ParallaxHTTPTransport

    public init(baseURL: URL, userId: UUID, urlSession: URLSession = .shared) {
        self.baseURL = baseURL
        self.auth = .devHeader(userId: userId)
        self.transport = URLSessionHTTPTransport(urlSession: urlSession)
    }

    public init(baseURL: URL, auth: ParallaxAPIAuth, urlSession: URLSession = .shared) {
        self.baseURL = baseURL
        self.auth = auth
        self.transport = URLSessionHTTPTransport(urlSession: urlSession)
    }

    public init(baseURL: URL, auth: ParallaxAPIAuth, transport: any ParallaxHTTPTransport) {
        self.baseURL = baseURL
        self.auth = auth
        self.transport = transport
    }

    public func resolveActivityRequest(query: String, limit: Int = 5) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/activities/resolve",
            method: "POST",
            body: ResolveActivityBody(query: query, limit: limit)
        )
    }

    public func listActivitiesRequest(q: String? = nil, limit: Int = 25) throws -> URLRequest {
        var queryItems = [URLQueryItem(name: "limit", value: "\(limit)")]
        if let q, !q.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            queryItems.append(URLQueryItem(name: "q", value: q))
        }
        return try request(path: "/v1/activities", method: "GET", queryItems: queryItems)
    }

    public func getActivityRequest(activityId: UUID) throws -> URLRequest {
        try request(path: "/v1/activities/\(activityId.uuidString)", method: "GET")
    }

    public func createActivityRequest(
        displayName: String,
        mutation: MutationEnvelope,
        defaultTimingMode: MeasurementMode = .wholeTask,
        privacyClass: String = "normal"
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/activities",
            method: "POST",
            body: CreateActivityBody(
                mutation: mutation,
                displayName: displayName,
                defaultTimingMode: defaultTimingMode,
                privacyClass: privacyClass
            )
        )
    }

    public func createTimingSessionRequest(
        activityId: UUID,
        clientSessionId: String,
        mode: MeasurementMode,
        mutation: MutationEnvelope,
        intendedStartAt: Date? = nil,
        userPreEstimateSeconds: Int? = nil
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/timing/sessions",
            method: "POST",
            body: CreateTimingSessionBody(
                mutation: mutation,
                activityId: activityId,
                clientSessionId: clientSessionId,
                mode: mode,
                intendedStartAt: intendedStartAt,
                userPreEstimateSeconds: userPreEstimateSeconds
            )
        )
    }

    public func getTimingSessionRequest(sessionId: UUID) throws -> URLRequest {
        try request(path: "/v1/timing/sessions/\(sessionId.uuidString)", method: "GET")
    }

    public func appendTimingEventRequest(_ event: PendingTimingEvent) throws -> URLRequest {
        try appendTimingEventRequest(event, remoteSessionId: event.sessionId)
    }

    public func appendTimingEventRequest(
        _ event: PendingTimingEvent,
        remoteSessionId: UUID
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/timing/sessions/\(remoteSessionId.uuidString)/events",
            method: "POST",
            body: AppendTimingEventBody(
                mutation: event.mutation,
                eventType: event.eventType,
                clientTime: event.clientTime,
                timerElapsedSeconds: event.timerElapsedSeconds,
                timerActiveSeconds: event.timerActiveSeconds,
                payload: event.payload
            )
        )
    }

    public func completeTimingSessionRequest(
        sessionId: UUID,
        mutation: MutationEnvelope,
        completedAt: Date,
        timerElapsedSeconds: Int,
        timerActiveSeconds: Int
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/timing/sessions/\(sessionId.uuidString)/complete",
            method: "POST",
            body: CompleteTimingSessionBody(
                mutation: mutation,
                completedAt: completedAt,
                timerElapsedSeconds: timerElapsedSeconds,
                timerActiveSeconds: timerActiveSeconds,
                payload: [:]
            )
        )
    }

    public func reviewTimingSessionRequest(
        sessionId: UUID,
        mutation: MutationEnvelope,
        decision: ModelUpdateDecision,
        modelInclusion: ModelInclusion,
        scopes: [ReviewLearningScope],
        userNote: String?
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/timing/sessions/\(sessionId.uuidString)/review",
            method: "POST",
            body: ReviewTimingSessionBody(
                mutation: mutation,
                decision: decision,
                modelInclusion: modelInclusion,
                scopes: scopes,
                userNote: userNote
            )
        )
    }

    public func discardTimingSessionRequest(
        sessionId: UUID,
        mutation: MutationEnvelope,
        decision: ModelUpdateDecision,
        userNote: String?
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/timing/sessions/\(sessionId.uuidString)/discard",
            method: "POST",
            body: ReviewTimingSessionBody(
                mutation: mutation,
                decision: decision,
                modelInclusion: .exclude,
                scopes: [],
                userNote: userNote
            )
        )
    }

    public func createAnnotationRequest(
        sessionId: UUID,
        mutation: MutationEnvelope,
        rawText: String,
        occurredAt: Date,
        captureMethod: CaptureMethod
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/timing/sessions/\(sessionId.uuidString)/annotations",
            method: "POST",
            body: CreateAnnotationBody(
                mutation: mutation,
                inputMode: inputMode(for: captureMethod),
                rawText: rawText,
                occurredAt: occurredAt,
                privacyClass: "normal",
                metadata: ["capture_method": captureMethod.rawValue]
            )
        )
    }

    public func confirmExtractedEventRequest(
        eventId: UUID,
        mutation: MutationEnvelope,
        confirmationState: ExtractedEventConfirmationState
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/timing/extracted-events/\(eventId.uuidString)/confirm",
            method: "POST",
            body: ConfirmExtractedEventBody(
                mutation: mutation,
                confirmationState: confirmationState
            )
        )
    }

    public func correctExtractedEventRequest(
        eventId: UUID,
        mutation: MutationEnvelope,
        spanType: TemporalSpanType,
        frictionCategory: TemporalFrictionCategory,
        durationSeconds: Int? = nil,
        countPolicy: CountPolicy,
        countInWallTime: Bool,
        countInActiveTime: Bool,
        suggestedPreflightText: String? = nil,
        userNote: String? = nil
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/timing/extracted-events/\(eventId.uuidString)/correct",
            method: "POST",
            body: CorrectExtractedEventBody(
                mutation: mutation,
                spanType: spanType,
                frictionCategory: frictionCategory,
                durationSeconds: durationSeconds,
                countPolicy: countPolicy,
                countInWallTime: countInWallTime,
                countInActiveTime: countInActiveTime,
                suggestedPreflightText: suggestedPreflightText,
                userNote: userNote
            )
        )
    }

    public func createPreflightCheckRequest(
        activityId: UUID,
        mutation: MutationEnvelope,
        checkText: String,
        source: String = "user_created"
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/activities/\(activityId.uuidString)/preflight-checks",
            method: "POST",
            body: CreatePreflightCheckBody(
                mutation: mutation,
                checkText: checkText,
                source: source
            )
        )
    }

    public func getActivityProfileRequest(activityId: UUID) throws -> URLRequest {
        try request(path: "/v1/activities/\(activityId.uuidString)/profile", method: "GET")
    }

    public func listCheckpointsRequest(activityId: UUID) throws -> URLRequest {
        try request(path: "/v1/activities/\(activityId.uuidString)/checkpoints", method: "GET")
    }

    public func putCheckpointsRequest(
        activityId: UUID,
        mutation: MutationEnvelope,
        checkpoints: [CheckpointTemplateDTO]
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/activities/\(activityId.uuidString)/checkpoints",
            method: "PUT",
            body: PutCheckpointsBody(mutation: mutation, checkpoints: checkpoints)
        )
    }

    public func listPreflightChecksRequest(activityId: UUID) throws -> URLRequest {
        try request(path: "/v1/activities/\(activityId.uuidString)/preflight-checks", method: "GET")
    }

    public func listResourceDependenciesRequest(activityId: UUID) throws -> URLRequest {
        try request(path: "/v1/activities/\(activityId.uuidString)/resource-dependencies", method: "GET")
    }

    public func createTemporalQueryRequest(
        mutation: MutationEnvelope,
        question: String,
        activityId: UUID? = nil,
        timeWindow: String? = nil,
        includeRawQuotes: Bool = false
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/temporal/query",
            method: "POST",
            body: TemporalQueryBody(
                mutation: mutation,
                question: question,
                activityId: activityId,
                timeWindow: timeWindow,
                includeRawQuotes: includeRawQuotes
            )
        )
    }

    public func getTemporalQueryAnswerRequest(answerId: UUID) throws -> URLRequest {
        try request(path: "/v1/temporal/query/\(answerId.uuidString)", method: "GET")
    }

    public func listTimingReviewFlagsRequest(
        sessionId: UUID,
        status: TimingReviewFlagStatus? = nil
    ) throws -> URLRequest {
        try request(
            path: "/v1/timing/sessions/\(sessionId.uuidString)/review-flags",
            method: "GET",
            queryItems: status.map { [URLQueryItem(name: "status", value: $0.rawValue)] } ?? []
        )
    }

    public func updateTimingReviewFlagRequest(
        flagId: UUID,
        mutation: MutationEnvelope,
        status: TimingReviewFlagStatus,
        resolutionNote: String? = nil
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/timing/review-flags/\(flagId.uuidString)",
            method: "PATCH",
            body: UpdateTimingReviewFlagBody(
                mutation: mutation,
                status: status,
                resolutionNote: resolutionNote
            )
        )
    }

    public func decidePreflightCheckRequest(
        activityId: UUID,
        checkId: UUID,
        mutation: MutationEnvelope,
        decision: PreflightCheckDecision,
        snoozedUntil: Date? = nil,
        reason: String? = nil
    ) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/activities/\(activityId.uuidString)/preflight-checks/\(checkId.uuidString)/decision",
            method: "POST",
            body: DecidePreflightCheckBody(
                mutation: mutation,
                decision: decision,
                snoozedUntil: snoozedUntil,
                reason: reason
            )
        )
    }

    private func inputMode(for captureMethod: CaptureMethod) -> AnnotationInputMode {
        switch captureMethod {
        case .voice:
            return .voice
        case .quickChip:
            return .quickChip
        case .backgroundSignal:
            return .systemDetected
        case .reviewReconstruction:
            return .reviewNote
        case .manualButton, .lockScreenWidget, .watch, .shortcut, .nfcTag, .calendarImport:
            return .text
        }
    }

    public func send<T: Decodable>(_ request: URLRequest, decode type: T.Type) async throws -> T {
        let (data, response) = try await transport.data(for: request)
        guard (200..<300).contains(response.statusCode) else {
            let body = String(data: data, encoding: .utf8)
            throw ParallaxAPIError.requestFailed(statusCode: response.statusCode, body: body)
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(type, from: data)
    }

    private func request(
        path: String,
        method: String,
        queryItems: [URLQueryItem] = []
    ) throws -> URLRequest {
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw ParallaxAPIError.invalidURL
        }
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        if !queryItems.isEmpty {
            components?.queryItems = queryItems
        }
        guard let resolvedURL = components?.url else {
            throw ParallaxAPIError.invalidURL
        }
        var request = URLRequest(url: resolvedURL)
        request.httpMethod = method
        try auth.apply(to: &request)
        return request
    }

    private func jsonRequest<T: Encodable>(path: String, method: String, body: T) throws -> URLRequest {
        var request = try request(path: path, method: method)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(body)
        return request
    }
}

private struct ResolveActivityBody: Encodable {
    let query: String
    let limit: Int
}

private struct CreateActivityBody: Encodable {
    let mutation: MutationEnvelope
    let displayName: String
    let defaultTimingMode: MeasurementMode
    let privacyClass: String
}

private struct CreateTimingSessionBody: Encodable {
    let mutation: MutationEnvelope
    let activityId: UUID
    let clientSessionId: String
    let mode: MeasurementMode
    let intendedStartAt: Date?
    let userPreEstimateSeconds: Int?
}

private struct AppendTimingEventBody: Encodable {
    let mutation: MutationEnvelope
    let eventType: TimingEventType
    let clientTime: Date
    let timerElapsedSeconds: Int?
    let timerActiveSeconds: Int?
    let payload: [String: String]
}

private struct CompleteTimingSessionBody: Encodable {
    let mutation: MutationEnvelope
    let completedAt: Date
    let timerElapsedSeconds: Int
    let timerActiveSeconds: Int
    let payload: [String: String]
}

private struct ReviewTimingSessionBody: Encodable {
    let mutation: MutationEnvelope
    let decision: ModelUpdateDecision
    let modelInclusion: ModelInclusion
    let scopes: [ReviewLearningScope]
    let userNote: String?
}

private struct CreateAnnotationBody: Encodable {
    let mutation: MutationEnvelope
    let inputMode: AnnotationInputMode
    let rawText: String
    let occurredAt: Date
    let privacyClass: String
    let metadata: [String: String]
}

private struct ConfirmExtractedEventBody: Encodable {
    let mutation: MutationEnvelope
    let confirmationState: ExtractedEventConfirmationState
}

private struct CorrectExtractedEventBody: Encodable {
    let mutation: MutationEnvelope
    let spanType: TemporalSpanType
    let frictionCategory: TemporalFrictionCategory
    let durationSeconds: Int?
    let countPolicy: CountPolicy
    let countInWallTime: Bool
    let countInActiveTime: Bool
    let suggestedPreflightText: String?
    let userNote: String?
}

private struct CreatePreflightCheckBody: Encodable {
    let mutation: MutationEnvelope
    let checkText: String
    let source: String
}

private struct PutCheckpointsBody: Encodable {
    let mutation: MutationEnvelope
    let checkpoints: [CheckpointTemplateDTO]
}

private struct TemporalQueryBody: Encodable {
    let mutation: MutationEnvelope
    let question: String
    let activityId: UUID?
    let timeWindow: String?
    let includeRawQuotes: Bool
}

private struct UpdateTimingReviewFlagBody: Encodable {
    let mutation: MutationEnvelope
    let status: TimingReviewFlagStatus
    let resolutionNote: String?
}

private struct DecidePreflightCheckBody: Encodable {
    let mutation: MutationEnvelope
    let decision: PreflightCheckDecision
    let snoozedUntil: Date?
    let reason: String?
}
