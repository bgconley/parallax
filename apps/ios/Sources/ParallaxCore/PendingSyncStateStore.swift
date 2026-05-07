import Foundation

public struct ActivitySyncMapping: Codable, Equatable, Sendable {
    public let localActivityId: UUID
    public let remoteActivityId: UUID
    public let displayName: String
    public let createdAt: Date

    public init(
        localActivityId: UUID,
        remoteActivityId: UUID,
        displayName: String,
        createdAt: Date
    ) {
        self.localActivityId = localActivityId
        self.remoteActivityId = remoteActivityId
        self.displayName = displayName
        self.createdAt = createdAt
    }
}

public struct TimingSessionSyncMapping: Codable, Equatable, Sendable {
    public let localSessionId: UUID
    public let localActivityId: UUID
    public let remoteActivityId: UUID
    public let remoteSessionId: UUID
    public let createdAt: Date

    public init(
        localSessionId: UUID,
        localActivityId: UUID,
        remoteActivityId: UUID,
        remoteSessionId: UUID,
        createdAt: Date
    ) {
        self.localSessionId = localSessionId
        self.localActivityId = localActivityId
        self.remoteActivityId = remoteActivityId
        self.remoteSessionId = remoteSessionId
        self.createdAt = createdAt
    }
}

public struct PreflightCheckSyncMapping: Codable, Equatable, Sendable {
    public let localCheckId: UUID
    public let localActivityId: UUID
    public let remoteActivityId: UUID
    public let remoteCheckId: UUID
    public let createdAt: Date

    public init(
        localCheckId: UUID,
        localActivityId: UUID,
        remoteActivityId: UUID,
        remoteCheckId: UUID,
        createdAt: Date
    ) {
        self.localCheckId = localCheckId
        self.localActivityId = localActivityId
        self.remoteActivityId = remoteActivityId
        self.remoteCheckId = remoteCheckId
        self.createdAt = createdAt
    }
}

public struct CheckpointRunSyncMapping: Codable, Equatable, Sendable {
    public let localSessionId: UUID
    public let sequenceOrder: Int
    public let remoteCheckpointRunId: UUID
    public let label: String?
    public let createdAt: Date

    public init(
        localSessionId: UUID,
        sequenceOrder: Int,
        remoteCheckpointRunId: UUID,
        label: String? = nil,
        createdAt: Date
    ) {
        self.localSessionId = localSessionId
        self.sequenceOrder = sequenceOrder
        self.remoteCheckpointRunId = remoteCheckpointRunId
        self.label = label
        self.createdAt = createdAt
    }
}

public struct AnnotationSyncMapping: Codable, Equatable, Sendable {
    public let localSessionId: UUID
    public let localEventId: UUID
    public let clientSequence: Int
    public let source: String?
    public let remoteAnnotationId: UUID
    public let createdAt: Date

    public init(
        localSessionId: UUID,
        localEventId: UUID,
        clientSequence: Int,
        source: String? = nil,
        remoteAnnotationId: UUID,
        createdAt: Date
    ) {
        self.localSessionId = localSessionId
        self.localEventId = localEventId
        self.clientSequence = clientSequence
        self.source = source
        self.remoteAnnotationId = remoteAnnotationId
        self.createdAt = createdAt
    }
}

public struct PendingSyncState: Codable, Equatable, Sendable {
    public var activities: [ActivitySyncMapping]
    public var sessions: [TimingSessionSyncMapping]
    public var preflightChecks: [PreflightCheckSyncMapping]
    public var checkpointRuns: [CheckpointRunSyncMapping]
    public var annotations: [AnnotationSyncMapping]

    public init(
        activities: [ActivitySyncMapping] = [],
        sessions: [TimingSessionSyncMapping] = [],
        preflightChecks: [PreflightCheckSyncMapping] = [],
        checkpointRuns: [CheckpointRunSyncMapping] = [],
        annotations: [AnnotationSyncMapping] = []
    ) {
        self.activities = activities
        self.sessions = sessions
        self.preflightChecks = preflightChecks
        self.checkpointRuns = checkpointRuns
        self.annotations = annotations
    }

