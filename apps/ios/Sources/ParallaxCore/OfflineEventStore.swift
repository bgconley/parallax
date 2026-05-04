import Foundation

public struct MutationEnvelope: Codable, Equatable, Sendable {
    public let idempotencyKey: String
    public let clientMutationId: String
    public let clientDeviceId: String
    public let clientSequence: Int
    public let clientTimestamp: Date

    public init(
        idempotencyKey: String,
        clientMutationId: String,
        clientDeviceId: String,
        clientSequence: Int,
        clientTimestamp: Date
    ) {
        self.idempotencyKey = idempotencyKey
        self.clientMutationId = clientMutationId
        self.clientDeviceId = clientDeviceId
        self.clientSequence = clientSequence
        self.clientTimestamp = clientTimestamp
    }
}

public struct MutationEnvelopeFactory: Sendable {
    public let clientDeviceId: String
    private var nextSequence: Int

    public init(clientDeviceId: String, initialSequence: Int = 0) {
        self.clientDeviceId = clientDeviceId
        self.nextSequence = initialSequence
    }

    public mutating func next(prefix: String, at timestamp: Date) -> MutationEnvelope {
        nextSequence += 1
        let mutationId = "\(prefix)-\(nextSequence)"
        return MutationEnvelope(
            idempotencyKey: "\(clientDeviceId):\(nextSequence)",
            clientMutationId: mutationId,
            clientDeviceId: clientDeviceId,
            clientSequence: nextSequence,
            clientTimestamp: timestamp
        )
    }
}

public struct PendingTimingEvent: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public let sessionId: UUID
    public let eventType: TimingEventType
    public let mutation: MutationEnvelope
    public let clientTime: Date
    public let timerElapsedSeconds: Int?
    public let timerActiveSeconds: Int?
    public let captureMethod: CaptureMethod?
    public let notePreview: String?
    public let payload: [String: String]

    public init(
        id: UUID = UUID(),
        sessionId: UUID,
        eventType: TimingEventType,
        mutation: MutationEnvelope,
        clientTime: Date,
        timerElapsedSeconds: Int? = nil,
        timerActiveSeconds: Int? = nil,
        captureMethod: CaptureMethod? = nil,
        notePreview: String? = nil,
        payload: [String: String] = [:]
    ) {
        self.id = id
        self.sessionId = sessionId
        self.eventType = eventType
        self.mutation = mutation
        self.clientTime = clientTime
        self.timerElapsedSeconds = timerElapsedSeconds
        self.timerActiveSeconds = timerActiveSeconds
        self.captureMethod = captureMethod
        self.notePreview = notePreview
        self.payload = payload
    }
}

public protocol PendingTimingEventStore: Sendable {
    func append(_ event: PendingTimingEvent) async throws
    func load() async throws -> [PendingTimingEvent]
    func remove(ids: Set<UUID>) async throws
}

public actor FilePendingTimingEventStore: PendingTimingEventStore {
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

    public func append(_ event: PendingTimingEvent) async throws {
        var events = try readEvents()
        if !events.contains(where: { $0.mutation.idempotencyKey == event.mutation.idempotencyKey }) {
            events.append(event)
        }
        try write(events)
    }

    public func load() async throws -> [PendingTimingEvent] {
        try readEvents()
    }

    public func remove(ids: Set<UUID>) async throws {
        let remaining = try readEvents().filter { !ids.contains($0.id) }
        try write(remaining)
    }

    private func readEvents() throws -> [PendingTimingEvent] {
        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            return []
        }
        let data = try Data(contentsOf: fileURL)
        return try decoder.decode([PendingTimingEvent].self, from: data)
    }

    private func write(_ events: [PendingTimingEvent]) throws {
        let directory = fileURL.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let data = try encoder.encode(events)
        try data.write(to: fileURL, options: [.atomic])
    }
}
