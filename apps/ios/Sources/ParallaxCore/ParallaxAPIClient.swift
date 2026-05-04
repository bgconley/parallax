import Foundation

public enum ParallaxAPIError: Error, Equatable {
    case invalidURL
}

public struct ParallaxAPIClient: Sendable {
    public let baseURL: URL
    public let userId: UUID
    public let urlSession: URLSession

    public init(baseURL: URL, userId: UUID, urlSession: URLSession = .shared) {
        self.baseURL = baseURL
        self.userId = userId
        self.urlSession = urlSession
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

    public func appendTimingEventRequest(_ event: PendingTimingEvent) throws -> URLRequest {
        try jsonRequest(
            path: "/v1/timing/sessions/\(event.sessionId.uuidString)/events",
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

    private func jsonRequest<T: Encodable>(path: String, method: String, body: T) throws -> URLRequest {
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw ParallaxAPIError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(userId.uuidString, forHTTPHeaderField: "X-Parallax-User-Id")
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(body)
        return request
    }
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

private struct DecidePreflightCheckBody: Encodable {
    let mutation: MutationEnvelope
    let decision: PreflightCheckDecision
    let snoozedUntil: Date?
    let reason: String?
}