    private enum CodingKeys: String, CodingKey {
        case activities
        case sessions
        case preflightChecks
        case checkpointRuns
        case annotations
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.activities = try container.decodeIfPresent([ActivitySyncMapping].self, forKey: .activities) ?? []
        self.sessions = try container.decodeIfPresent([TimingSessionSyncMapping].self, forKey: .sessions) ?? []
        self.preflightChecks = try container.decodeIfPresent([PreflightCheckSyncMapping].self, forKey: .preflightChecks) ?? []
        self.checkpointRuns = try container.decodeIfPresent([CheckpointRunSyncMapping].self, forKey: .checkpointRuns) ?? []
        self.annotations = try container.decodeIfPresent([AnnotationSyncMapping].self, forKey: .annotations) ?? []
    }

    public func activity(localActivityId: UUID) -> ActivitySyncMapping? {
        activities.first { $0.localActivityId == localActivityId }
    }

    public func session(localSessionId: UUID) -> TimingSessionSyncMapping? {
        sessions.first { $0.localSessionId == localSessionId }
    }

    public func preflightCheck(localCheckId: UUID) -> PreflightCheckSyncMapping? {
        preflightChecks.first { $0.localCheckId == localCheckId }
    }

    public func checkpointRun(
        localSessionId: UUID,
        sequenceOrder: Int
    ) -> CheckpointRunSyncMapping? {
        checkpointRuns.first {
            $0.localSessionId == localSessionId && $0.sequenceOrder == sequenceOrder
        }
    }

    public func latestAnnotation(
        localSessionId: UUID,
        source: String? = nil
    ) -> AnnotationSyncMapping? {
        annotations
            .filter { mapping in
                mapping.localSessionId == localSessionId
                    && (source == nil || mapping.source == source)
            }
            .max { lhs, rhs in lhs.clientSequence < rhs.clientSequence }
    }

    public mutating func upsert(_ mapping: ActivitySyncMapping) {
        activities.removeAll { $0.localActivityId == mapping.localActivityId }
        activities.append(mapping)
    }

    public mutating func upsert(_ mapping: TimingSessionSyncMapping) {
        sessions.removeAll { $0.localSessionId == mapping.localSessionId }
        sessions.append(mapping)
    }

    public mutating func upsert(_ mapping: PreflightCheckSyncMapping) {
        preflightChecks.removeAll { $0.localCheckId == mapping.localCheckId }
        preflightChecks.append(mapping)
    }

    public mutating func upsert(_ mapping: CheckpointRunSyncMapping) {
        checkpointRuns.removeAll {
            $0.localSessionId == mapping.localSessionId
                && $0.sequenceOrder == mapping.sequenceOrder
        }
        checkpointRuns.append(mapping)
    }

    public mutating func upsert(_ mapping: AnnotationSyncMapping) {
        annotations.removeAll { $0.localEventId == mapping.localEventId }
        annotations.append(mapping)
    }
}

public protocol PendingSyncStateStore: Sendable {
    func load() async throws -> PendingSyncState
    func save(_ state: PendingSyncState) async throws
}

public actor InMemoryPendingSyncStateStore: PendingSyncStateStore {
    private var state: PendingSyncState

    public init(state: PendingSyncState = PendingSyncState()) {
        self.state = state
    }

    public func load() async throws -> PendingSyncState {
        state
    }

    public func save(_ state: PendingSyncState) async throws {
        self.state = state
    }
}

public actor FilePendingSyncStateStore: PendingSyncStateStore {
    private let fileURL: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public init(fileURL: URL) {
        self.fileURL = fileURL
        self.encoder = JSONEncoder()
        self.decoder = JSONDecoder()
        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601
    }

    public func load() async throws -> PendingSyncState {
        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            return PendingSyncState()
        }
        let data = try Data(contentsOf: fileURL)
        return try decoder.decode(PendingSyncState.self, from: data)
    }

    public func save(_ state: PendingSyncState) async throws {
        let directory = fileURL.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let data = try encoder.encode(state)
        try data.write(to: fileURL, options: [.atomic])
    }
}
