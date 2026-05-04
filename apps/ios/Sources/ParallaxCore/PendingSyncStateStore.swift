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

public struct PendingSyncState: Codable, Equatable, Sendable {
    public var activities: [ActivitySyncMapping]
    public var sessions: [TimingSessionSyncMapping]
    public var preflightChecks: [PreflightCheckSyncMapping]

    public init(
        activities: [ActivitySyncMapping] = [],
        sessions: [TimingSessionSyncMapping] = [],
        preflightChecks: [PreflightCheckSyncMapping] = []
    ) {
        self.activities = activities
        self.sessions = sessions
        self.preflightChecks = preflightChecks
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
