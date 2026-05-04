import Foundation

public struct PendingPreflightDecision: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public let activityId: UUID
    public let checkId: UUID
    public let mutation: MutationEnvelope
    public let decision: PreflightCheckDecision
    public let decidedAt: Date
    public let snoozedUntil: Date?
    public let reason: String?

    public init(
        id: UUID = UUID(),
        activityId: UUID,
        checkId: UUID,
        mutation: MutationEnvelope,
        decision: PreflightCheckDecision,
        decidedAt: Date,
        snoozedUntil: Date? = nil,
        reason: String? = nil
    ) {
        self.id = id
        self.activityId = activityId
        self.checkId = checkId
        self.mutation = mutation
        self.decision = decision
        self.decidedAt = decidedAt
        self.snoozedUntil = snoozedUntil
        self.reason = reason
    }
}

public protocol PendingPreflightDecisionStore: Sendable {
    func append(_ decision: PendingPreflightDecision) async throws
    func load() async throws -> [PendingPreflightDecision]
    func remove(ids: Set<UUID>) async throws
}

public actor InMemoryPendingPreflightDecisionStore: PendingPreflightDecisionStore {
    private var decisions: [PendingPreflightDecision]

    public init(decisions: [PendingPreflightDecision] = []) {
        self.decisions = decisions
    }

    public func append(_ decision: PendingPreflightDecision) async throws {
        if !decisions.contains(where: { $0.mutation.idempotencyKey == decision.mutation.idempotencyKey }) {
            decisions.append(decision)
        }
    }

    public func load() async throws -> [PendingPreflightDecision] {
        decisions
    }

    public func remove(ids: Set<UUID>) async throws {
        decisions.removeAll { ids.contains($0.id) }
    }
}

public actor FilePendingPreflightDecisionStore: PendingPreflightDecisionStore {
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

    public func append(_ decision: PendingPreflightDecision) async throws {
        var decisions = try readDecisions()
        if !decisions.contains(where: { $0.mutation.idempotencyKey == decision.mutation.idempotencyKey }) {
            decisions.append(decision)
        }
        try write(decisions)
    }

    public func load() async throws -> [PendingPreflightDecision] {
        try readDecisions()
    }

    public func remove(ids: Set<UUID>) async throws {
        let remaining = try readDecisions().filter { !ids.contains($0.id) }
        try write(remaining)
    }

    private func readDecisions() throws -> [PendingPreflightDecision] {
        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            return []
        }
        let data = try Data(contentsOf: fileURL)
        return try decoder.decode([PendingPreflightDecision].self, from: data)
    }

    private func write(_ decisions: [PendingPreflightDecision]) throws {
        let directory = fileURL.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let data = try encoder.encode(decisions)
        try data.write(to: fileURL, options: [.atomic])
    }
}
