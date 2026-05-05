import Foundation

public struct ActivityDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public let userId: UUID?
    public let displayName: String
    public let canonicalKey: String?
    public let description: String?
    public let status: String?
    public let defaultTimingMode: MeasurementMode?
    public let privacyClass: String?

    public init(
        id: UUID,
        userId: UUID? = nil,
        displayName: String,
        canonicalKey: String? = nil,
        description: String? = nil,
        status: String? = nil,
        defaultTimingMode: MeasurementMode? = nil,
        privacyClass: String? = nil
    ) {
        self.id = id
        self.userId = userId
        self.displayName = displayName
        self.canonicalKey = canonicalKey
        self.description = description
        self.status = status
        self.defaultTimingMode = defaultTimingMode
        self.privacyClass = privacyClass
    }
}

public struct TimingSessionDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public let activityId: UUID
    public let status: TimingSessionStatus
    public let mode: MeasurementMode?
    public let startedAt: Date?
    public let completedAt: Date?
    public let activeSeconds: Int?
    public let wallSeconds: Int?

    public init(
        id: UUID,
        activityId: UUID,
        status: TimingSessionStatus,
        mode: MeasurementMode? = nil,
        startedAt: Date? = nil,
        completedAt: Date? = nil,
        activeSeconds: Int? = nil,
        wallSeconds: Int? = nil
    ) {
        self.id = id
        self.activityId = activityId
        self.status = status
        self.mode = mode
        self.startedAt = startedAt
        self.completedAt = completedAt
        self.activeSeconds = activeSeconds
        self.wallSeconds = wallSeconds
    }
}

public struct TimingEventDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public let sessionId: UUID
    public let eventType: TimingEventType
    public let clientTime: Date?
    public let payload: [String: String]?
}

public struct TimingEventSpanDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public let sessionId: UUID
    public let spanType: TemporalSpanType
    public let countPolicy: CountPolicy
    public let durationSeconds: Int?
}

public struct ActivityProfileDTO: Codable, Equatable, Sendable {
    public let activity: ActivityDTO?
    public let latestStats: ActivityStatsDTO?
    public let preflightChecks: [PreflightCheckDTO]?
    public let recentSessions: [TimingSessionDTO]?
    public let limitations: [String]?
}

public struct ActivityStatsDTO: Codable, Equatable, Sendable {
    public let sampleSize: Int?
    public let confidence: String?
    public let activeP50Seconds: Int?
    public let activeP80Seconds: Int?
    public let wallP50Seconds: Int?
    public let wallP80Seconds: Int?
}

public struct PreflightCheckDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public let activityId: UUID?
    public let checkText: String
    public let state: String?
    public let source: String?
}

public struct CheckpointTemplateDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID?
    public let label: String
    public let position: Int?
    public let isOptional: Bool?
}

public struct ResourceDependencyDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID?
    public let resourceName: String
    public let failureCount: Int?
    public let confidence: Double?
}

public struct TemporalQueryAnswerDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public let question: String
    public let status: String?
    public let answerText: String?
    public let confidence: String?
    public let sampleSize: Int?
    public let evidence: [TemporalQueryEvidenceDTO]?
    public let limitations: [String]?

    private enum CodingKeys: String, CodingKey {
        case id
        case question
        case status
        case answerText = "answer"
        case confidence
        case sampleSize
        case evidence
        case limitations
    }
}

public struct TemporalQueryEvidenceDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID?
    public let summary: String
    public let entityType: String?
    public let entityId: UUID?
}

public struct TimingReviewFlagDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public let sessionId: UUID
    public let status: TimingReviewFlagStatus?
    public let flagType: String?
    public let explanation: String?
}
